# UniForge

**Blender → Unity Asset Bridge**
Preserve Blender Shader Node Graphs as Unity Shader Graph materials via the
`.unif` (Universal Node-based Interchange Format).

Where FBX/GLTF discard shader logic, UniForge reads, encodes, and faithfully
reconstructs it on the Unity side.

## Repository layout

```
UniForge/
├── blender_addon/          Python addon — the exporter (writes .unif)
│   └── uniforge/
│       ├── __init__.py     bl_info + register/unregister
│       ├── operators.py    File > Export operator
│       ├── ui.py           N-Panel sidebar tab
│       ├── export/         mesh / material / node-tree extraction
│       └── unif/           .unif writer
├── unity_plugin/           C# plugin — the importer (reads .unif)
│   └── com.fleitec.uniforge/
│       └── Editor/         ScriptedImporter, parser, builders, inspector
├── docs/                   format spec + node-mapping reference
├── samples/                example .unif files
└── README.md
```

## Components

| Component        | Tech                                   | Role                          |
|------------------|----------------------------------------|-------------------------------|
| Blender Addon    | Python 3.10+, `bpy`, stdlib only       | Export scene → `.unif`        |
| Unity Plugin     | C# 9, `UnityEditor`, ShaderGraph API   | Auto-import `.unif` → assets  |

## Status

`v1.0` in development — see [docs/ROADMAP.md](docs/ROADMAP.md).

Scope for v1.0: Mesh, UVs, Normals, Transforms, PBR nodes, Image Textures,
node connections, material slots, URP + HDRP.

## License

Commercial — Single Developer License. See [LICENSE](LICENSE).
