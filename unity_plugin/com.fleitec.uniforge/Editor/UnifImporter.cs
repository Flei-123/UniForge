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
    [ScriptedImporter(version: 2, ext: "unif")]
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

            // 12. Build mesh.
            Mesh mesh = MeshBuilder.Build(doc.Mesh);
            ctx.AddObjectToAsset("mesh", mesh);

            // 13-15. Reconstruct one material per slot (ordered by slot index).
            Material[] materials = ShaderGraphBuilder.BuildMaterials(doc, ctx);

            // 16. Build prefab (MeshFilter + MeshRenderer).
            GameObject prefab = BuildPrefab(doc, mesh, materials);
            ctx.AddObjectToAsset("prefab", prefab);
            ctx.SetMainObject(prefab);

            // 17. Per-node warnings are emitted by ShaderGraphBuilder during the build.
        }

        private static bool IsVersionSupported(string version)
        {
            // v1.x is forward-tolerant; reject 2.x+.
            return !string.IsNullOrEmpty(version) && version.StartsWith("1.");
        }

        private static GameObject BuildPrefab(UnifDocument doc, Mesh mesh, Material[] materials)
        {
            var go = new GameObject(doc.Mesh != null ? doc.Mesh.Name : "UnifAsset");
            var filter = go.AddComponent<MeshFilter>();
            filter.sharedMesh = mesh;
            var renderer = go.AddComponent<MeshRenderer>();
            if (materials != null && materials.Length > 0)
                renderer.sharedMaterials = materials;
            return go;
        }
    }
}
