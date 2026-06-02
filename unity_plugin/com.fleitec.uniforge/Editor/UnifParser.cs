using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace UniForge
{
    /// <summary>
    /// Parses .unif text into a <see cref="UnifDocument"/> (spec §5.3 step 11).
    ///
    /// The format is block-based (see docs/FORMAT.md): lines like "[BLOCK ...]"
    /// open blocks, "key: value" lines are entries, and connection lines look
    /// like "1.Color -&gt; 0.Base_Color". Indentation is cosmetic — structure is
    /// driven by block kind, not whitespace. Inline attribute values may be
    /// double-quoted (with \\-escapes) when they contain spaces, '=' or ']'.
    /// </summary>
    public static class UnifParser
    {
        private const string ConnectionArrow = "->";

        private enum Section { None, Unif, Mesh, Transform, Material }

        public static UnifDocument ParseFile(string path)
        {
            return Parse(System.IO.File.ReadAllText(path));
        }

        public static UnifDocument Parse(string text)
        {
            var doc = new UnifDocument();
            var section = Section.None;
            UnifObject currentObject = null;
            UnifMaterial currentMaterial = null;
            UnifNode currentNode = null;
            bool inConnections = false;
            string pendingEmbeddedName = null; // set by [TEXTURE_EMBEDDED], consumed by its data: line

            // Geometry blocks before any [OBJECT] (legacy single-object files)
            // attach to one implicit object.
            UnifObject EnsureObject()
            {
                if (currentObject == null)
                {
                    currentObject = new UnifObject();
                    doc.Objects.Add(currentObject);
                }
                return currentObject;
            }

            foreach (string rawLine in text.Split('\n'))
            {
                string line = rawLine.Trim();
                if (line.Length == 0)
                    continue;

                if (line[0] == '[' && line.EndsWith("]", StringComparison.Ordinal))
                {
                    string header = line.Substring(1, line.Length - 2).Trim();
                    List<string> tokens = TokenizeHeader(header);
                    if (tokens.Count == 0)
                        continue;

                    string kind = tokens[0];
                    pendingEmbeddedName = null; // any new block ends a pending embed
                    switch (kind)
                    {
                        case "UNIF":
                            section = Section.Unif;
                            currentMaterial = null; currentNode = null; inConnections = false;
                            break;
                        case "OBJECT":
                            currentObject = new UnifObject
                            {
                                Name = HeaderAttr(tokens, "name"),
                                Parent = HeaderAttr(tokens, "parent"),
                            };
                            doc.Objects.Add(currentObject);
                            section = Section.None;
                            currentMaterial = null; currentNode = null; inConnections = false;
                            break;
                        case "MESH":
                            section = Section.Mesh;
                            EnsureObject().Mesh = new UnifMesh();
                            currentMaterial = null; currentNode = null; inConnections = false;
                            break;
                        case "TRANSFORM":
                            section = Section.Transform;
                            EnsureObject().Transform = new UnifTransform();
                            currentMaterial = null; currentNode = null; inConnections = false;
                            break;
                        case "MATERIAL":
                            section = Section.Material;
                            currentMaterial = new UnifMaterial();
                            EnsureObject().Materials.Add(currentMaterial);
                            currentNode = null; inConnections = false;
                            break;
                        case "NODE":
                            currentNode = ParseNodeHeader(tokens);
                            currentMaterial?.Nodes.Add(currentNode);
                            inConnections = false;
                            break;
                        case "CONNECTION":
                            inConnections = true; currentNode = null;
                            break;
                        case "TEXTURE_EMBEDDED":
                            pendingEmbeddedName = HeaderAttr(tokens, "name");
                            currentNode = null; inConnections = false;
                            break;
                        default:
                            currentNode = null; inConnections = false;
                            break;
                    }
                    continue;
                }

                if (inConnections && line.Contains(ConnectionArrow))
                {
                    UnifConnection conn = ParseConnection(line);
                    if (conn != null)
                        currentMaterial?.Connections.Add(conn);
                    continue;
                }

                int colon = line.IndexOf(':');
                if (colon < 0)
                    continue;

                string key = line.Substring(0, colon).Trim();
                string value = line.Substring(colon + 1).Trim();

                if (pendingEmbeddedName != null && key == "data")
                {
                    try
                    {
                        doc.EmbeddedTextures[pendingEmbeddedName] = Convert.FromBase64String(value);
                    }
                    catch (FormatException) { /* skip malformed base64 */ }
                    pendingEmbeddedName = null;
                    continue;
                }

                if (currentNode != null)
                {
                    currentNode.Parameters[key] = value;
                }
                else if (section == Section.Material && currentMaterial != null)
                {
                    AssignMaterialField(currentMaterial, key, value);
                }
                else if (section == Section.Unif)
                {
                    AssignUnifField(doc, key, value);
                }
                else if (section == Section.Mesh && currentObject?.Mesh != null)
                {
                    AssignMeshField(currentObject.Mesh, key, value);
                }
                else if (section == Section.Transform && currentObject?.Transform != null)
                {
                    AssignTransformField(currentObject.Transform, key, value);
                }
            }

            return doc;
        }

        // --- field assignment -------------------------------------------------
        private static void AssignUnifField(UnifDocument doc, string key, string value)
        {
            switch (key)
            {
                case "version": doc.Version = value; break;
                case "generator": doc.Generator = value; break;
                case "source_file": doc.SourceFile = value; break;
            }
        }

        private static void AssignMeshField(UnifMesh mesh, string key, string value)
        {
            switch (key)
            {
                case "name": mesh.Name = value; break;
                case "vertices": mesh.Vertices = ParseFloatArray(value); break;
                case "faces": mesh.Faces = ParseIntArray(value); break;
                case "uvs": mesh.Uvs = ParseFloatArray(value); break;
                case "normals": mesh.Normals = ParseFloatArray(value); break;
                case "colors": mesh.Colors = ParseFloatArray(value); break;
                case "submeshes": mesh.Submeshes = ParseIntArray(value); break;
            }
        }

        private static void AssignTransformField(UnifTransform t, string key, string value)
        {
            switch (key)
            {
                case "position": t.Position = ParseFloatArray(value); break;
                case "rotation": t.Rotation = ParseFloatArray(value); break;
                case "scale": t.Scale = ParseFloatArray(value); break;
            }
        }

        private static void AssignMaterialField(UnifMaterial mat, string key, string value)
        {
            switch (key)
            {
                case "name": mat.Name = value; break;
                case "slot":
                    if (int.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out int slot))
                        mat.Slot = slot;
                    break;
            }
        }

        // --- header / node parsing -------------------------------------------
        private static UnifNode ParseNodeHeader(List<string> tokens)
        {
            // tokens: "NODE" <Type> [key=value ...]
            var node = new UnifNode();
            if (tokens.Count >= 2)
                node.Type = tokens[1];

            for (int i = 2; i < tokens.Count; i++)
            {
                string tok = tokens[i];
                int eq = tok.IndexOf('=');
                if (eq < 0)
                    continue;
                string k = tok.Substring(0, eq);
                string v = tok.Substring(eq + 1);

                if (k == "id" && int.TryParse(v, NumberStyles.Integer, CultureInfo.InvariantCulture, out int id))
                    node.Id = id;
                else
                    node.Attributes[k] = v;
            }
            return node;
        }

        /// <summary>Find a ``key=value`` attribute among header tokens (skips the kind token).</summary>
        private static string HeaderAttr(List<string> tokens, string key)
        {
            for (int i = 1; i < tokens.Count; i++)
            {
                int eq = tokens[i].IndexOf('=');
                if (eq > 0 && tokens[i].Substring(0, eq) == key)
                    return tokens[i].Substring(eq + 1);
            }
            return null;
        }

        private static UnifConnection ParseConnection(string line)
        {
            int arrow = line.IndexOf(ConnectionArrow, StringComparison.Ordinal);
            string left = line.Substring(0, arrow).Trim();
            string right = line.Substring(arrow + ConnectionArrow.Length).Trim();

            if (!SplitEndpoint(left, out int srcId, out string srcSocket)) return null;
            if (!SplitEndpoint(right, out int dstId, out string dstSocket)) return null;

            return new UnifConnection
            {
                SourceId = srcId,
                SourceSocket = srcSocket,
                TargetId = dstId,
                TargetSocket = dstSocket,
            };
        }

        private static bool SplitEndpoint(string endpoint, out int id, out string socket)
        {
            id = 0;
            socket = null;
            int dot = endpoint.IndexOf('.');
            if (dot < 0)
                return false;
            string idPart = endpoint.Substring(0, dot).Trim();
            socket = endpoint.Substring(dot + 1).Trim();
            return int.TryParse(idPart, NumberStyles.Integer, CultureInfo.InvariantCulture, out id);
        }

        /// <summary>
        /// Split a header into tokens on spaces, honoring double-quoted values
        /// (with backslash escapes) so 'path="my tile.png"' stays one token.
        /// </summary>
        private static List<string> TokenizeHeader(string header)
        {
            var tokens = new List<string>();
            var sb = new StringBuilder();
            bool inQuotes = false;
            bool hasContent = false;

            for (int i = 0; i < header.Length; i++)
            {
                char c = header[i];
                if (inQuotes)
                {
                    if (c == '\\' && i + 1 < header.Length)
                    {
                        sb.Append(header[++i]);
                        hasContent = true;
                    }
                    else if (c == '"')
                    {
                        inQuotes = false;
                    }
                    else
                    {
                        sb.Append(c);
                        hasContent = true;
                    }
                }
                else if (c == '"')
                {
                    inQuotes = true;
                    hasContent = true; // an empty "" is still a real (empty) token
                }
                else if (c == ' ' || c == '\t')
                {
                    if (hasContent)
                    {
                        tokens.Add(sb.ToString());
                        sb.Clear();
                        hasContent = false;
                    }
                }
                else
                {
                    sb.Append(c);
                    hasContent = true;
                }
            }
            if (hasContent)
                tokens.Add(sb.ToString());
            return tokens;
        }

        // --- numeric parsing --------------------------------------------------
        internal static float[] ParseFloatArray(string token)
        {
            string trimmed = token.Trim().TrimStart('[').TrimEnd(']');
            if (trimmed.Length == 0) return Array.Empty<float>();

            string[] parts = trimmed.Split(',');
            var result = new float[parts.Length];
            for (int i = 0; i < parts.Length; i++)
                result[i] = float.Parse(parts[i].Trim(), CultureInfo.InvariantCulture);
            return result;
        }

        internal static int[] ParseIntArray(string token)
        {
            string trimmed = token.Trim().TrimStart('[').TrimEnd(']');
            if (trimmed.Length == 0) return Array.Empty<int>();

            string[] parts = trimmed.Split(',');
            var result = new int[parts.Length];
            for (int i = 0; i < parts.Length; i++)
                result[i] = int.Parse(parts[i].Trim(), CultureInfo.InvariantCulture);
            return result;
        }
    }
}
