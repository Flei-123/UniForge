"""Export operator: File > Export > UniForge Asset (.unif)."""

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from .export import mesh as mesh_export
from .export import materials as material_export
from .unif.writer import UnifWriter


class UNIFORGE_OT_export(Operator, ExportHelper):
    """Export the scene (or selection) to a .unif file."""

    bl_idname = "uniforge.export"
    bl_label = "UniForge Asset (.unif)"
    bl_options = {"PRESET"}

    filename_ext = ".unif"
    filter_glob: StringProperty(default="*.unif", options={"HIDDEN"})

    # --- Export dialog options (see docs/FORMAT.md, spec §4.2) ---
    selection_only: BoolProperty(
        name="Export Selection Only",
        description="Export only selected objects instead of the entire scene",
        default=False,
    )
    embed_textures: BoolProperty(
        name="Embed Textures",
        description="Base64-encode textures into the .unif file",
        default=False,
    )
    bake_unsupported: BoolProperty(
        name="Bake Unsupported Nodes",
        description="Auto-bake nodes without a Unity equivalent to a texture",
        default=True,
    )
    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply all modifiers before exporting the mesh",
        default=True,
    )
    coordinate_system: EnumProperty(
        name="Coordinate System",
        description="Target coordinate system",
        items=[("UNITY", "Unity (Y-up)", "Convert Blender Z-up to Unity Y-up")],
        default="UNITY",
    )

    def execute(self, context):
        objects = (
            context.selected_objects if self.selection_only else context.scene.objects
        )
        meshes = [obj for obj in objects if obj.type == "MESH" and obj.material_slots]

        if not meshes:
            self.report({"WARNING"}, "No mesh objects with material slots to export.")
            return {"CANCELLED"}

        writer = UnifWriter(generator="UniForge Blender Addon 1.0")
        writer.write_header(source_file=bpy.path.basename(bpy.data.filepath))

        for obj in meshes:
            mesh_export.export_object(obj, writer, options=self)
            material_export.export_materials(obj, writer, options=self)

        writer.save(self.filepath)
        self.report({"INFO"}, f"Exported {len(meshes)} object(s) to {self.filepath}")
        return {"FINISHED"}


def _menu_func_export(self, context):
    self.layout.operator(UNIFORGE_OT_export.bl_idname, text="UniForge Asset (.unif)")


_classes = (UNIFORGE_OT_export,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_export.append(_menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(_menu_func_export)
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
