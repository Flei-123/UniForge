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
    out_socket = _primary_output(node)
    if out_socket is None:
        return None
    return bake_socket_to_texture(
        obj, material, out_socket, output_dir,
        name_hint=f"{material.name}_{node.name}", resolution=resolution,
    )


def bake_socket_to_texture(obj, material, from_socket, output_dir, name_hint,
                           resolution=_BAKE_RESOLUTION):
    """Bake the value carried by ``from_socket`` to a PNG; return basename or None.

    Used for bake-only nodes and for collapsing a procedural sub-network that
    drives a Principled input into a single texture."""
    image = _bake_socket(obj, material, from_socket, resolution)
    if image is None:
        return None
    try:
        return _save_png(image, name_hint, output_dir)
    finally:
        bpy.data.images.remove(image)


def bake_metallic_smoothness(obj, material, bsdf, output_dir, name_hint,
                             resolution=_BAKE_RESOLUTION):
    """Bake a Unity-packed Metallic/Smoothness map (R=metallic, A=1-roughness).

    Each channel is baked from its Principled input if procedurally linked, or
    filled from the constant default otherwise. Returns the PNG basename or
    None when neither channel is linked."""
    import numpy as np

    metallic = _channel_for_input(obj, material, bsdf, "Metallic", resolution)
    roughness = _channel_for_input(obj, material, bsdf, "Roughness", resolution)
    if metallic is None and roughness is None:
        return None

    count = resolution * resolution
    if metallic is None:
        metallic = np.full(count, _const_input(bsdf, "Metallic", 0.0), dtype=np.float32)
    if roughness is None:
        roughness = np.full(count, _const_input(bsdf, "Roughness", 0.5), dtype=np.float32)

    packed = np.empty((count, 4), dtype=np.float32)
    packed[:, 0] = packed[:, 1] = packed[:, 2] = metallic  # metallic in RGB
    packed[:, 3] = 1.0 - roughness                          # smoothness in alpha

    image = bpy.data.images.new(
        f"{name_hint}_ms".replace(" ", "_"), resolution, resolution, alpha=True
    )
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(packed.ravel())
    try:
        return _save_png(image, name_hint, output_dir)
    finally:
        bpy.data.images.remove(image)


def _bake_socket(obj, material, from_socket, resolution, non_color=False):
    """Bake ``from_socket`` via an EMIT pass; return the Image (caller removes it)."""
    tree = material.node_tree
    material_output = _find_material_output(tree)
    if from_socket is None or material_output is None:
        return None

    surface = material_output.inputs["Surface"]
    original_from = surface.links[0].from_socket if surface.links else None

    emission = tree.nodes.new("ShaderNodeEmission")
    image_node = tree.nodes.new("ShaderNodeTexImage")
    image = bpy.data.images.new("uniforge_bake_tmp", resolution, resolution, alpha=True)
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    image_node.image = image

    links = tree.links
    links.new(from_socket, emission.inputs["Color"])
    links.new(emission.outputs["Emission"], surface)

    restore = _begin_bake(obj, tree, image_node)
    ok = False
    try:
        bpy.ops.object.bake(type="EMIT")
        ok = True
    except RuntimeError:
        ok = False
    finally:
        restore()
        tree.nodes.remove(emission)
        tree.nodes.remove(image_node)
        if original_from is not None:
            links.new(original_from, surface)

    if not ok:
        bpy.data.images.remove(image)
        return None
    return image


def _channel_for_input(obj, material, bsdf, input_name, resolution):
    """Bake a Principled input's R channel to a numpy array, or None if unlinked."""
    import numpy as np

    socket = bsdf.inputs.get(input_name)
    if socket is None or not socket.is_linked:
        return None
    image = _bake_socket(obj, material, socket.links[0].from_socket, resolution, non_color=True)
    if image is None:
        return None
    try:
        buffer = np.empty(resolution * resolution * 4, dtype=np.float32)
        image.pixels.foreach_get(buffer)
        return buffer.reshape(-1, 4)[:, 0].copy()  # red channel
    finally:
        bpy.data.images.remove(image)


def _const_input(bsdf, input_name, default):
    socket = bsdf.inputs.get(input_name)
    if socket is not None and not socket.is_linked and hasattr(socket, "default_value"):
        try:
            return float(socket.default_value)
        except (TypeError, ValueError):
            return default
    return default


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


def _save_png(image, name_hint, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{name_hint}_baked.png".replace(" ", "_")
    filepath = os.path.join(output_dir, filename)
    image.filepath_raw = filepath
    image.file_format = "PNG"
    image.save()
    return filename
