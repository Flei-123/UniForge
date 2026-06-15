"""Export operator: File > Export > UniForge Asset (.unif)."""

import os

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from . import preferences
from .export import materials as material_export
from .export import mesh as mesh_export
from .unif.writer import UnifWriter

# Export-option properties shown in the File > Export dialog sidebar.
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
    "smart_uv": BoolProperty(
        name="Smart UV Unwrap",
        description=(
            "Re-unwrap with Smart UV Project before baking (non-destructive). "
            "Recommended for procedural materials so baked textures map cleanly"
        ),
        default=False,
    ),
    "recalc_normals": BoolProperty(
        name="Recalculate Normals",
        description=(
            "Recompute outward-facing normals on the exported mesh "
            "(non-destructive; fixes inverted/inconsistent faces)"
        ),
        default=False,
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

    # Include parent chains (e.g. empties) as transform-only objects so the
    # hierarchy survives even when a mesh is parented to a non-mesh object.
    scene_objects = set(context.scene.objects)
    export_set = set(meshes)
    for mesh_obj in meshes:
        ancestor = mesh_obj.parent
        while ancestor is not None and ancestor in scene_objects and ancestor not in export_set:
            export_set.add(ancestor)
            ancestor = ancestor.parent

    # Keep scene order; the importer resolves parents by name regardless.
    export_list = [obj for obj in context.scene.objects if obj in export_set]
    for obj in export_list:
        parent = obj.parent if obj.parent in export_set else None
        writer.begin_object(obj.name, parent.name if parent else None)

        if obj.type == "MESH" and obj.material_slots:
            # Smart-UV-project (temporarily) so baked textures map cleanly; the
            # same active UV layer feeds both mesh export and baking.
            restore_uv = mesh_export.apply_smart_uv(obj) if operator.smart_uv else None
            try:
                mesh_export.export_object(obj, writer, options=operator, parent=parent)
                material_export.export_materials(obj, writer, options=operator)
            finally:
                if restore_uv is not None:
                    restore_uv()
        else:
            # Empty / non-mesh parent: transform only, so children keep their place.
            mesh_export.export_transform_only(obj, writer, parent=parent)

    writer.write_embedded()  # no-op unless 'Embed Textures' queued any
    writer.save(operator.filepath)
    return len(export_list)


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
    smart_uv: _EXPORT_PROPS["smart_uv"]
    recalc_normals: _EXPORT_PROPS["recalc_normals"]
    coordinate_system: EnumProperty(
        name="Coordinate System",
        description="Target coordinate system",
        items=[("UNITY", "Unity (Y-up)", "Convert Blender Z-up to Unity Y-up")],
        default="UNITY",
    )

    def invoke(self, context, event):
        # Pre-fill the dialog with the saved export path when enabled; otherwise
        # fall back to Blender's normal "Export As" location.
        prefs = preferences.get_prefs(context)
        if prefs and prefs.use_saved_path and prefs.export_path.strip():
            folder = bpy.path.abspath(prefs.export_path)
            base = os.path.splitext(bpy.path.basename(bpy.data.filepath))[0] or "untitled"
            self.filepath = os.path.join(folder, base + ".unif")
        return ExportHelper.invoke(self, context, event)

    def execute(self, context):
        count = _run_export(self, context)
        if count < 0:
            return {"CANCELLED"}
        self.report({"INFO"}, f"Exported {count} object(s) to {self.filepath}")
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
