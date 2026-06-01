"""Material / shader node-tree extraction (spec §4.3, steps 6-9).

For each material slot:
  - Walk the node tree, identify node types via node_map.
  - Supported / Partial nodes -> serialize to [NODE] blocks.
  - Bake-only / unsupported nodes -> skip (bake fallback is a TODO milestone).
  - Serialize all connections between exported nodes to [CONNECTION].

Unlinked input sockets carrying a ``default_value`` are written as node
parameters so the Unity side can rebuild the graph without the source .blend.
"""

import bpy

from . import node_map


def export_materials(obj, writer, options):
    """Serialize every material slot of ``obj`` into ``writer``."""
    for slot_index, slot in enumerate(obj.material_slots):
        material = slot.material
        if material is None:
            options.report(
                {"WARNING"}, f"{obj.name}: material slot {slot_index} is empty; skipped."
            )
            continue

        writer.begin_material(material.name, slot_index)
        if material.use_nodes and material.node_tree:
            _export_node_tree(material.node_tree, writer, options)
        else:
            options.report(
                {"INFO"},
                f"{material.name}: no node tree; exported as a bare material.",
            )
        writer.end_material()


# --- internals ------------------------------------------------------------
def _export_node_tree(node_tree, writer, options):
    ids = _assign_ids(node_tree, options)

    for node, node_id in ids.items():
        unif_type, _status = node_map.lookup(node.bl_idname)
        writer.write_node(
            unif_type,
            node_id,
            attrs=_node_attrs(node, unif_type),
            params=_node_params(node, unif_type),
        )

    connections = [
        link
        for link in node_tree.links
        if link.from_node in ids and link.to_node in ids
    ]
    if connections:
        writer.begin_connections()
        for link in connections:
            writer.write_connection(
                ids[link.from_node],
                _socket_name(link.from_socket),
                ids[link.to_node],
                _socket_name(link.to_socket),
            )


def _assign_ids(node_tree, options):
    """Map each exportable node to a stable id, warning on the rest."""
    ids = {}
    next_id = 0
    for node in node_tree.nodes:
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
            # TODO(v1.x): bake to a PNG texture when options.bake_unsupported.
            options.report(
                {"WARNING"},
                f"Node '{unif_type}' is bake-only; texture bake not yet implemented.",
            )
            continue

        ids[node] = next_id
        next_id += 1
    return ids


def _socket_name(socket):
    """Normalize a Blender socket name to the .unif convention (spaces -> '_')."""
    return socket.name.replace(" ", "_")


def _node_attrs(node, unif_type):
    """Inline header attributes for a node (e.g. image path)."""
    attrs = {}
    if unif_type == "ImageTexture":
        image = getattr(node, "image", None)
        if image is not None:
            path = image.filepath_raw or image.filepath or image.name
            # bpy.path.basename understands Blender's "//" relative prefix;
            # os.path.basename mangles it into a UNC root on Windows.
            attrs["path"] = bpy.path.basename(path)
    return attrs


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
