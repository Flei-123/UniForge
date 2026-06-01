# UniForge — Blender Addon (Exporter)

Exports meshes and shader node graphs to the `.unif` format.

## Install (development)

1. Zip the `uniforge/` folder (the zip's top-level entry must be `uniforge/`).
2. Blender → `Edit > Preferences > Add-ons > Install…` → pick the zip.
3. Enable **UniForge**.

Or symlink `uniforge/` into your Blender `scripts/addons/` for live editing.

- Blender 3.6 LTS+ (4.x recommended), Python 3.10+, no external dependencies.

## Use

- `File > Export > UniForge Asset (.unif)`, or the **UniForge** tab in the
  3D-Viewport N-Panel.

## Layout

| Path                  | Role                                            |
|-----------------------|-------------------------------------------------|
| `uniforge/__init__.py`| `bl_info`, register/unregister.                 |
| `uniforge/operators.py`| Export operator + dialog options.              |
| `uniforge/ui.py`      | N-Panel sidebar tab.                            |
| `uniforge/export/`    | mesh / materials extraction, node mapping.      |
| `uniforge/unif/`      | `.unif` writer.                                 |
