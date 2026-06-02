using System.Collections.Generic;

namespace UniForge
{
    /// <summary>In-memory model of a parsed .unif file.</summary>
    public class UnifDocument
    {
        public string Version;
        public string Generator;
        public string SourceFile;

        // One entry per exported object (an [OBJECT] block, or a single implicit
        // object for legacy single-object files).
        public readonly List<UnifObject> Objects = new List<UnifObject>();

        // Base64-decoded textures embedded in the file, keyed by their name
        // (which matches an Image Texture node's "path" attribute). Shared
        // across all objects.
        public readonly Dictionary<string, byte[]> EmbeddedTextures =
            new Dictionary<string, byte[]>();

        // Convenience accessors for the first object (back-compat / single-object).
        public UnifMesh Mesh => Objects.Count > 0 ? Objects[0].Mesh : null;
        public UnifTransform Transform => Objects.Count > 0 ? Objects[0].Transform : null;
        public List<UnifMaterial> Materials =>
            Objects.Count > 0 ? Objects[0].Materials : _noMaterials;

        private static readonly List<UnifMaterial> _noMaterials = new List<UnifMaterial>();
    }

    /// <summary>A single exported object: geometry + transform + materials.</summary>
    public class UnifObject
    {
        public string Name;
        public string Parent; // name of the parent object, or null for top-level
        public UnifMesh Mesh;
        public UnifTransform Transform;
        public readonly List<UnifMaterial> Materials = new List<UnifMaterial>();
    }

    public class UnifMesh
    {
        public string Name;
        public float[] Vertices; // flat xyz triples (Unity Y-up space)
        public int[] Faces;      // flat triangle index triples, ordered by submesh
        public float[] Uvs;      // flat uv pairs
        public float[] Normals;  // flat xyz triples
        public float[] Colors;   // flat rgba per vertex (null = none)
        public int[] Submeshes;  // triangle count per material slot (null = single submesh)
    }

    public class UnifTransform
    {
        public float[] Position = { 0f, 0f, 0f };
        public float[] Rotation = { 0f, 0f, 0f };
        public float[] Scale = { 1f, 1f, 1f };
    }

    public class UnifMaterial
    {
        public string Name;
        public int Slot;
        public readonly List<UnifNode> Nodes = new List<UnifNode>();
        public readonly List<UnifConnection> Connections = new List<UnifConnection>();
    }

    public class UnifNode
    {
        public string Type;                 // .unif node type, e.g. "PrincipledBSDF"
        public int Id;
        public readonly Dictionary<string, string> Attributes = new Dictionary<string, string>();
        public readonly Dictionary<string, string> Parameters = new Dictionary<string, string>();
    }

    public class UnifConnection
    {
        public int SourceId;
        public string SourceSocket;
        public int TargetId;
        public string TargetSocket;
    }
}
