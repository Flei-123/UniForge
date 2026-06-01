"""Headless exporter smoke test. Run with:

    blender --background --python tests/blender_export_test.py

Builds a cube + material (Principled BSDF fed by an Image Texture), runs it
through the UniForge export functions, and prints the resulting .unif.
"""

import os
import sys
import tempfile

_ADDON_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "blender_addon"
)
sys.path.insert(0, _ADDON_DIR)

import bpy  # noqa: E402

from uniforge.export import materials as material_export  # noqa: E402
from uniforge.export import mesh as mesh_export  # noqa: E402
from uniforge.unif.writer import UnifWriter  # noqa: E402


class _Options:
    """Stand-in for the export operator (carries options + report())."""

    apply_modifiers = True
    bake_unsupported = True
    embed_textures = False
    selection_only = False
    filepath = ""  # set in main(); the exporter derives the output dir from it

    def report(self, level, message):
        print(f"  report[{'/'.join(level)}]: {message}")


def _build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=2.0)
    obj = bpy.context.active_object
    obj.name = "TestCube"
    obj.location = (1.0, 2.0, 3.0)

    mat = bpy.data.materials.new("WetTile_Mat")
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = tree.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.35

    tex = tree.nodes.new("ShaderNodeTexImage")
    image = bpy.data.images.new("tiles_diffuse", 4, 4)
    # A path with spaces exercises inline-attribute quoting.
    image.filepath_raw = "//wet tiles/diffuse 01.png"
    tex.image = image
    tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

    # Mapping + Texture Coordinate feeding the texture exercises the Mapping
    # param whitelist (Location/Rotation/Scale) and connection chaining.
    mapping = tree.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (2.0, 2.0, 1.0)
    tex_coord = tree.nodes.new("ShaderNodeTexCoord")
    tree.links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])
    tree.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])

    # A Brick Texture (bake-only) feeding Metallic exercises the bake fallback.
    brick = tree.nodes.new("ShaderNodeTexBrick")
    tree.links.new(brick.outputs["Color"], bsdf.inputs["Metallic"])

    obj.data.materials.append(mat)
    return obj


def main():
    obj = _build_scene()
    options = _Options()

    out_path = os.path.join(tempfile.gettempdir(), "uniforge_test.unif")
    options.filepath = out_path  # exporter derives the bake/texture dir from this

    writer = UnifWriter()
    writer.write_header("test.blend")
    mesh_export.export_object(obj, writer, options)
    material_export.export_materials(obj, writer, options)

    writer.save(out_path)

    print("\n=== .unif output ===")
    print(writer.render())
    print(f"=== written to {out_path} ===")

    # Report any baked textures produced alongside the .unif.
    out_dir = os.path.dirname(out_path)
    baked = [f for f in os.listdir(out_dir) if f.endswith("_baked.png")]
    for name in baked:
        size = os.path.getsize(os.path.join(out_dir, name))
        print(f"=== baked texture: {name} ({size} bytes) ===")


if __name__ == "__main__":
    main()
