"""Blender operators + preferences for the in-addon updater."""

import shutil
import tempfile
import threading
import urllib.request

import bpy
from bpy.types import Operator

from . import core

_PACKAGE = __package__.split(".")[0]  # the installed addon module ("uniforge")

# Cached result of the most recent check, shared with the UI. Written by the
# background thread / check operator; only ever read on the main thread.
_state = {
    "checked": False,
    "checking": False,
    "result": None,  # dict from core.check_for_update
}


def _current_version():
    import uniforge  # the addon package; bl_info is defined at its top level

    return uniforge.bl_info["version"]


def _run_check(version_tuple):
    """Network check; safe to run off the main thread (touches no bpy data)."""
    _state["checking"] = True
    try:
        _state["result"] = core.check_for_update(version_tuple)
        _state["checked"] = True
    finally:
        _state["checking"] = False
    _tag_redraw()


def _tag_redraw():
    """Ask the 3D-Viewport sidebar to repaint so a finished check shows up."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def start_background_check():
    """Kick off a one-shot, non-blocking update check (used on register)."""
    if _state["checking"] or _state["checked"]:
        return
    version = _current_version()
    thread = threading.Thread(target=_run_check, args=(version,), daemon=True)
    thread.start()


class UNIFORGE_OT_check_update(Operator):
    bl_idname = "uniforge.check_update"
    bl_label = "Check for Updates"
    bl_description = "Check GitHub for a newer UniForge release"

    def execute(self, context):
        result = core.check_for_update(_current_version())
        _state["result"] = result
        _state["checked"] = True

        if result["error"]:
            self.report({"WARNING"}, f"Update check failed: {result['error']}")
        elif result["available"]:
            self.report({"INFO"}, f"Update available: v{result['latest']}")
        else:
            self.report({"INFO"}, "UniForge is up to date.")
        return {"FINISHED"}


class UNIFORGE_OT_install_update(Operator):
    bl_idname = "uniforge.install_update"
    bl_label = "Download & Install Update"
    bl_description = "Download the latest release and install it over this addon"

    def execute(self, context):
        result = _state.get("result")
        if not result or not result.get("url"):
            self.report({"WARNING"}, "No update download is available.")
            return {"CANCELLED"}

        try:
            archive = _download(result["url"])
        except Exception as exc:  # network/IO — surface, don't crash the UI
            self.report({"ERROR"}, f"Download failed: {exc}")
            return {"CANCELLED"}

        bpy.ops.preferences.addon_install(overwrite=True, filepath=archive)
        bpy.ops.preferences.addon_enable(module=_PACKAGE)
        self.report(
            {"INFO"},
            f"UniForge v{result['latest']} installed — restart Blender to finish.",
        )
        return {"FINISHED"}


def _download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "UniForge-Updater"})
    fd, path = tempfile.mkstemp(suffix=".zip", prefix="uniforge_update_")
    with urllib.request.urlopen(request, timeout=60) as response, open(path, "wb") as out:
        shutil.copyfileobj(response, out)
    import os

    os.close(fd)
    return path


def draw_update_status(layout, result):
    """Shared status block used by both the preferences and the N-Panel."""
    if result.get("error"):
        layout.label(text=result["error"], icon="ERROR")
    elif result.get("available"):
        box = layout.box()
        box.label(text=f"Update available: v{result['latest']}", icon="IMPORT")
        box.operator(UNIFORGE_OT_install_update.bl_idname, icon="IMPORT")
        if result.get("notes"):
            col = box.column(align=True)
            for line in result["notes"].splitlines()[:6]:
                col.label(text=line)
    else:
        layout.label(text="Up to date", icon="CHECKMARK")


_classes = (
    UNIFORGE_OT_check_update,
    UNIFORGE_OT_install_update,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    start_background_check()


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
