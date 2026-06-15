"""Material browser UI: search ambientCG, preview thumbnails, apply to object."""

import os
import tempfile

import bpy
import bpy.utils.previews
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator, Panel

from . import ambientcg, apply

# Latest search results (list of dicts), a preview-icon collection, and a
# kept-alive enum item list (Blender requires the strings to stay referenced).
_results = []
_previews = None
_enum_items = []


def _get_previews():
    global _previews
    if _previews is None:
        _previews = bpy.utils.previews.new()
    return _previews


def _material_items(self, context):
    """Visual enum items (id, label, desc, icon, index) for template_icon_view."""
    _enum_items.clear()
    pcoll = _get_previews()
    for index, result in enumerate(_results):
        asset_id = result.get("id") or ""
        icon = pcoll[asset_id].icon_id if asset_id in pcoll else 0
        _enum_items.append((asset_id, asset_id, asset_id, icon, index))
    if not _enum_items:
        _enum_items.append(("", "search first", "", 0, 0))
    return _enum_items


class UNIFORGE_OT_browse_search(Operator):
    bl_idname = "uniforge.browse_search"
    bl_label = "Search"
    bl_description = "Search ambientCG for CC0 materials (downloads preview thumbnails)"

    def execute(self, context):
        query = context.scene.uniforge_browser_query
        results = ambientcg.search(query, limit=24)
        if not results:
            self.report({"WARNING"}, "No results (check your connection or query).")
            return {"CANCELLED"}

        # Download preview thumbnails into the icon collection.
        pcoll = _get_previews()
        pcoll.clear()
        tmp = tempfile.mkdtemp(prefix="uniforge_thumbs_")
        for result in results:
            url = result.get("preview")
            asset_id = result.get("id")
            if not url or not asset_id:
                continue
            path = os.path.join(tmp, asset_id + ".png")
            try:
                ambientcg.download(url, path, timeout=20)
                pcoll.load(asset_id, path, "IMAGE")
            except Exception:
                pass  # missing thumbnail just shows no icon

        _results[:] = results
        context.scene.uniforge_browser_material = results[0]["id"]
        self.report({"INFO"}, f"Found {len(results)} materials.")
        return {"FINISHED"}


class UNIFORGE_OT_browse_apply(Operator):
    bl_idname = "uniforge.browse_apply"
    bl_label = "Download & Apply"
    bl_description = "Download the selected material and apply it to the active object"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        selected = context.scene.uniforge_browser_material
        result = next((r for r in _results if r.get("id") == selected), None)
        if result is None:
            self.report({"WARNING"}, "Select a material (search first).")
            return {"CANCELLED"}

        resolution = context.scene.uniforge_browser_resolution
        try:
            material = apply.download_and_apply(result, resolution, context.active_object)
        except Exception as exc:
            self.report({"ERROR"}, f"Download failed: {exc}")
            return {"CANCELLED"}

        if material is None:
            self.report({"WARNING"}, "No usable textures in the downloaded set.")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Applied '{material.name}' to {context.active_object.name}.")
        return {"FINISHED"}


class UNIFORGE_PT_browser(Panel):
    bl_label = "Material Browser (CC0)"
    bl_idname = "UNIFORGE_PT_browser"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UniForge"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row(align=True)
        row.prop(scene, "uniforge_browser_query", text="", icon="VIEWZOOM")
        row.operator(UNIFORGE_OT_browse_search.bl_idname, text="", icon="VIEWZOOM")

        if _results:
            # Visual thumbnail grid.
            layout.template_icon_view(
                scene, "uniforge_browser_material", show_labels=True, scale=6.0, scale_popup=5.0
            )
            layout.label(text=scene.uniforge_browser_material)
        else:
            layout.label(text="Search for materials (e.g. metal, wood, concrete)")

        layout.prop(scene, "uniforge_browser_resolution", text="Resolution")
        col = layout.column()
        col.enabled = bool(_results) and UNIFORGE_OT_browse_apply.poll(context)
        col.operator(UNIFORGE_OT_browse_apply.bl_idname, icon="IMPORT")
        if context.active_object is None or context.active_object.type != "MESH":
            layout.label(text="Select a mesh object", icon="INFO")
        layout.label(text="Materials are CC0 (ambientcg.com)")


_classes = (
    UNIFORGE_OT_browse_search,
    UNIFORGE_OT_browse_apply,
    UNIFORGE_PT_browser,
)


def register():
    bpy.types.Scene.uniforge_browser_query = StringProperty(
        name="Search", description="Search term for ambientCG materials", default=""
    )
    bpy.types.Scene.uniforge_browser_material = EnumProperty(
        name="Material", description="Material to apply", items=_material_items
    )
    bpy.types.Scene.uniforge_browser_resolution = EnumProperty(
        name="Resolution",
        description="Texture resolution to download",
        items=[("1K", "1K", ""), ("2K", "2K", ""), ("4K", "4K", "")],
        default="1K",
    )
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.uniforge_browser_query
    del bpy.types.Scene.uniforge_browser_material
    del bpy.types.Scene.uniforge_browser_resolution
    global _previews
    if _previews is not None:
        bpy.utils.previews.remove(_previews)
        _previews = None
    _results.clear()
