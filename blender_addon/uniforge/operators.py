"""Export operators: File > Export dialog and one-click 'Export to Unity'."""

import os

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from . import preferences
from .export import materials as material_export
from .export import mesh as mesh_export
from .unif.writer import UnifWriter

# Shared export-option properties, mixed into both export operators so the
# export pipeline can read them (and report()) off a single `operator` object.
_EXPORT_PROPS = {
    "selection_only": BoolProperty(
        name="Export Selection Only",
        description="Export only selected objects instead of the entire scene",
        default=False,
    ),
    "embed_textures": BoolProperty(
        name="Embed Textures",
        description="Base64-encode textures into the .unif file (self-contained, no loose files)",
        default=True,
    ),
    "bake_unsupported": BoolProperty(
        name="Bake Unsupported Nodes",
        description="Auto-bake unsupported / procedural nodes to textures",
        default=True,
    ),
    "apply_modifiers": BoolProperty(
        name="Apply Modifiers",
        description="Apply all modifiers before exporting the mesh",
        default=True,
    ),
}


def _run_export(operator, context):
    """Run the export pipeline using ``operator`` as the option carrier.

    ``operator`` must expose the _EXPORT_PROPS flags, a ``filepath``, and
    ``report()``. Returns the number of exported objects, or -1 on failure.
    """
    objects = (
        context.selected_objects if operator.selection_only else context.scene.objects
    )
    meshes = [obj for obj in objects if obj.type == "MESH" and obj.material_slots]
    if not meshes:
        operator.report({"WARNING"}, "No mesh objects with material slots to export.")
        return -1

    writer = UnifWriter(generator="UniForge Blender Addon 1.0")
    writer.write_header(source_file=bpy.path.basename(bpy.data.filepath))

    for obj in meshes:
        mesh_export.export_object(obj, writer, options=operator)
        material_export.export_materials(obj, writer, options=operator)

    writer.write_embedded()  # no-op unless 'Embed Textures' queued any
    writer.save(operator.filepath)
    return len(meshes)


class UNIFORGE_OT_export(Operator, ExportHelper):
    """Export the scene (or selection) to a .unif file."""

    bl_idname = "uniforge.export"
    bl_label = "UniForge Asset (.unif)"
    bl_options = {"PRESET"}

    filename_ext = ".unif"
    filter_glob: StringProperty(default="*.unif", options={"HIDDEN"})

    selection_only: _EXPORT_PROPS["selection_only"]
    embed_textures: _EXPORT_PROPS["embed_textures"]
    bake_unsupported: _EXPORT_PROPS["bake_unsupported"]
    apply_modifiers: _EXPORT_PROPS["apply_modifiers"]
    coordinate_system: EnumProperty(
        name="Coordinate System",
        description="Target coordinate system",
        items=[("UNITY", "Unity (Y-up)", "Convert Blender Z-up to Unity Y-up")],
        default="UNITY",
    )

    def execute(self, context):
        count = _run_export(self, context)
        if count < 0:
            return {"CANCELLED"}
        self.report({"INFO"}, f"Exported {count} object(s) to {self.filepath}")
        return {"FINISHED"}


class UNIFORGE_OT_export_to_unity(Operator):
    """Export directly into the configured Unity project folder."""

    bl_idname = "uniforge.export_to_unity"
    bl_label = "Export to Unity"
    bl_description = "Export the scene straight into the configured Unity Assets folder"

    selection_only: _EXPORT_PROPS["selection_only"]
    embed_textures: _EXPORT_PROPS["embed_textures"]
    bake_unsupported: _EXPORT_PROPS["bake_unsupported"]
    apply_modifiers: _EXPORT_PROPS["apply_modifiers"]

    # Set by execute() before running the shared pipeline.
    filepath: StringProperty(subtype="FILE_PATH", options={"HIDDEN"})

    def execute(self, context):
        prefs = preferences.get_prefs(context)
        folder = bpy.path.abspath(prefs.unity_assets_path) if prefs else ""
        if not folder or not folder.strip():
            self.report(
                {"ERROR"},
                "No Unity folder configured — set it in the UniForge panel or Preferences.",
            )
            return {"CANCELLED"}
        if not os.path.isdir(folder):
            self.report({"ERROR"}, f"Unity folder does not exist: {folder}")
            return {"CANCELLED"}

        blend_name = os.path.splitext(bpy.path.basename(bpy.data.filepath))[0] or "scene"
        self.filepath = os.path.join(folder, blend_name + ".unif")

        count = _run_export(self, context)
        if count < 0:
            return {"CANCELLED"}
        self.report({"INFO"}, f"Exported {count} object(s) to Unity: {self.filepath}")
        return {"FINISHED"}


def _menu_func_export(self, context):
    self.layout.operator(UNIFORGE_OT_export.bl_idname, text="UniForge Asset (.unif)")


_classes = (UNIFORGE_OT_export, UNIFORGE_OT_export_to_unity)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_export.append(_menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(_menu_func_export)
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
