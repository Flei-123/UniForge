"""UniForge — Blender → Unity asset bridge (exporter).

Registers the 'UniForge Asset (.unif)' export operator and the N-Panel UI tab.
"""

bl_info = {
    "name": "UniForge",
    "author": "Justin (Fleitec)",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "File > Export > UniForge Asset (.unif) | N-Panel > UniForge",
    "description": "Export meshes and shader node graphs to the .unif format for Unity.",
    "category": "Import-Export",
}

from . import operators, ui

# Modules exposing register()/unregister() helpers, in registration order.
_modules = (operators, ui)


def register():
    for module in _modules:
        module.register()


def unregister():
    for module in reversed(_modules):
        module.unregister()


if __name__ == "__main__":
    register()
