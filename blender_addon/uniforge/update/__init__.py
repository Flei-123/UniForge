"""In-addon update checking & one-click install (GitHub Releases backed).

Split so the version/network logic in ``core`` stays importable and testable
without Blender; ``ops`` holds the bpy operators and preferences UI.
"""
