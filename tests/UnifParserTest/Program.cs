using System;
using System.IO;
using UniForge;

// Standalone parser harness. Run from the repo root:
//   dotnet run --project tests/UnifParserTest -- samples/FloorTile.unif
// With no argument it runs the built-in assertion suite only.

internal static class Program
{
    private static int _failures;

    private static int Main(string[] args)
    {
        RunAssertions();

        if (args.Length > 0 && File.Exists(args[0]))
        {
            Console.WriteLine($"\n=== Dump of {args[0]} ===");
            Dump(UnifParser.ParseFile(args[0]));
        }

        Console.WriteLine(_failures == 0
            ? "\nALL ASSERTIONS PASSED"
            : $"\n{_failures} ASSERTION(S) FAILED");
        return _failures == 0 ? 0 : 1;
    }

    private static void RunAssertions()
    {
        // Mirrors the exporter's real output: curated params, a quoted path
        // with spaces, and a TexCoord -> Mapping -> Texture connection chain.
        const string sample = @"
[UNIF]
  version: 1.0
  generator: UniForge Blender Addon 1.0
  source_file: test.blend

[MESH]
  name: TestCube
  vertices: [-1,-1,-1, -1,1,-1, -1,1,1]
  faces: [0,2,1]
  uvs: [0.375,0, 0.625,0, 0.625,0.25]
  normals: [-1,0,0, -1,0,0, -1,0,0]

[TRANSFORM]
  position: 1, 3, 2
  rotation: 0, 0, 0
  scale: 1, 1, 1

[MATERIAL]
  name: WetTile_Mat
  slot: 0
  [NODE PrincipledBSDF id=0]
    metallic: 0
    roughness: 0.35
    emission_color: 1,1,1,1
  [NODE ImageTexture id=2 path=""wet tiles/diffuse 01.png""]
  [NODE Mapping id=3]
    scale: 2,2,1
  [NODE TextureCoordinate id=4]
  [CONNECTION]
    2.Color -> 0.Base_Color
    4.UV -> 3.Vector
    3.Vector -> 2.Vector
";

        UnifDocument doc = UnifParser.Parse(sample);

        Check("version", doc.Version == "1.0");
        Check("generator", doc.Generator == "UniForge Blender Addon 1.0");
        Check("mesh name", doc.Mesh != null && doc.Mesh.Name == "TestCube");
        Check("vertex floats", doc.Mesh.Vertices.Length == 9);
        Check("face indices", doc.Mesh.Faces.Length == 3 && doc.Mesh.Faces[1] == 2);
        Check("uv floats", doc.Mesh.Uvs.Length == 6);
        Check("normal floats", doc.Mesh.Normals.Length == 9);

        Check("transform position", doc.Transform != null
            && doc.Transform.Position[0] == 1f
            && doc.Transform.Position[1] == 3f
            && doc.Transform.Position[2] == 2f);

        Check("material count", doc.Materials.Count == 1);
        UnifMaterial mat = doc.Materials[0];
        Check("material name", mat.Name == "WetTile_Mat");
        Check("material slot", mat.Slot == 0);
        Check("node count", mat.Nodes.Count == 4);

        UnifNode bsdf = mat.Nodes[0];
        Check("bsdf type", bsdf.Type == "PrincipledBSDF");
        Check("bsdf id", bsdf.Id == 0);
        Check("bsdf roughness param", bsdf.Parameters.TryGetValue("roughness", out string r) && r == "0.35");
        Check("bsdf emission param", bsdf.Parameters.TryGetValue("emission_color", out string e) && e == "1,1,1,1");

        UnifNode tex = mat.Nodes[1];
        Check("tex type", tex.Type == "ImageTexture");
        Check("tex id", tex.Id == 2);
        Check("quoted path with spaces",
            tex.Attributes.TryGetValue("path", out string p) && p == "wet tiles/diffuse 01.png");

        Check("connection count", mat.Connections.Count == 3);
        UnifConnection c0 = mat.Connections[0];
        Check("connection src id", c0.SourceId == 2);
        Check("connection src socket", c0.SourceSocket == "Color");
        Check("connection dst id", c0.TargetId == 0);
        Check("connection dst socket (underscore preserved)", c0.TargetSocket == "Base_Color");

        RunClassifierAssertions();
        RunEmbeddedTextureAssertions();
    }

    private static void RunEmbeddedTextureAssertions()
    {
        // "hello" -> base64; name carries a space to exercise quoted attrs.
        const string unif = @"
[MATERIAL]
  name: M
  [NODE ImageTexture id=0 path=""wet tile.png""]
[TEXTURE_EMBEDDED name=""wet tile.png"" format=png]
  data: aGVsbG8=
";
        UnifDocument doc = UnifParser.Parse(unif);
        Check("embedded: one texture parsed", doc.EmbeddedTextures.Count == 1);
        bool found = doc.EmbeddedTextures.TryGetValue("wet tile.png", out byte[] bytes);
        Check("embedded: keyed by quoted name", found);
        Check("embedded: base64 decoded", found && System.Text.Encoding.ASCII.GetString(bytes) == "hello");
    }

    private static void RunClassifierAssertions()
    {
        // Lit-sufficient: Principled + textures + mapping/coord only.
        var lit = new UnifMaterial { Name = "Lit" };
        lit.Nodes.Add(new UnifNode { Type = "PrincipledBSDF", Id = 0 });
        lit.Nodes.Add(new UnifNode { Type = "MaterialOutput", Id = 1 });
        lit.Nodes.Add(new UnifNode { Type = "ImageTexture", Id = 2 });
        lit.Nodes.Add(new UnifNode { Type = "Mapping", Id = 3 });
        lit.Nodes.Add(new UnifNode { Type = "TextureCoordinate", Id = 4 });
        Check("classifier: lit-sufficient -> no graph",
            !MaterialClassifier.RequiresShaderGraph(lit, out _));

        // Procedural node forces a graph.
        var proc = new UnifMaterial { Name = "Proc" };
        proc.Nodes.Add(new UnifNode { Type = "PrincipledBSDF", Id = 0 });
        proc.Nodes.Add(new UnifNode { Type = "NoiseTexture", Id = 1 });
        bool needsGraph = MaterialClassifier.RequiresShaderGraph(proc, out string reason);
        Check("classifier: procedural -> needs graph", needsGraph);
        Check("classifier: reason names the node", reason != null && reason.Contains("NoiseTexture"));

        // Empty material is trivially lit-sufficient.
        Check("classifier: empty -> no graph",
            !MaterialClassifier.RequiresShaderGraph(new UnifMaterial(), out _));
    }

    private static void Check(string label, bool condition)
    {
        Console.WriteLine($"  [{(condition ? "PASS" : "FAIL")}] {label}");
        if (!condition) _failures++;
    }

    private static void Dump(UnifDocument doc)
    {
        Console.WriteLine($"version={doc.Version} generator={doc.Generator} source={doc.SourceFile}");
        if (doc.Mesh != null)
            Console.WriteLine($"mesh '{doc.Mesh.Name}': {doc.Mesh.Vertices.Length / 3} verts, "
                + $"{doc.Mesh.Faces.Length / 3} tris");
        if (doc.Transform != null)
            Console.WriteLine($"transform pos=({string.Join(',', doc.Transform.Position)})");
        foreach (UnifMaterial m in doc.Materials)
        {
            Console.WriteLine($"material '{m.Name}' slot {m.Slot}: {m.Nodes.Count} nodes, "
                + $"{m.Connections.Count} connections");
            foreach (UnifNode n in m.Nodes)
            {
                string attrs = n.Attributes.Count > 0 ? " {" + string.Join(", ", FormatPairs(n.Attributes)) + "}" : "";
                Console.WriteLine($"  - {n.Type} id={n.Id}{attrs} params={n.Parameters.Count}");
            }
            foreach (UnifConnection c in m.Connections)
                Console.WriteLine($"  ~ {c.SourceId}.{c.SourceSocket} -> {c.TargetId}.{c.TargetSocket}");
        }
    }

    private static System.Collections.Generic.IEnumerable<string> FormatPairs(
        System.Collections.Generic.Dictionary<string, string> dict)
    {
        foreach (var kv in dict)
            yield return $"{kv.Key}={kv.Value}";
    }
}
