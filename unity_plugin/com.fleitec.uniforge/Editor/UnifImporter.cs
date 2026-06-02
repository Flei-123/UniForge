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
    [ScriptedImporter(version: 8, ext: "unif")]
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

            // Textures are shared across the whole file (one sub-asset each).
            var textureCache = new System.Collections.Generic.Dictionary<string, Texture2D>();
            var built = new System.Collections.Generic.List<GameObject>();
            var byName = new System.Collections.Generic.Dictionary<string, GameObject>();

            // Pass 1: build a GameObject (mesh + materials) per object.
            for (int i = 0; i < doc.Objects.Count; i++)
            {
                UnifObject obj = doc.Objects[i];
                var go = new GameObject(obj.Name ?? obj.Mesh?.Name ?? $"Object_{i}");

                if (obj.Mesh != null)
                {
                    Mesh mesh = MeshBuilder.Build(obj.Mesh);
                    ctx.AddObjectToAsset($"mesh_{i}", mesh);
                    Material[] materials = ShaderGraphBuilder.BuildMaterials(
                        obj.Materials, doc, ctx, mesh.subMeshCount, textureCache, $"o{i}_");
                    go.AddComponent<MeshFilter>().sharedMesh = mesh;
                    var renderer = go.AddComponent<MeshRenderer>();
                    if (materials != null && materials.Length > 0)
                        renderer.sharedMaterials = materials;
                }

                built.Add(go);
                if (!string.IsNullOrEmpty(obj.Name))
                    byName[obj.Name] = go;
            }

            // Pass 2: rebuild Blender's parent hierarchy and apply transforms.
            var roots = new System.Collections.Generic.List<GameObject>();
            for (int i = 0; i < doc.Objects.Count; i++)
            {
                UnifObject obj = doc.Objects[i];
                GameObject go = built[i];
                if (!string.IsNullOrEmpty(obj.Parent) && byName.TryGetValue(obj.Parent, out GameObject parentGo))
                    go.transform.SetParent(parentGo.transform, worldPositionStays: false);
                else
                    roots.Add(go);
                ApplyTransform(go.transform, obj.Transform); // local for children, world for roots
            }

            // A single top-level object is the prefab root (its pivot matches the
            // Blender origin); multiple roots are wrapped in a container.
            GameObject prefab;
            if (roots.Count == 1)
            {
                prefab = roots[0];
            }
            else
            {
                string rootName = string.IsNullOrEmpty(doc.SourceFile)
                    ? "UnifAsset"
                    : System.IO.Path.GetFileNameWithoutExtension(doc.SourceFile);
                prefab = new GameObject(rootName);
                foreach (GameObject r in roots)
                    r.transform.SetParent(prefab.transform, worldPositionStays: true);
            }

            ctx.AddObjectToAsset("prefab", prefab);
            ctx.SetMainObject(prefab);
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
