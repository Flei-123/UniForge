"""Addon preferences: the Unity export target folder + updater status.

A Blender addon may register exactly one AddonPreferences, so this is the
single home for all UniForge settings (export target + update UI).
"""

import bpy
from bpy.props import StringProperty
from bpy.types import AddonPreferences

ADDON_ID = __package__.split(".")[0]  # "uniforge", regardless of submodule depth


def get_prefs(context):
    """Return the UniForge AddonPreferences, or None if the addon isn't loaded
    through the addon system (e.g. a bare sys.path import in tests)."""
    addon = context.preferences.addons.get(ADDON_ID)
    return addon.preferences if addon else None


def _current_version():
    import uniforge

    return uniforge.bl_info["version"]


class UNIFORGE_AP_preferences(AddonPreferences):
    bl_idname = ADDON_ID

    unity_assets_path: StringProperty(
        name="Unity Assets Folder",
        description=(
            "Target folder inside your Unity project's Assets/ used by "
            "'Export to Unity'"
        ),
        subtype="DIR_PATH",
        default="",
    )

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Export to Unity", icon="EXPORT")
        box.prop(self, "unity_assets_path")
        box.label(text="One-click export drops the .unif + textures here.")

        box = layout.box()
        box.label(text="Updates", icon="FILE_REFRESH")
        version = ".".join(str(n) for n in _current_version())
        box.label(text=f"Installed version: v{version}")

        from .update import ops as update_ops

        box.operator(update_ops.UNIFORGE_OT_check_update.bl_idname, icon="FILE_REFRESH")
        if update_ops._state.get("checking"):
            box.label(text="Checking for updates…", icon="SORTTIME")
        elif update_ops._state.get("result"):
            update_ops.draw_update_status(box, update_ops._state["result"])


_classes = (UNIFORGE_AP_preferences,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
