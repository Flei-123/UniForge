using System.Collections.Generic;
using UnityEditor.AssetImporters;
using UnityEngine;

namespace UniForge
{
    /// <summary>
    /// Reconstructs a Unity Shader Graph from .unif material/node data and wraps
    /// it in a Material (spec §5.3 steps 13-15).
    /// </summary>
    public static class ShaderGraphBuilder
    {
        public static Material BuildMaterial(List<UnifMaterial> materials, AssetImportContext ctx)
        {
            // TODO(v1.0):
            //   13. Instantiate Shader Graph nodes via the ShaderGraph API,
            //       resolving .unif node types through NodeMap.
            //   14. Recreate connections from each material's Connections list.
            //   15. Generate a Material referencing the produced shader and
            //       register both with ctx.AddObjectToAsset.
            //   Emit warnings for NotSupported / BakeOnly nodes.

            // Placeholder so imports don't fail before the builder lands:
            // a default URP/Standard-lit material.
            Shader fallback = Shader.Find("Universal Render Pipeline/Lit")
                              ?? Shader.Find("Standard");
            var mat = new Material(fallback) { name = "UnifMaterial" };
            ctx.AddObjectToAsset("material", mat);
            return mat;
        }
    }
}
