# UniForge — Blender Addon (Exporter)

Exports meshes and shader node graphs to the `.unif` format.

## Install (development)

1. Zip the `uniforge/` folder (the zip's top-level entry must be `uniforge/`).
2. Blender → `Edit > Preferences > Add-ons > Install…` → pick the zip.
3. Enable **UniForge**.

Or symlink `uniforge/` into your Blender `scripts/addons/` for live editing.

- Blender 3.6 LTS+ (4.x recommended), Python 3.10+, no external dependencies.

## Use

- **Export:** `File > Export > UniForge Asset (.unif)`, or the **UniForge** tab
  in the 3D-Viewport N-Panel (incl. one-click *Export to Unity*).
- **Import:** `File > Import > UniForge Asset (.unif)` — rebuilds objects,
  hierarchy, transforms and materials (with embedded textures) back into
  Blender, so the bridge round-trips.

## Layout

| Path                  | Role                                            |
|-----------------------|-------------------------------------------------|
| `uniforge/__init__.py`| `bl_info`, register/unregister.                 |
| `uniforge/operators.py`| Export operator + dialog options.              |
| `uniforge/ui.py`      | N-Panel sidebar tab.                            |
| `uniforge/export/`    | mesh / materials extraction, node mapping.      |
| `uniforge/unif/`      | `.unif` writer.                                 |
| `uniforge/update/`    | in-addon updater (GitHub Releases).             |
| `uniforge/browser/`   | CC0 material browser (ambientCG).               |

## Material browser

N-Panel → **UniForge** → *Material Browser (CC0)*: search ambientCG, pick a
material + resolution, and **Download & Apply** builds a PBR material (Base
Color / Roughness / Metallic / Normal) and assigns it to the active mesh. All
ambientCG materials are CC0 (free for any use). Textures download next to the
`.blend` (or to a temp folder if unsaved).
