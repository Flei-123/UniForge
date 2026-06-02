"""Material browser UI: search ambientCG, pick a material, apply to the object."""

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator, Panel

from . import ambientcg, apply

# Latest search results (list of dicts) and a kept-alive enum item list.
_results = []
_enum_items = []


def _material_items(self, context):
    _enum_items.clear()
    for result in _results:
        asset_id = result.get("id") or ""
        _enum_items.append((asset_id, asset_id, "ambientCG material"))
    if not _enum_items:
        _enum_items.append(("", "— search first —", ""))
    return _enum_items


class UNIFORGE_OT_browse_search(Operator):
    bl_idname = "uniforge.browse_search"
    bl_label = "Search"
    bl_description = "Search ambientCG for CC0 materials"

    def execute(self, context):
        query = context.scene.uniforge_browser_query
        _results[:] = ambientcg.search(query, limit=30)
        if not _results:
            self.report({"WARNING"}, "No results (check your connection or query).")
            return {"CANCELLED"}
        # Select the first result.
        context.scene.uniforge_browser_material = _results[0]["id"]
        self.report({"INFO"}, f"Found {len(_results)} materials.")
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
        except Exception as exc:  # network / IO / zip — surface, don't crash
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
            layout.prop(scene, "uniforge_browser_material", text="")
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
