"""Import operator: File > Import > UniForge Asset (.unif).

Rebuilds Blender objects (mesh + hierarchy + transforms) and materials
(Principled + textures, incl. embedded ones) from a .unif file — the reverse
of the exporter, making the bridge round-trippable.
"""

import os
import tempfile

import bpy
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from .export import node_map
from .export.mesh import blender_to_unity_vector  # self-inverse axis swap
from .unif import reader

# unif type -> Blender node bl_idname (reverse of node_map.NODE_MAP).
_BL_IDNAME = {unif: bl for bl, (unif, _status) in node_map.NODE_MAP.items()}


class UNIFORGE_OT_import(Operator, ImportHelper):
    """Import a .unif file back into Blender."""

    bl_idname = "uniforge.import_asset"
    bl_label = "UniForge Asset (.unif)"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".unif"
    filter_glob: StringProperty(default="*.unif", options={"HIDDEN"})

    def execute(self, context):
        doc = reader.parse_file(self.filepath)
        unif_dir = os.path.dirname(self.filepath)
        images = _load_images(doc, unif_dir)

        created = {}  # name -> object
        for obj_data in doc.objects:
            obj = _build_object(obj_data, images, context)
            if obj is not None:
                created[obj_data.name] = obj

        # Re-parent per the stored hierarchy (keep_transform=False: the stored
        # transform is already parent-relative).
        for obj_data in doc.objects:
            child = created.get(obj_data.name)
            parent = created.get(obj_data.parent) if obj_data.parent else None
            if child is not None and parent is not None:
                child.parent = parent

        self.report({"INFO"}, f"Imported {len(created)} object(s) from {os.path.basename(self.filepath)}")
        return {"FINISHED"}


# --- build objects --------------------------------------------------------
def _build_object(obj_data, images, context):
    name = obj_data.name or "UnifObject"
    if obj_data.mesh:
        mesh = _build_mesh(obj_data.mesh)
        obj = bpy.data.objects.new(name, mesh)
        materials = [_build_material(m, images) for m in sorted(obj_data.materials, key=lambda m: m.slot)]
        for material in materials:
            obj.data.materials.append(material)
        _assign_submeshes(mesh, obj_data.mesh.get("submeshes"))
    else:
        obj = bpy.data.objects.new(name, None)  # empty (transform-only)

    context.scene.collection.objects.link(obj)
    _apply_transform(obj, obj_data.transform)
    return obj


def _build_mesh(data):
    flat_v = data.get("vertices", [])
    faces_flat = data.get("faces", [])
    # Unity Y-up -> Blender Z-up (the (x,y,z)->(x,z,y) swap is its own inverse).
    verts = [blender_to_unity_vector(flat_v[i:i + 3]) for i in range(0, len(flat_v), 3)]
    # Reverse the winding flip applied on export.
    faces = [(faces_flat[i], faces_flat[i + 2], faces_flat[i + 1]) for i in range(0, len(faces_flat), 3)]

    mesh = bpy.data.meshes.new(data.get("name", "UnifMesh"))
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    uvs = data.get("uvs")
    if uvs:
        uv_layer = mesh.uv_layers.new(name="UVMap")
        for loop in mesh.loops:
            base = loop.vertex_index * 2  # per-corner data (unwelded export)
            if base + 1 < len(uvs):
                uv_layer.data[loop.index].uv = (uvs[base], uvs[base + 1])

    colors = data.get("colors")
    if colors:
        color_layer = mesh.color_attributes.new(name="Color", type="BYTE_COLOR", domain="CORNER")
        for loop in mesh.loops:
            base = loop.vertex_index * 4
            if base + 3 < len(colors):
                color_layer.data[loop.index].color = colors[base:base + 4]

    mesh.validate()
    mesh.update()
    return mesh


def _assign_submeshes(mesh, submeshes):
    if not submeshes or len(submeshes) <= 1:
        return
    triangle = 0
    for slot, count in enumerate(submeshes):
        for _ in range(count):
            if triangle < len(mesh.polygons):
                mesh.polygons[triangle].material_index = slot
            triangle += 1


def _apply_transform(obj, transform):
    if not transform:
        return
    import math

    pos = transform.get("position")
    rot = transform.get("rotation")
    scale = transform.get("scale")
    if pos and len(pos) >= 3:
        obj.location = blender_to_unity_vector(pos)
    if scale and len(scale) >= 3:
        sx, sy, sz = scale[:3]
        obj.scale = (sx, sz, sy)
    if rot and len(rot) >= 3:
        rx, ry, rz = rot[:3]
        obj.rotation_euler = (math.radians(rx), math.radians(rz), math.radians(ry))


# --- build materials ------------------------------------------------------
def _build_material(mat_data, images):
    material = bpy.data.materials.new(mat_data.name or "UnifMaterial")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()

    nodes_by_id = {}
    for node_data in mat_data.nodes:
        bl_idname = _BL_IDNAME.get(node_data.type)
        if bl_idname is None:
            continue
        node = tree.nodes.new(bl_idname)
        nodes_by_id[node_data.id] = node
        _apply_node(node, node_data, images)

    for src_id, src_socket, dst_id, dst_socket in mat_data.connections:
        src, dst = nodes_by_id.get(src_id), nodes_by_id.get(dst_id)
        if src is None or dst is None:
            continue
        out = _find_socket(src.outputs, src_socket)
        inp = _find_socket(dst.inputs, dst_socket)
        if out is not None and inp is not None:
            tree.links.new(out, inp)

    return material


def _apply_node(node, node_data, images):
    if node_data.type == "ImageTexture":
        path = node_data.attrs.get("path")
        if path and path in images:
            node.image = images[path]
        return
    for key, value in node_data.params.items():
        socket = _find_socket(node.inputs, key)
        if socket is not None and hasattr(socket, "default_value"):
            _set_socket(socket, value)


def _find_socket(sockets, name):
    """Match a socket by the .unif normalized name (spaces/underscores, case)."""
    target = name.replace(" ", "_").lower()
    for socket in sockets:
        if socket.name.replace(" ", "_").lower() == target:
            return socket
    return None


def _set_socket(socket, value):
    if value in ("true", "false"):
        try:
            socket.default_value = value == "true"
        except (TypeError, ValueError):
            pass
        return
    try:
        parts = [float(p) for p in value.split(",")]
    except ValueError:
        return
    if len(parts) == 1:
        try:
            socket.default_value = parts[0]
        except (TypeError, ValueError):
            pass
        return
    try:
        current = socket.default_value
        for i in range(min(len(current), len(parts))):
            current[i] = parts[i]
    except TypeError:
        socket.default_value = parts[0]


# --- embedded / referenced textures ---------------------------------------
def _load_images(doc, unif_dir):
    """Return {path -> bpy.types.Image} for embedded and referenced textures."""
    images = {}
    tmp = tempfile.mkdtemp(prefix="uniforge_import_")

    for name, (_fmt, data) in doc.embedded.items():
        out = os.path.join(tmp, os.path.basename(name) or "tex")
        try:
            with open(out, "wb") as handle:
                handle.write(data)
            image = bpy.data.images.load(out)
            image.pack()  # embed in the .blend so the temp file isn't needed
            images[name] = image
        except (OSError, RuntimeError):
            pass

    # Referenced (non-embedded) textures: try next to the .unif.
    for obj in doc.objects:
        for mat in obj.materials:
            for node in mat.nodes:
                path = node.attrs.get("path")
                if not path or path in images:
                    continue
                candidate = os.path.join(unif_dir, path)
                if os.path.isfile(candidate):
                    try:
                        images[path] = bpy.data.images.load(candidate)
                    except RuntimeError:
                        pass
    return images


def _menu_func_import(self, context):
    self.layout.operator(UNIFORGE_OT_import.bl_idname, text="UniForge Asset (.unif)")


def register():
    bpy.utils.register_class(UNIFORGE_OT_import)
    bpy.types.TOPBAR_MT_file_import.append(_menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(_menu_func_import)
    bpy.utils.unregister_class(UNIFORGE_OT_import)
