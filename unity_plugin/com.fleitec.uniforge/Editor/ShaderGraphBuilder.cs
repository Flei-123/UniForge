using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEditor;
using UnityEditor.AssetImporters;
using UnityEngine;

namespace UniForge
{
    /// <summary>
    /// Reconstructs Unity materials from .unif material/node data (spec §5.3
    /// steps 13-15).
    ///
    /// v1.0 scope — PBR material reconstruction: the Principled BSDF and its
    /// connected Image / Normal-Map textures are mapped onto a URP Lit (or
    /// Built-in Standard) material. Full arbitrary node-graph → Shader Graph
    /// *asset* generation via the Shader Graph API is a dedicated later
    /// milestone (see docs/ROADMAP.md). Nodes that fall outside the mapping
    /// emit import warnings rather than failing the import.
    /// </summary>
    public static class ShaderGraphBuilder
    {
        /// <summary>Build one material per slot, ordered by slot index.</summary>
        public static Material[] BuildMaterials(UnifDocument doc, AssetImportContext ctx)
        {
            var ordered = new List<UnifMaterial>(doc.Materials);
            ordered.Sort((a, b) => a.Slot.CompareTo(b.Slot));

            var materials = new Material[ordered.Count];
            for (int i = 0; i < ordered.Count; i++)
            {
                materials[i] = BuildOne(ordered[i], ctx, doc);
                ctx.AddObjectToAsset($"material_{ordered[i].Slot}", materials[i]);
            }
            return materials;
        }

        private static Material BuildOne(UnifMaterial unifMat, AssetImportContext ctx, UnifDocument doc)
        {
            // Only reconstruct a custom shader when the node network actually
            // needs one; otherwise a plain Lit material is sufficient.
            if (MaterialClassifier.RequiresShaderGraph(unifMat, out string reason))
            {
                ctx.LogImportWarning(
                    $"UniForge: material '{unifMat.Name}' uses {reason} which needs full " +
                    "Shader Graph reconstruction (not yet generated). A base Lit material " +
                    "was created as a placeholder.");
            }

            Shader shader = Shader.Find("Universal Render Pipeline/Lit")
                            ?? Shader.Find("Standard");
            var mat = new Material(shader) { name = unifMat.Name ?? "UnifMaterial" };

            UnifNode bsdf = FindNodeByType(unifMat, "PrincipledBSDF");
            if (bsdf == null)
            {
                ctx.LogImportWarning(
                    $"UniForge: material '{unifMat.Name}' has no Principled BSDF; " +
                    "left at shader defaults.");
                WarnUnmappedNodes(unifMat, ctx, mappedIds: new HashSet<int>());
                return mat;
            }

            var mapped = new HashSet<int> { bsdf.Id };

            ApplyScalarParams(mat, bsdf);
            ApplyTransparency(mat, bsdf);
            ApplyEmission(mat, bsdf);
            ApplyBaseColorTexture(mat, unifMat, bsdf, ctx, doc, mapped);
            ApplyNormalTexture(mat, unifMat, bsdf, ctx, doc, mapped);

            WarnUnmappedNodes(unifMat, ctx, mapped);
            return mat;
        }

        // --- parameter mapping ------------------------------------------------
        private static void ApplyScalarParams(Material mat, UnifNode bsdf)
        {
            TryColor(bsdf, "base_color", out Color baseColor);
            // Blender transparency comes from the Principled 'Alpha' input, not
            // the base-color alpha channel — fold it into the material color.
            if (TryFloat(bsdf, "alpha", out float alpha))
                baseColor.a = alpha;
            SetColor(mat, "_BaseColor", baseColor);
            SetColor(mat, "_Color", baseColor); // Built-in Standard

            if (TryFloat(bsdf, "metallic", out float metallic))
                SetFloat(mat, "_Metallic", metallic);
            if (TryFloat(bsdf, "roughness", out float roughness))
            {
                // Blender roughness is the inverse of Unity smoothness.
                float smoothness = Mathf.Clamp01(1f - roughness);
                SetFloat(mat, "_Smoothness", smoothness);
                SetFloat(mat, "_Glossiness", smoothness); // Built-in Standard
            }
        }

        private static void ApplyTransparency(Material mat, UnifNode bsdf)
        {
            // Alpha defaults to 1 (fully opaque); only switch surface mode when
            // the material is actually see-through.
            if (!TryFloat(bsdf, "alpha", out float alpha) || alpha >= 1f)
                return;

            float srcAlpha = (float)UnityEngine.Rendering.BlendMode.SrcAlpha;
            float oneMinusSrcAlpha = (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha;
            int transparentQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;

            if (mat.HasProperty("_Surface"))
            {
                // URP Lit transparent setup (mirrors URP's own ShaderGUI).
                mat.SetFloat("_Surface", 1f); // 0 = Opaque, 1 = Transparent
                mat.SetFloat("_Blend", 0f);   // Alpha blend
                mat.SetFloat("_SrcBlend", srcAlpha);
                mat.SetFloat("_DstBlend", oneMinusSrcAlpha);
                mat.SetFloat("_ZWrite", 0f);
                mat.SetFloat("_AlphaClip", 0f);
                mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                mat.DisableKeyword("_ALPHATEST_ON");
                mat.DisableKeyword("_ALPHAPREMULTIPLY_ON");
            }
            else
            {
                // Built-in Standard transparent (_Mode = 3 = Transparent).
                if (mat.HasProperty("_Mode"))
                    mat.SetFloat("_Mode", 3f);
                mat.SetFloat("_SrcBlend", srcAlpha);
                mat.SetFloat("_DstBlend", oneMinusSrcAlpha);
                mat.SetFloat("_ZWrite", 0f);
                mat.DisableKeyword("_ALPHATEST_ON");
                mat.EnableKeyword("_ALPHABLEND_ON");
                mat.DisableKeyword("_ALPHAPREMULTIPLY_ON");
            }
            mat.renderQueue = transparentQueue;
        }

        private static void ApplyEmission(Material mat, UnifNode bsdf)
        {
            if (!TryColor(bsdf, "emission_color", out Color emission))
                return;
            float strength = TryFloat(bsdf, "emission_strength", out float s) ? s : 1f;
            Color final = emission * strength;
            if (final.maxColorComponent <= 0f)
                return;

            if (mat.HasProperty("_EmissionColor"))
                mat.SetColor("_EmissionColor", final);
            mat.EnableKeyword("_EMISSION");
            mat.globalIlluminationFlags &= ~MaterialGlobalIlluminationFlags.EmissiveIsBlack;
        }

        // --- texture mapping --------------------------------------------------
        private static void ApplyBaseColorTexture(
            Material mat, UnifMaterial unifMat, UnifNode bsdf,
            AssetImportContext ctx, UnifDocument doc, HashSet<int> mapped)
        {
            UnifNode src = FindSource(unifMat, bsdf.Id, "Base_Color");
            if (src == null || src.Type != "ImageTexture")
                return;

            Texture2D tex = LoadTexture(src, ctx, doc);
            mapped.Add(src.Id);
            if (tex == null)
                return;

            SetTexture(mat, "_BaseMap", tex);
            SetTexture(mat, "_MainTex", tex); // Built-in Standard
        }

        private static void ApplyNormalTexture(
            Material mat, UnifMaterial unifMat, UnifNode bsdf,
            AssetImportContext ctx, UnifDocument doc, HashSet<int> mapped)
        {
            UnifNode src = FindSource(unifMat, bsdf.Id, "Normal");
            if (src == null)
                return;

            // Normal usually arrives via a Normal Map node fed by an Image Texture.
            UnifNode imageNode = src;
            if (src.Type == "NormalMap")
            {
                mapped.Add(src.Id);
                imageNode = FindSource(unifMat, src.Id, "Color");
            }
            if (imageNode == null || imageNode.Type != "ImageTexture")
                return;

            Texture2D tex = LoadTexture(imageNode, ctx, doc);
            mapped.Add(imageNode.Id);
            if (tex == null)
                return;

            SetTexture(mat, "_BumpMap", tex);
            if (mat.HasProperty("_BumpMap"))
                mat.EnableKeyword("_NORMALMAP");
        }

        private static Texture2D LoadTexture(UnifNode imageNode, AssetImportContext ctx, UnifDocument doc)
        {
            if (!imageNode.Attributes.TryGetValue("path", out string path) || string.IsNullOrEmpty(path))
                return null;

            // Prefer an embedded texture (self-contained .unif) over a disk file.
            if (doc != null && doc.EmbeddedTextures.TryGetValue(path, out byte[] data))
            {
                var embedded = new Texture2D(2, 2);
                if (ImageConversion.LoadImage(embedded, data))
                {
                    embedded.name = Path.GetFileNameWithoutExtension(path);
                    ctx.AddObjectToAsset("tex_" + path, embedded);
                    return embedded;
                }
                ctx.LogImportWarning($"UniForge: failed to decode embedded texture '{path}'.");
            }

            // Textures are referenced relative to the .unif file's folder.
            string dir = Path.GetDirectoryName(ctx.assetPath);
            string texPath = string.IsNullOrEmpty(dir) ? path : $"{dir}/{path}";
            texPath = texPath.Replace('\\', '/');

            // Re-import this asset when the texture changes.
            ctx.DependsOnSourceAsset(texPath);

            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(texPath);
            if (tex == null)
                ctx.LogImportWarning($"UniForge: texture not found at '{texPath}'.");
            return tex;
        }

        private static void WarnUnmappedNodes(
            UnifMaterial unifMat, AssetImportContext ctx, HashSet<int> mappedIds)
        {
            foreach (UnifNode node in unifMat.Nodes)
            {
                if (mappedIds.Contains(node.Id))
                    continue;
                // Material Output and coordinate/utility nodes are expected to be
                // unmapped in the PBR material path; only flag shading nodes.
                if (node.Type == "MaterialOutput" || node.Type == "Mapping"
                    || node.Type == "TextureCoordinate" || node.Type == "UVMap")
                    continue;

                string note = NodeMap.TryGet(node.Type, out NodeMap.Mapping m)
                    ? $"status {m.Status}"
                    : "unknown type";
                ctx.LogImportWarning(
                    $"UniForge: node '{node.Type}' (id {node.Id}) not represented in " +
                    $"the v1.0 material mapping ({note}).");
            }
        }

        // --- graph helpers ----------------------------------------------------
        private static UnifNode FindNodeByType(UnifMaterial mat, string type)
        {
            foreach (UnifNode n in mat.Nodes)
                if (n.Type == type)
                    return n;
            return null;
        }

        private static UnifNode FindNodeById(UnifMaterial mat, int id)
        {
            foreach (UnifNode n in mat.Nodes)
                if (n.Id == id)
                    return n;
            return null;
        }

        /// <summary>Node feeding <paramref name="targetSocket"/> of node <paramref name="targetId"/>.</summary>
        private static UnifNode FindSource(UnifMaterial mat, int targetId, string targetSocket)
        {
            foreach (UnifConnection c in mat.Connections)
                if (c.TargetId == targetId && c.TargetSocket == targetSocket)
                    return FindNodeById(mat, c.SourceId);
            return null;
        }

        // --- value parsing / property setters ---------------------------------
        private static bool TryFloat(UnifNode node, string key, out float value)
        {
            value = 0f;
            return node.Parameters.TryGetValue(key, out string raw)
                && float.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out value);
        }

        private static bool TryColor(UnifNode node, string key, out Color color)
        {
            color = Color.white;
            if (!node.Parameters.TryGetValue(key, out string raw))
                return false;

            string[] parts = raw.Split(',');
            float[] c = { 1f, 1f, 1f, 1f };
            for (int i = 0; i < parts.Length && i < 4; i++)
                float.TryParse(parts[i].Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out c[i]);
            color = new Color(c[0], c[1], c[2], c[3]);
            return true;
        }

        private static void SetColor(Material mat, string prop, Color value)
        {
            if (mat.HasProperty(prop)) mat.SetColor(prop, value);
        }

        private static void SetFloat(Material mat, string prop, float value)
        {
            if (mat.HasProperty(prop)) mat.SetFloat(prop, value);
        }

        private static void SetTexture(Material mat, string prop, Texture tex)
        {
            if (mat.HasProperty(prop)) mat.SetTexture(prop, tex);
        }
    }
}
