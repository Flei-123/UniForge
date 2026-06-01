"""N-Panel sidebar tab: View3D > Sidebar (N) > UniForge."""

import bpy
from bpy.types import Panel


class UNIFORGE_PT_panel(Panel):
    bl_label = "UniForge"
    bl_idname = "UNIFORGE_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UniForge"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Blender → Unity bridge")
        layout.operator("uniforge.export", icon="EXPORT")

        col = layout.column(align=True)
        col.label(text=f"Scene meshes: {_mesh_count(context)}")


def _mesh_count(context):
    return sum(1 for obj in context.scene.objects if obj.type == "MESH")


_classes = (UNIFORGE_PT_panel,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
