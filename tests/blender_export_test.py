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
    embed_textures = True  # self-contained .unif: textures Base64-embedded
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
    bsdf.inputs["Roughness"].default_value = 0.787
    bsdf.inputs["Alpha"].default_value = 0.448  # transparent

    # Procedural Base Color: Noise -> Color Ramp -> Base Color. Should be baked
    # to a texture and collapsed (Noise + Color Ramp must NOT appear in output).
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 5.0
    ramp = tree.nodes.new("ShaderNodeValToRGB")  # Color Ramp
    tree.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    # A Brick Texture (bake-only) feeding Metallic exercises the node bake.
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

    writer.write_embedded()  # mirrors operators._run_export
    writer.save(out_path)

    print("\n=== .unif output ===")
    print(writer.render())
    print(f"=== written to {out_path} ===")

    # With embedding on: expect [TEXTURE_EMBEDDED] blocks and NO loose PNGs.
    out_dir = os.path.dirname(out_path)
    rendered = writer.render()
    embedded_count = rendered.count("[TEXTURE_EMBEDDED")
    loose_png = [f for f in os.listdir(out_dir) if f.endswith("_baked.png")]
    print(f"=== embedded blocks: {embedded_count} ===")
    print(f"=== loose baked PNGs left (expect 0 when embedding): {len(loose_png)} {loose_png} ===")


if __name__ == "__main__":
    main()
