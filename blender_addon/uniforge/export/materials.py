"""Material / shader node-tree extraction (spec §4.3, steps 6-9).

For each material slot:
  - Walk the node tree, identify node types via node_map.
  - Supported / Partial nodes -> serialize to [NODE] blocks.
  - Bake-only / unsupported nodes -> skip (bake fallback is a TODO milestone).
  - Serialize all connections between exported nodes to [CONNECTION].

Unlinked input sockets carrying a ``default_value`` are written as node
parameters so the Unity side can rebuild the graph without the source .blend.
"""

import os
import shutil

import bpy

from . import bake, node_map


def export_materials(obj, writer, options):
    """Serialize every material slot of ``obj`` into ``writer``."""
    output_dir = (
        os.path.dirname(options.filepath) if getattr(options, "filepath", None) else None
    )
    for slot_index, slot in enumerate(obj.material_slots):
        material = slot.material
        if material is None:
            options.report(
                {"WARNING"}, f"{obj.name}: material slot {slot_index} is empty; skipped."
            )
            continue

        writer.begin_material(material.name, slot_index)
        if material.use_nodes and material.node_tree:
            _export_node_tree(material.node_tree, writer, options, obj, output_dir)
        else:
            options.report(
                {"INFO"},
                f"{material.name}: no node tree; exported as a bare material.",
            )
        writer.end_material()


# --- internals ------------------------------------------------------------
def _export_node_tree(node_tree, writer, options, obj=None, output_dir=None):
    # Collapse procedural sub-networks driving Principled inputs into baked
    # textures, so the exported graph stays Lit-mappable on the Unity side.
    # ``synthetic`` are extra (packed) textures with no single source node.
    prebaked, excluded, synthetic = _plan_procedural_bakes(
        node_tree, options, obj, output_dir, writer
    )

    ids, baked = _assign_ids(node_tree, options, obj, output_dir, prebaked, excluded, writer)
    baked.update(prebaked)

    for node, node_id in ids.items():
        if node in baked:
            # Baked to a texture; emit as an Image Texture so connections
            # referencing its output socket still resolve on the Unity side.
            writer.write_node("ImageTexture", node_id, attrs={"path": baked[node]})
            continue
        unif_type, _status = node_map.lookup(node.bl_idname)
        writer.write_node(
            unif_type,
            node_id,
            attrs=_node_attrs(node, unif_type, output_dir, options, writer),
            params=_node_params(node, unif_type),
        )

    # Emit synthetic packed textures (e.g. MetallicSmoothness) as fresh nodes
    # wired straight into the Principled input they represent.
    synthetic_connections = []
    next_id = max(ids.values(), default=-1) + 1
    bsdf_id = ids.get(_find_principled(node_tree))
    for target_socket, filename in synthetic:
        writer.write_node("ImageTexture", next_id, attrs={"path": filename})
        if bsdf_id is not None:
            synthetic_connections.append((next_id, "Color", bsdf_id, target_socket))
        next_id += 1

    connections = [
        link
        for link in node_tree.links
        if link.from_node in ids and link.to_node in ids
    ]
    if connections or synthetic_connections:
        writer.begin_connections()
        for link in connections:
            writer.write_connection(
                ids[link.from_node],
                _socket_name(link.from_socket),
                ids[link.to_node],
                _socket_name(link.to_socket),
            )
        for src_id, src_socket, dst_id, dst_socket in synthetic_connections:
            writer.write_connection(src_id, src_socket, dst_id, dst_socket)


def _assign_ids(node_tree, options, obj=None, output_dir=None, prebaked=None, excluded=None, writer=None):
    """Map each exportable node to a stable id, baking or skipping the rest.

    Returns ``(ids, baked)`` where ``ids`` maps node -> id and ``baked`` maps a
    node -> baked PNG basename (a subset of ``ids``). ``prebaked`` nodes (already
    baked procedural roots) are assigned ids and emitted as Image Textures;
    ``excluded`` nodes (collapsed procedural upstream) are skipped entirely.
    """
    prebaked = prebaked or {}
    excluded = excluded or set()
    ids = {}
    baked = {}
    next_id = 0
    for node in node_tree.nodes:
        if node in excluded:
            continue
        if node in prebaked:
            ids[node] = next_id
            next_id += 1
            continue

        unif_type, status = node_map.lookup(node.bl_idname)

        if unif_type is None:
            options.report({"WARNING"}, f"Unknown node '{node.bl_idname}' skipped.")
            continue
        if status is node_map.Status.NOT_SUPPORTED:
            options.report(
                {"WARNING"}, f"Node '{unif_type}' is not supported in v1.0; skipped."
            )
            continue
        if status is node_map.Status.BAKE_ONLY:
            filename = _try_bake(node, unif_type, options, obj, output_dir)
            if filename is None:
                continue
            filename = _finalize_texture(writer, options, output_dir, filename)
            ids[node] = next_id
            baked[node] = filename
            next_id += 1
            continue

        ids[node] = next_id
        next_id += 1
    return ids, baked


def _plan_procedural_bakes(node_tree, options, obj, output_dir, writer=None):
    """Bake Principled inputs driven by procedural networks to textures.

    Returns ``(prebaked, excluded, synthetic)``:
      - ``prebaked`` maps a feeding node -> baked PNG basename (re-emitted as an
        Image Texture in place, reusing its existing connection),
      - ``excluded`` is the set of now-redundant nodes to drop,
      - ``synthetic`` is a list of ``(target_socket, filename)`` for packed maps
        that have no single source node (e.g. MetallicSmoothness).
    """
    prebaked = {}
    excluded = set()
    synthetic = []
    if not getattr(options, "bake_unsupported", False) or obj is None or output_dir is None:
        return prebaked, excluded, synthetic

    bsdf = _find_principled(node_tree)
    if bsdf is None:
        return prebaked, excluded, synthetic
    material = _owning_material(bsdf)
    if material is None:
        return prebaked, excluded, synthetic

    # Base Color: a single map, re-emitted in place of its feeding node.
    socket = bsdf.inputs.get("Base Color")
    if socket is not None and socket.is_linked:
        src_node = socket.links[0].from_node
        if src_node.bl_idname != "ShaderNodeTexImage":
            hint = f"{material.name}_BaseColor"
            filename = bake.bake_socket_to_texture(
                obj, material, socket.links[0].from_socket, output_dir, hint
            )
            if filename:
                filename = _finalize_texture(writer, options, output_dir, filename)
                prebaked[src_node] = filename
                excluded |= _upstream_nodes(src_node)
                options.report({"INFO"}, f"Baked procedural Base Color to {filename}.")

    # Metallic + Roughness: packed into one Unity map (R=metallic, A=smoothness).
    # Triggered whenever either is textured — procedural OR a direct image map
    # (separate Metallic/Roughness maps, e.g. from the material browser, can't
    # map to URP's single Metallic/Smoothness texture otherwise).
    if _is_textured_input(bsdf, "Metallic") or _is_textured_input(bsdf, "Roughness"):
        hint = f"{material.name}_MetallicSmoothness"
        filename = bake.bake_metallic_smoothness(obj, material, bsdf, output_dir, hint)
        if filename:
            filename = _finalize_texture(writer, options, output_dir, filename)
            synthetic.append(("Metallic", filename))
            for input_name in ("Metallic", "Roughness"):
                feeder = bsdf.inputs.get(input_name)
                if feeder is not None and feeder.is_linked:
                    src = feeder.links[0].from_node
                    excluded.add(src)
                    excluded |= _upstream_nodes(src)
            options.report({"INFO"}, f"Baked Metallic/Smoothness to {filename}.")

    # Emission: bake a procedurally-driven emission color to a map.
    if _is_procedural_input(bsdf, "Emission Color"):
        socket = bsdf.inputs.get("Emission Color")
        hint = f"{material.name}_Emission"
        filename = bake.bake_socket_to_texture(
            obj, material, socket.links[0].from_socket, output_dir, hint
        )
        if filename:
            filename = _finalize_texture(writer, options, output_dir, filename)
            synthetic.append(("Emission_Color", filename))
            src = socket.links[0].from_node
            excluded.add(src)
            excluded |= _upstream_nodes(src)
            options.report({"INFO"}, f"Baked Emission to {filename}.")

    return prebaked, excluded, synthetic


def _is_procedural_input(bsdf, input_name):
    """True if the input is linked to something other than a direct Image Texture."""
    socket = bsdf.inputs.get(input_name)
    if socket is None or not socket.is_linked:
        return False
    return socket.links[0].from_node.bl_idname != "ShaderNodeTexImage"


def _is_textured_input(bsdf, input_name):
    """True if the input is linked to anything (procedural or a direct image)."""
    socket = bsdf.inputs.get(input_name)
    return socket is not None and socket.is_linked


def _finalize_texture(writer, options, output_dir, basename):
    """Embed a just-baked PNG (and remove the standalone file) when embedding."""
    if getattr(options, "embed_textures", False) and writer is not None and output_dir:
        full = os.path.join(output_dir, basename)
        if _embed_file(writer, full, basename):
            try:
                os.remove(full)
            except OSError:
                pass
    return basename


def _embed_file(writer, filepath, basename):
    """Read a texture file and queue it as a [TEXTURE_EMBEDDED] block."""
    try:
        with open(filepath, "rb") as handle:
            data = handle.read()
    except OSError:
        return False
    fmt = os.path.splitext(basename)[1].lstrip(".").lower() or "png"
    writer.queue_embedded(basename, fmt, data)
    return True


def _find_principled(node_tree):
    for node in node_tree.nodes:
        if node.bl_idname == "ShaderNodeBsdfPrincipled":
            return node
    return None


def _upstream_nodes(node):
    """All nodes transitively feeding ``node``'s inputs (excluding ``node``)."""
    result = set()
    stack = [node]
    while stack:
        current = stack.pop()
        for socket in current.inputs:
            for link in socket.links:
                upstream = link.from_node
                if upstream not in result:
                    result.add(upstream)
                    stack.append(upstream)
    return result


def _try_bake(node, unif_type, options, obj, output_dir):
    """Bake a bake-only node when enabled; return the PNG basename or None."""
    if not getattr(options, "bake_unsupported", False) or obj is None or output_dir is None:
        options.report(
            {"WARNING"}, f"Node '{unif_type}' is bake-only; not baked (option off)."
        )
        return None

    material = _owning_material(node)
    if material is None:
        options.report({"WARNING"}, f"Could not resolve material for '{unif_type}'; skipped.")
        return None

    filename = bake.bake_node_to_texture(obj, material, node, output_dir)
    if filename:
        options.report({"INFO"}, f"Baked bake-only node '{unif_type}' to {filename}.")
    else:
        options.report({"WARNING"}, f"Could not bake '{unif_type}'; skipped.")
    return filename


def _owning_material(node):
    """Resolve the Material that owns ``node`` from its node tree."""
    tree = node.id_data  # ShaderNodeTree
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree is tree:
            return mat
    return None


def _socket_name(socket):
    """Normalize a Blender socket name to the .unif convention (spaces -> '_')."""
    return socket.name.replace(" ", "_")


def _node_attrs(node, unif_type, output_dir=None, options=None, writer=None):
    """Inline header attributes for a node (e.g. image path).

    With *Embed Textures* the referenced image is Base64-embedded into the
    .unif; otherwise (when ``output_dir`` is set) it is copied next to the
    .unif so the export is self-contained either way.
    """
    attrs = {}
    if unif_type == "ImageTexture":
        image = getattr(node, "image", None)
        if image is not None:
            raw = image.filepath_raw or image.filepath
            # bpy.path.basename understands Blender's "//" relative prefix;
            # os.path.basename mangles it into a UNC root on Windows.
            basename = bpy.path.basename(raw or image.name)
            attrs["path"] = basename
            if getattr(options, "embed_textures", False) and writer is not None:
                _embed_image(writer, image, basename)
            elif output_dir:
                src = bpy.path.abspath(raw) if raw else None
                if src:
                    _copy_texture(src, output_dir, basename)
    return attrs


def _embed_image(writer, image, basename):
    """Embed an image datablock: prefer packed bytes, then a disk file, then a
    temporary PNG export (covers generated/edited images)."""
    fmt = os.path.splitext(basename)[1].lstrip(".").lower() or "png"

    packed = getattr(image, "packed_file", None)
    if packed is not None and packed.data:
        writer.queue_embedded(basename, fmt, bytes(packed.data))
        return True

    raw = image.filepath_raw or image.filepath
    src = bpy.path.abspath(raw) if raw else None
    if src and os.path.isfile(src):
        return _embed_file(writer, src, basename)

    # Fallback: render the image to a temporary PNG and embed that.
    import tempfile

    tmp = os.path.join(tempfile.gettempdir(), "uniforge_emb_" + basename)
    if not tmp.lower().endswith(".png"):
        tmp += ".png"
    prev_path, prev_fmt = image.filepath_raw, image.file_format
    try:
        image.filepath_raw = tmp
        image.file_format = "PNG"
        image.save()
        return _embed_file(writer, tmp, basename)
    except (RuntimeError, OSError):
        return False
    finally:
        image.filepath_raw, image.file_format = prev_path, prev_fmt
        try:
            os.remove(tmp)
        except OSError:
            pass


def _copy_texture(src, output_dir, basename):
    """Copy a source texture next to the .unif (skip if missing or up to date)."""
    if not src or not os.path.isfile(src):
        return
    dest = os.path.join(output_dir, basename)
    try:
        if os.path.abspath(src) == os.path.abspath(dest):
            return
        if os.path.exists(dest) and os.path.getmtime(dest) >= os.path.getmtime(src):
            return
        os.makedirs(output_dir, exist_ok=True)
        shutil.copy2(src, dest)
    except OSError:
        pass


# Curated input sockets per node type (Blender socket names). When a type is
# listed, ONLY these sockets are exported as params; this trims the dozens of
# internal/closure sockets (Normal, Tangent, Weight, Coat*, Sheen*, …) that a
# Blender node exposes but Unity has no use for. Types not listed here fall
# back to _is_meaningful_param().
_PARAM_WHITELIST = {
    "PrincipledBSDF": (
        "Base Color",
        "Metallic",
        "Roughness",
        "Specular IOR Level",
        "IOR",
        "Alpha",
        "Emission Color",
        "Emission Strength",
    ),
    "Mapping": ("Location", "Rotation", "Scale"),
}


def _node_params(node, unif_type):
    """Unlinked input defaults, keyed by lowercased underscore name."""
    whitelist = _PARAM_WHITELIST.get(unif_type)
    params = {}
    for socket in node.inputs:
        if socket.is_linked or not hasattr(socket, "default_value"):
            continue
        if whitelist is not None:
            if socket.name not in whitelist:
                continue
        elif not _is_meaningful_param(socket):
            continue
        key = socket.name.replace(" ", "_").lower()
        params[key] = _format_value(socket.default_value)
    return params


def _is_meaningful_param(socket):
    """Heuristic for non-whitelisted nodes: drop link-only / internal sockets."""
    # The closure-mixing "Weight" socket is Blender-internal; Unity ignores it.
    if socket.name == "Weight":
        return False
    value = socket.default_value
    # A bare 3-component vector input (Vector / Normal / Tangent) is virtually
    # always meant to be linked; a 0,0,0 default carries no usable information.
    if hasattr(value, "__len__") and not isinstance(value, str) and len(value) == 3:
        return False
    return True


def _format_value(value):
    """Coerce a socket default into a writer-friendly scalar or string."""
    # Color / vector sockets expose an indexable bpy_prop_array.
    if hasattr(value, "__len__") and not isinstance(value, str):
        return ",".join(f"{float(v):.6g}" for v in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return value
