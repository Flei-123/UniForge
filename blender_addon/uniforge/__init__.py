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

def _modules():
    """Modules exposing register()/unregister(), in registration order.

    Imported lazily so that bpy-free submodules (e.g. uniforge.unif.writer)
    stay importable — and unit-testable — outside of Blender.
    """
    from . import import_op, operators, preferences, ui
    from .browser import ops as browser_ops
    from .update import ops as update_ops

    return (preferences, operators, import_op, ui, update_ops, browser_ops)


def register():
    for module in _modules():
        module.register()


def unregister():
    for module in reversed(_modules()):
        module.unregister()


if __name__ == "__main__":
    register()
