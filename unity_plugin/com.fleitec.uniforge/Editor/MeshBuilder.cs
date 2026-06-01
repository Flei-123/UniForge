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

            mesh.SetVertices(ToVector3Array(data.Vertices));
            mesh.SetTriangles(data.Faces ?? Array.Empty<int>(), 0);
            if (data.Uvs != null && data.Uvs.Length > 0)
                mesh.SetUVs(0, ToVector2Array(data.Uvs));
            if (data.Normals != null && data.Normals.Length > 0)
                mesh.SetNormals(ToVector3Array(data.Normals));
            else
                mesh.RecalculateNormals();

            mesh.RecalculateBounds();
            return mesh;
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
