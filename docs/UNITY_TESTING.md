# Unity Roundtrip Testing

How to verify the full Blender → `.unif` → Unity pipeline. The parser is already
verified standalone; this checks mesh/material/prefab generation inside a real
Unity Editor (the part that needs Unity's assemblies).

## Prerequisites

- Unity **2021.3 LTS or newer** (Unity 6 also fine) with a **URP** project
  (URP is primary; HDRP is the secondary target).
- The Shader Graph package (`com.unity.shadergraph`) — included by default in
  URP projects.

## 1. Install the UniForge package

Add to the Unity project's `Packages/manifest.json`:

```json
"com.fleitec.uniforge": "file:<absolute-path>/UniForge/unity_plugin/com.fleitec.uniforge"
```

(Windows paths: use forward slashes, e.g. `file:C:/Users/justi/Dev/UniForge/unity_plugin/com.fleitec.uniforge`.)

Unity compiles the `UniForge.Editor` assembly. Check the Console for compile
errors before continuing.

## 2. Produce a test asset

Either export from Blender (the addon, or `tests/blender_export_test.py`), or
use the bundled [samples/FloorTile.unif](../samples/FloorTile.unif).

The sample references `tiles_diffuse.png`. Drop a small PNG named
`tiles_diffuse.png` next to the `.unif` so the texture-resolution path is
exercised (any image works).

## 3. Import

Copy `FloorTile.unif` (+ `tiles_diffuse.png`) into the project's `Assets/`
folder. UniForge's ScriptedImporter runs automatically.

## 4. What to verify

- [ ] The `.unif` imports without errors; a **Mesh**, **Material**, and
      **Prefab** sub-asset appear under it.
- [ ] Dragging the prefab into the scene shows the mesh, correctly oriented
      (Y-up, front faces — confirms the coordinate/winding conversion).
- [ ] The material is a **URP/Lit** instance (no custom shader created for the
      simple PBR case) with:
  - Base Color set, Metallic/Smoothness mapped (smoothness = 1 − roughness),
  - the base color texture assigned to `_BaseMap`.
- [ ] For a material with a procedural node (e.g. add a Noise Texture in
      Blender), the Console shows a warning that full Shader Graph
      reconstruction is pending and a Lit placeholder was created.
- [ ] For a baked node (Brick/SSS with bake enabled), the baked PNG is
      referenced and loads.

## 5. Driving the test via MCP (optional)

If the Unity Editor is open with the MCP for Unity bridge connected, the test
can be driven programmatically (create the URP scene, trigger import, inspect
the generated assets and Console). Open Unity, ensure the bridge shows as
connected, then ask to run the roundtrip.

## Known caveats to watch for

- **Rotation handedness**: position/scale conversion is verified; Euler
  rotation parity is still pending round-trip confirmation (see ROADMAP).
- **Render pipeline**: property names differ between URP Lit and Built-in
  Standard — the builder sets both (`_BaseColor`/`_Color`, `_BaseMap`/`_MainTex`,
  `_Smoothness`/`_Glossiness`). HDRP Lit is not yet verified.
