"""Mesh geometry extraction and Blender (Z-up) → Unity (Y-up) conversion.

Pipeline (spec §4.3, steps 1-5):
  1. Validate object (done by caller).
  2. Apply modifiers via evaluated depsgraph (if enabled).
  3. Triangulate and extract vertices / faces / UVs / normals.
  4. Convert coordinate system (Z-up → Y-up, flip winding).
  5. Extract transform.

Geometry is exported *per loop* (one vertex per triangle corner) rather than
deduplicated. This keeps the parallel vertices/normals/uvs arrays trivially
consistent with the face index list — matching how the Unity MeshBuilder reads
them — and preserves split normals and UV seams exactly. Deduplication is a
later optimization (see docs/ROADMAP.md).
"""

import math

import bpy


def export_object(obj, writer, options):
    """Serialize ``obj``'s geometry and transform into ``writer``."""
    mesh, owner = _evaluated_mesh(obj, options)
    try:
        vertices, faces, uvs, normals = _extract_geometry(mesh)
    finally:
        owner.to_mesh_clear()

    writer.write_mesh(obj.name, vertices, faces, uvs, normals)
    _write_transform(obj, writer)


def blender_to_unity_vector(vec):
    """Convert a Blender Z-up vector to Unity Y-up: (x, y, z) -> (x, z, y)."""
    x, y, z = vec
    return (x, z, y)


# --- internals ------------------------------------------------------------
def _evaluated_mesh(obj, options):
    """Return ``(mesh, owner)``; ``owner.to_mesh_clear()`` frees the temp mesh.

    With *Apply Modifiers* the mesh is taken from the depsgraph-evaluated
    object so all modifiers are baked in; otherwise the raw object mesh.
    """
    if options.apply_modifiers:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        owner = obj.evaluated_get(depsgraph)
    else:
        owner = obj
    return owner.to_mesh(), owner


def _extract_geometry(mesh):
    """Triangulate, convert axes, and return flat (vertices, faces, uvs, normals)."""
    if hasattr(mesh, "calc_normals_split"):
        # Required for split_normals on Blender < 4.1; a no-op concept on 4.1+.
        mesh.calc_normals_split()
    mesh.calc_loop_triangles()

    uv_data = mesh.uv_layers.active.data if mesh.uv_layers.active else None

    vertices = []
    normals = []
    uvs = []
    faces = []
    corner = 0

    for tri in mesh.loop_triangles:
        corners = []
        for slot in range(3):
            loop_index = tri.loops[slot]
            co = mesh.vertices[tri.vertices[slot]].co
            no = tri.split_normals[slot]

            vertices.extend(blender_to_unity_vector(co))
            normals.extend(blender_to_unity_vector(no))
            if uv_data is not None:
                uv = uv_data[loop_index].uv
                uvs.extend((uv[0], uv[1]))
            else:
                uvs.extend((0.0, 0.0))

            corners.append(corner)
            corner += 1

        # The Z-up → Y-up axis swap mirrors handedness, so reverse winding to
        # keep faces front-facing in Unity.
        faces.extend((corners[0], corners[2], corners[1]))

    return vertices, faces, uvs, normals


def _write_transform(obj, writer):
    """Emit the [TRANSFORM] block in Unity space.

    Position and scale convert cleanly via the (x, y, z) -> (x, z, y) axis
    swap. Rotation is exported as degrees with the same axis swap; full
    handedness parity is verified during the importer round-trip milestone.
    """
    position = blender_to_unity_vector(obj.location)

    sx, sy, sz = obj.scale
    scale = (sx, sz, sy)

    rx, ry, rz = (math.degrees(a) for a in obj.rotation_euler)
    rotation = (rx, rz, ry)

    writer.write_transform(position, rotation, scale)
