# UniForge — Unity Plugin (Importer)

A C# Editor plugin that registers a `ScriptedImporter` for `.unif` files: any
`.unif` dropped into `Assets/` is auto-converted into Mesh, Shader Graph,
Material, and Prefab assets.

## Install (development)

Add the package to a Unity project via `Packages/manifest.json`:

```json
"com.fleitec.uniforge": "file:../../UniForge/unity_plugin/com.fleitec.uniforge"
```

Or copy `com.fleitec.uniforge/` into the project's `Packages/` folder.

- Unity 2021.3 LTS+ (incl. Unity 6). Requires the Shader Graph package
  (`com.unity.shadergraph`). URP (primary) / HDRP (secondary).

## Layout (`com.fleitec.uniforge/Editor/`)

| File                     | Role                                          |
|--------------------------|-----------------------------------------------|
| `UnifImporter.cs`        | ScriptedImporter entry point.                 |
| `UnifParser.cs`          | `.unif` text → `UnifDocument`.                |
| `UnifDocument.cs`        | In-memory model (mesh/material/node/connection). |
| `MeshBuilder.cs`         | Geometry → `UnityEngine.Mesh`.                |
| `ShaderGraphBuilder.cs`  | Nodes → Shader Graph + Material.              |
| `NodeMap.cs`             | `.unif` node type → Unity equivalent + status.|
| `UniForgeInspector.cs`   | Custom importer inspector.                     |
