# The `.unif` File Format

`.unif` = **Universal Node-based Interchange Format**. A structured, text-based
format (JSON-like, custom syntax) designed to be human-readable during
development and parseable by both Python and C#.

A binary variant (`.unifb`) is planned for v2.0 to reduce file size.

## Structure

A `.unif` file is a sequence of **named blocks** enclosed in square brackets.
Each block holds key-value pairs (`key: value`) or nested sub-blocks.

```unif
[UNIF]
  version: 1.0
  generator: UniForge Blender Addon 1.0
  source_file: tiles.blend

[MESH]
  name: FloorTile
  vertices: [0.5,0.0,0.5, -0.5,0.0,0.5, ...]
  faces: [0,1,2, 2,3,0, ...]
  uvs: [0.0,0.0, 1.0,0.0, ...]
  normals: [0.0,1.0,0.0, ...]

[TRANSFORM]
  position: 0.0, 0.0, 0.0
  rotation: 0.0, 0.0, 0.0
  scale: 1.0, 1.0, 1.0

[MATERIAL]
  name: WetTile_Mat
  slot: 0
  [NODE PrincipledBSDF id=0]
    roughness: 0.35
  [NODE ImageTexture id=1 path=tiles_diffuse.png]
  [CONNECTION]
    1.Color -> 0.Base_Color
```

## Blocks

| Block                  | Cardinality | Purpose                                            |
|------------------------|-------------|----------------------------------------------------|
| `[UNIF]`               | once        | Header: format version, generator, source file.    |
| `[OBJECT name=…]`      | per object  | Groups the mesh/transform/materials of one object. |
| `[MESH]`               | per object  | Geometry: vertices, faces, uvs, normals, submeshes.|
| `[TRANSFORM]`          | per object  | position / rotation / scale (Unity Y-up space).    |
| `[MATERIAL]`           | per slot    | Material name + slot index, contains NODE blocks.  |
| `[NODE <Type> id=N …]` | per node    | One shader node. Inline attrs + key-value params.  |
| `[CONNECTION]`         | per material| Edges: `srcId.Socket -> dstId.Socket`.             |
| `[TEXTURE_EMBEDDED]`   | optional    | Base64-encoded texture for self-contained files.   |

A file may contain multiple `[OBJECT]` blocks; each owns the `[MESH]` /
`[TRANSFORM]` / `[MATERIAL]` blocks that follow it until the next `[OBJECT]`.
Files with no `[OBJECT]` block are treated as one implicit object (legacy
single-object form). `[MESH]` may carry a `submeshes: [c0,c1,…]` triangle-count
list (faces are ordered by material slot) for multi-material meshes.

### `[NODE]` syntax

```
[NODE <BlenderType> id=<int> [key=value ...]]
  <param>: <value>
```

- `id` is unique within the material and referenced by connections.
- Inline attributes (e.g. `path=tiles_diffuse.png`) sit on the header line.
- Indented `key: value` lines are node parameters (e.g. `roughness: 0.35`).

#### Inline attribute quoting

Inline attribute values are space-delimited on the header line. A value that
contains whitespace, `=`, `]`, or is empty is **double-quoted**; literal `"`
and `\` inside are backslash-escaped. Parsers must accept both forms:

```
[NODE ImageTexture id=1 path=tiles_diffuse.png]
[NODE ImageTexture id=2 path="wet tiles/diffuse 01.png"]
```

### `[CONNECTION]` syntax

```
<srcId>.<SocketName> -> <dstId>.<SocketName>
```

Socket names use the Unity-side naming (e.g. `Base_Color`), mapped from the
Blender socket during export.

## Textures

By default textures are referenced by **relative path** (and copied next to the
`.unif` on export). With the *Embed Textures* option, each texture — including
baked ones — is Base64-encoded into a `[TEXTURE_EMBEDDED]` block for a single
self-contained file (larger size, no loose files).

```
[TEXTURE_EMBEDDED name=tiles_diffuse.png format=png]
  data: iVBORw0KGgoAAAANSUhEUgAA…
```

- `name` matches an Image Texture node's `path` attribute (the linkage key);
  it is quoted when it contains spaces.
- `format` is the file extension (`png`, `jpg`, …).
- `data` is the Base64 of the raw image file bytes, on one line.

The importer prefers an embedded texture over a same-named file on disk, and
registers it as a sub-asset of the imported `.unif`.

## Coordinate system

The exporter converts Blender **Z-up** to Unity **Y-up** and flips triangle
winding so meshes render with correct normals in Unity.
