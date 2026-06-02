using UnityEditor;
using UnityEditor.AssetImporters;
using UnityEngine;

namespace UniForge
{
    /// <summary>
    /// ScriptedImporter for .unif files. Any .unif dropped into the Assets
    /// folder is parsed and turned into Mesh, Shader Graph, Material, and
    /// Prefab sub-assets (spec §5.2 / §5.3).
    /// </summary>
    [ScriptedImporter(version: 6, ext: "unif")]
    public class UnifImporter : ScriptedImporter
    {
        public const string SupportedFormatVersion = "1.0";

        public override void OnImportAsset(AssetImportContext ctx)
        {
            // 11. Parse .unif into the internal document model.
            UnifDocument doc = UnifParser.ParseFile(ctx.assetPath);

            if (!IsVersionSupported(doc.Version))
            {
                ctx.LogImportWarning(
                    $"UniForge: .unif version '{doc.Version}' may be incompatible " +
                    $"(importer supports {SupportedFormatVersion}).");
            }

            // Build a child GameObject per exported object under one root, so
            // multi-object .unif files import as a single prefab hierarchy.
            string rootName = string.IsNullOrEmpty(doc.SourceFile)
                ? "UnifAsset"
                : System.IO.Path.GetFileNameWithoutExtension(doc.SourceFile);
            var root = new GameObject(rootName);

            // Textures are shared across the whole file (one sub-asset each).
            var textureCache = new System.Collections.Generic.Dictionary<string, Texture2D>();

            for (int i = 0; i < doc.Objects.Count; i++)
            {
                UnifObject obj = doc.Objects[i];
                if (obj.Mesh == null)
                    continue;

                Mesh mesh = MeshBuilder.Build(obj.Mesh);
                ctx.AddObjectToAsset($"mesh_{i}", mesh);

                Material[] materials = ShaderGraphBuilder.BuildMaterials(
                    obj.Materials, doc, ctx, mesh.subMeshCount, textureCache, $"o{i}_");

                var child = new GameObject(obj.Mesh.Name ?? $"Object_{i}");
                child.transform.SetParent(root.transform, worldPositionStays: false);
                ApplyTransform(child.transform, obj.Transform);

                var filter = child.AddComponent<MeshFilter>();
                filter.sharedMesh = mesh;
                var renderer = child.AddComponent<MeshRenderer>();
                if (materials != null && materials.Length > 0)
                    renderer.sharedMaterials = materials;
            }

            ctx.AddObjectToAsset("prefab", root);
            ctx.SetMainObject(root);
        }

        private static void ApplyTransform(Transform transform, UnifTransform t)
        {
            if (t == null)
                return;
            transform.localPosition = ToVector3(t.Position, Vector3.zero);
            transform.localEulerAngles = ToVector3(t.Rotation, Vector3.zero);
            transform.localScale = ToVector3(t.Scale, Vector3.one);
        }

        private static Vector3 ToVector3(float[] v, Vector3 fallback)
        {
            if (v == null || v.Length < 3)
                return fallback;
            return new Vector3(v[0], v[1], v[2]);
        }

        private static bool IsVersionSupported(string version)
        {
            // v1.x is forward-tolerant; reject 2.x+.
            return !string.IsNullOrEmpty(version) && version.StartsWith("1.");
        }
    }
}
