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

- [ ] Blender addon registers, appears in `File > Export` and N-Panel.
- [ ] Mesh export: vertices, triangulated faces, UVs, normals.
- [ ] Coordinate conversion Z-up → Y-up + winding flip.
- [ ] Transform export (position / rotation / scale).
- [ ] Node-tree walk with supported-node serialization.
- [ ] Connection serialization.
- [ ] Bake fallback for unsupported nodes (when enabled).
- [ ] `.unif` writer produces spec-compliant output.
- [ ] Unity ScriptedImporter parses `.unif`.
- [ ] Mesh / ShaderGraph / Material / Prefab generation.
- [ ] URP + HDRP verified on Unity 2021.3 LTS and Unity 6.
