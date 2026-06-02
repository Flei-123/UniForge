using System.Collections.Generic;

namespace UniForge
{
    /// <summary>In-memory model of a parsed .unif file.</summary>
    public class UnifDocument
    {
        public string Version;
        public string Generator;
        public string SourceFile;

        public UnifMesh Mesh;
        public UnifTransform Transform;
        public readonly List<UnifMaterial> Materials = new List<UnifMaterial>();

        // Base64-decoded textures embedded in the file, keyed by their name
        // (which matches an Image Texture node's "path" attribute).
        public readonly Dictionary<string, byte[]> EmbeddedTextures =
            new Dictionary<string, byte[]>();
    }

    public class UnifMesh
    {
        public string Name;
        public float[] Vertices; // flat xyz triples (Unity Y-up space)
        public int[] Faces;      // flat triangle index triples
        public float[] Uvs;      // flat uv pairs
        public float[] Normals;  // flat xyz triples
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
