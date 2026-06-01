# Versioning & Roadmap

| Version | Target  | Features |
|---------|---------|----------|
| v1.0    | Q3 2026 | Core export: Mesh, UV, Normals, Transforms, PBR nodes, Image Textures, Node Connections, Material Slots, URP + HDRP support. |
| v1.1    | Q4 2026 | Embedded texture support, batch export (multiple objects), UniForge Inspector panel, import report/log. |
| v1.2    | Q1 2027 | Partial node bake fallback improvements, Custom HLSL generation for Wave / RGB Curves, progress bar for large scenes. |
| v1.5    | Q2 2027 | Skeletal armature export, keyframe animation export, shape keys / morph targets, action clip export. |
| v2.0    | Q4 2027 | Binary `.unifb` format, LOD export, collision mesh export, Godot Engine support (experimental), CLI export tool. |
| v2.5    | 2028+   | Godot stable support, Unreal Engine 5 experimental, real-time live-link (Blender ↔ Unity viewport sync). |

## v1.0 Definition of Done

- [x] Blender addon registers, appears in `File > Export` and N-Panel.
- [x] Mesh export: vertices, triangulated faces, UVs, normals.
- [x] Coordinate conversion Z-up → Y-up + winding flip.
- [x] Transform export (position / rotation / scale). *(rotation handedness pending round-trip verification)*
- [x] Node-tree walk with supported-node serialization.
- [x] Connection serialization.
- [x] Bake fallback for unsupported nodes (when enabled).
- [x] `.unif` writer produces spec-compliant output.
- [x] Unity ScriptedImporter parses `.unif`. *(parser verified standalone)*
- [~] Mesh / Material / Prefab generation. *(implemented; Shader Graph asset generation only for complex graphs — see below; untested in Unity)*
- [ ] URP + HDRP verified on Unity 2021.3 LTS and Unity 6.

## Bonus (beyond original v1.0 scope)

- [x] In-addon updater (GitHub Releases, one-click install).
- [ ] Full Shader Graph *asset* generation for procedural node networks
      (Lit material used when sufficient).
- [ ] Material browser (Poly Haven / ambientCG, CC0) — future.
