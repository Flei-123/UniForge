using System.Collections.Generic;

namespace UniForge
{
    /// <summary>
    /// Decides whether a .unif material maps cleanly onto a built-in Lit
    /// material or needs a full Shader Graph asset.
    ///
    /// Design goal (per product direction): do NOT spin up a custom shader when
    /// the standard Lit material is enough. Only materials whose shading network
    /// uses procedural / compositing nodes (Noise, Voronoi, Mix, Math, Color
    /// Ramp, …) require Shader Graph reconstruction.
    ///
    /// Pure C# (no Unity dependencies) so the rule is unit-testable.
    /// </summary>
    public static class MaterialClassifier
    {
        /// <summary>
        /// Node types the Lit material mapping (ShaderGraphBuilder) fully
        /// consumes. Anything outside this set implies a real graph is needed.
        /// </summary>
        private static readonly HashSet<string> LitSupported = new HashSet<string>
        {
            "PrincipledBSDF",
            "MaterialOutput",
            "ImageTexture",
            "NormalMap",
            "Mapping",
            "TextureCoordinate",
            "UVMap",
        };

        /// <summary>
        /// True if <paramref name="material"/> needs a Shader Graph asset rather
        /// than a plain Lit material. <paramref name="reason"/> names the first
        /// node that forced the decision.
        /// </summary>
        public static bool RequiresShaderGraph(UnifMaterial material, out string reason)
        {
            reason = null;
            if (material == null || material.Nodes == null)
                return false;

            foreach (UnifNode node in material.Nodes)
            {
                if (!LitSupported.Contains(node.Type))
                {
                    reason = $"node '{node.Type}' (id {node.Id})";
                    return true;
                }
            }
            return false;
        }
    }
}
