"""Bake a single shader node's output to a PNG (exporter pipeline step 8).

Bake-only / unsupported nodes have no Unity Shader Graph equivalent, so when the
*Bake Unsupported Nodes* option is on we render the node's primary output to a
texture and emit it as an Image Texture in the .unif instead.

Technique: temporarily route the target node's output through an Emission shader
into the material's surface output, bake type ``EMIT`` into a temporary image
texture, save the PNG, then fully restore the node tree. Baking requires Cycles
and a UV-mapped mesh.
"""

import os

import bpy

_BAKE_RESOLUTION = 512


def bake_node_to_texture(obj, material, node, output_dir, resolution=_BAKE_RESOLUTION):
    """Bake ``node``'s primary output to ``output_dir``; return the PNG basename
    on success, or ``None`` if baking is not possible."""
    tree = material.node_tree
    out_socket = _primary_output(node)
    material_output = _find_material_output(tree)
    if out_socket is None or material_output is None:
        return None

    surface = material_output.inputs["Surface"]
    original_from = surface.links[0].from_socket if surface.links else None

    emission = tree.nodes.new("ShaderNodeEmission")
    image_node = tree.nodes.new("ShaderNodeTexImage")
    image = bpy.data.images.new(
        f"{material.name}_{node.name}_bake", resolution, resolution, alpha=True
    )
    image_node.image = image

    links = tree.links
    links.new(out_socket, emission.inputs["Color"])
    links.new(emission.outputs["Emission"], surface)

    restore = _begin_bake(obj, tree, image_node)
    baked_name = None
    try:
        bpy.ops.object.bake(type="EMIT")
        baked_name = _save_png(image, material, node, output_dir)
    except RuntimeError:
        baked_name = None
    finally:
        restore()
        tree.nodes.remove(emission)
        tree.nodes.remove(image_node)
        if original_from is not None:
            links.new(original_from, surface)
        bpy.data.images.remove(image)

    return baked_name


# --- internals ------------------------------------------------------------
def _primary_output(node):
    """The first meaningful output socket (prefer Color, then any enabled one)."""
    for socket in node.outputs:
        if socket.name == "Color" and socket.enabled:
            return socket
    for socket in node.outputs:
        if socket.enabled:
            return socket
    return None


def _find_material_output(tree):
    fallback = None
    for node in tree.nodes:
        if node.bl_idname == "ShaderNodeOutputMaterial":
            fallback = fallback or node
            if node.is_active_output:
                return node
    return fallback


def _begin_bake(obj, tree, image_node):
    """Configure Cycles + selection for an EMIT bake; return a restore callback."""
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer

    prev_engine = scene.render.engine
    prev_samples = getattr(scene.cycles, "samples", None) if hasattr(scene, "cycles") else None
    prev_active_node = tree.nodes.active
    prev_active_obj = view_layer.objects.active
    prev_selection = list(bpy.context.selected_objects)

    scene.render.engine = "CYCLES"
    if hasattr(scene, "cycles"):
        scene.cycles.samples = 1  # EMIT bake is a direct read; no AA needed
    scene.render.bake.margin = 4

    for selected in prev_selection:
        selected.select_set(False)
    obj.select_set(True)
    view_layer.objects.active = obj
    tree.nodes.active = image_node
    image_node.select = True

    def restore():
        scene.render.engine = prev_engine
        if prev_samples is not None and hasattr(scene, "cycles"):
            scene.cycles.samples = prev_samples
        tree.nodes.active = prev_active_node
        obj.select_set(False)
        for selected in prev_selection:
            selected.select_set(True)
        view_layer.objects.active = prev_active_obj

    return restore


def _save_png(image, material, node, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{material.name}_{node.name}_baked.png".replace(" ", "_")
    filepath = os.path.join(output_dir, filename)
    image.filepath_raw = filepath
    image.file_format = "PNG"
    image.save()
    return filename
