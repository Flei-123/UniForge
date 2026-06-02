using System;
using UnityEngine;

namespace UniForge
{
    /// <summary>Builds a UnityEngine.Mesh from parsed geometry (spec §5.3 step 12).</summary>
    public static class MeshBuilder
    {
        public static Mesh Build(UnifMesh data)
        {
            if (data == null)
                throw new ArgumentNullException(nameof(data), "No [MESH] block in .unif file.");

            var mesh = new Mesh { name = data.Name ?? "UnifMesh" };
            if (data.Vertices != null && data.Vertices.Length / 3 > ushort.MaxValue)
                mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;

            mesh.SetVertices(ToVector3Array(data.Vertices));
            int[] faces = data.Faces ?? Array.Empty<int>();
            if (data.Uvs != null && data.Uvs.Length > 0)
                mesh.SetUVs(0, ToVector2Array(data.Uvs));
            if (data.Normals != null && data.Normals.Length > 0)
                mesh.SetNormals(ToVector3Array(data.Normals));

            AssignSubmeshes(mesh, faces, data.Submeshes);

            if (data.Normals == null || data.Normals.Length == 0)
                mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            return mesh;
        }

        /// <summary>
        /// Split the (slot-ordered) triangle list into one submesh per material
        /// slot. Faces are grouped by slot on export; ``submeshes`` holds the
        /// triangle count per slot. Falls back to a single submesh.
        /// </summary>
        private static void AssignSubmeshes(Mesh mesh, int[] faces, int[] submeshes)
        {
            if (submeshes == null || submeshes.Length <= 1)
            {
                mesh.subMeshCount = 1;
                mesh.SetTriangles(faces, 0);
                return;
            }

            mesh.subMeshCount = submeshes.Length;
            int start = 0; // index into the flat faces array
            for (int slot = 0; slot < submeshes.Length; slot++)
            {
                int indexCount = submeshes[slot] * 3;
                int end = Math.Min(start + indexCount, faces.Length);
                var slice = new int[Math.Max(0, end - start)];
                Array.Copy(faces, start, slice, 0, slice.Length);
                mesh.SetTriangles(slice, slot);
                start = end;
            }
        }

        private static Vector3[] ToVector3Array(float[] flat)
        {
            if (flat == null) return Array.Empty<Vector3>();
            var result = new Vector3[flat.Length / 3];
            for (int i = 0; i < result.Length; i++)
                result[i] = new Vector3(flat[i * 3], flat[i * 3 + 1], flat[i * 3 + 2]);
            return result;
        }

        private static Vector2[] ToVector2Array(float[] flat)
        {
            if (flat == null) return Array.Empty<Vector2>();
            var result = new Vector2[flat.Length / 2];
            for (int i = 0; i < result.Length; i++)
                result[i] = new Vector2(flat[i * 2], flat[i * 2 + 1]);
            return result;
        }
    }
}
