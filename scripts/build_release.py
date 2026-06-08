"""Build a versioned release zip of the UniForge Blender addon.

Reads the version from the addon's bl_info and writes
``dist/UniForge-<version>.zip`` (top-level folder: ``uniforge/``).

Usage:
    python scripts/build_release.py
"""

import os
import re
import zipfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON = os.path.join(_ROOT, "blender_addon", "uniforge")
_INIT = os.path.join(_ADDON, "__init__.py")


def read_version():
    """Parse the ``"version": (x, y, z)`` tuple from bl_info."""
    with open(_INIT, encoding="utf-8") as f:
        text = f.read()
    match = re.search(r'"version"\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', text)
    if not match:
        raise SystemExit("Could not find a version tuple in bl_info.")
    return ".".join(match.groups())


def build(version):
    dist = os.path.join(_ROOT, "dist")
    os.makedirs(dist, exist_ok=True)
    out = os.path.join(dist, f"UniForge-{version}.zip")

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, _dirs, files in os.walk(_ADDON):
            for name in files:
                if "__pycache__" in root or name.endswith(".pyc"):
                    continue
                full = os.path.join(root, name)
                arc = os.path.join("uniforge", os.path.relpath(full, _ADDON))
                archive.write(full, arc)
    return out


def main():
    version = read_version()
    out = build(version)
    size_kb = os.path.getsize(out) // 1024
    print(f"Built {out} ({size_kb} KB) — tag this release 'v{version}' on GitHub.")


if __name__ == "__main__":
    main()
