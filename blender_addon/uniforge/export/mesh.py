"""Mesh geometry extraction and Blender (Z-up) → Unity (Y-up) conversion.

Pipeline (spec §4.3, steps 1-5):
  1. Validate object (done by caller).
  2. Apply modifiers via evaluated depsgraph (if enabled).
  3. Triangulate and extract vertices / faces / UVs / normals.
  4. Convert coordinate system (Z-up → Y-up, flip winding).
  5. Extract transform.
"""


def export_object(obj, writer, options):
    """Serialize ``obj``'s geometry and transform into ``writer``.

    TODO(v1.0):
      - Evaluate depsgraph + apply modifiers when ``options.apply_modifiers``.
      - Triangulate via bmesh; collect verts/loops/uvs/normals.
      - Convert each vector Z-up → Y-up: (x, y, z) -> (x, z, y); flip winding.
      - Emit [MESH] and [TRANSFORM] blocks.
    """
    raise NotImplementedError("mesh.export_object — implemented in the exporter milestone")


def blender_to_unity_vector(vec):
    """Convert a Blender Z-up vector to Unity Y-up: (x, y, z) -> (x, z, y)."""
    x, y, z = vec
    return (x, z, y)
