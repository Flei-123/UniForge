"""Download an ambientCG material set and build a Blender material from it."""

import os
import tempfile
import zipfile

import bpy

from . import ambientcg


def download_and_apply(result, resolution, obj):
    """Download ``result`` at ``resolution``, build a material, assign to ``obj``.

    Returns the created Material, or None on failure.
    """
    asset_id = result.get("id") or "Material"
    url = ambientcg.pick_download(result.get("resolutions", {}), resolution)
    if not url:
        return None

    folder = os.path.join(_textures_root(), f"{asset_id}_{resolution}")
    os.makedirs(folder, exist_ok=True)
    zip_path = os.path.join(folder, "_download.zip")
    ambientcg.download(url, zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(folder)
    try:
        os.remove(zip_path)
    except OSError:
        pass

    material = build_material(asset_id, folder)
    if material is not None:
        _assign(obj, material)
    return material


def build_material(name, folder):
    """Build a Principled material from the PBR maps found in ``folder``."""
    maps = _classify_maps(folder)
    if not maps:
        return None

    material = bpy.data.materials.new(name)
    material.use_nodes = True
    tree = material.node_tree
    bsdf = tree.nodes.get("Principled BSDF")

    def add_texture(path, non_color):
        image = bpy.data.images.load(path, check_existing=True)
        if non_color:
            image.colorspace_settings.name = "Non-Color"
        node = tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        return node

    if "color" in maps:
        tree.links.new(add_texture(maps["color"], False).outputs["Color"], bsdf.inputs["Base Color"])
    if "roughness" in maps:
        tree.links.new(add_texture(maps["roughness"], True).outputs["Color"], bsdf.inputs["Roughness"])
    if "metalness" in maps:
        tree.links.new(add_texture(maps["metalness"], True).outputs["Color"], bsdf.inputs["Metallic"])
    if "normal" in maps:
        normal_map = tree.nodes.new("ShaderNodeNormalMap")
        tree.links.new(add_texture(maps["normal"], True).outputs["Color"], normal_map.inputs["Color"])
        tree.links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])

    return material


# --- internals ------------------------------------------------------------
def _classify_maps(folder):
    """Map type -> file path for the textures in ``folder`` (prefer NormalGL)."""
    maps = {}
    normal_gl = normal_dx = None
    for filename in os.listdir(folder):
        if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff")):
            continue
        path = os.path.join(folder, filename)
        lower = filename.lower()
        if "normalgl" in lower:
            normal_gl = path
        elif "normaldx" in lower:
            normal_dx = path
        elif "color" in lower or "diffuse" in lower or "albedo" in lower:
            maps["color"] = path
        elif "roughness" in lower:
            maps["roughness"] = path
        elif "metal" in lower:  # Metalness / Metallic
            maps["metalness"] = path
    normal = normal_gl or normal_dx
    if normal:
        maps["normal"] = normal
    return maps


def _assign(obj, material):
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)


def _textures_root():
    """Folder for downloaded textures: next to the .blend if saved, else temp."""
    if bpy.data.filepath:
        root = os.path.join(os.path.dirname(bpy.data.filepath), "uniforge_materials")
    else:
        root = os.path.join(tempfile.gettempdir(), "uniforge_materials")
    os.makedirs(root, exist_ok=True)
    return root
