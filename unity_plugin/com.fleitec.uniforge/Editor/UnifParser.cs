using System;

namespace UniForge
{
    /// <summary>
    /// Parses .unif text into a <see cref="UnifDocument"/> (spec §5.3 step 11).
    ///
    /// The format is block-based: lines like "[BLOCK ...]" open blocks,
    /// indented "key: value" lines are entries, and connection lines look like
    /// "1.Color -&gt; 0.Base_Color". See docs/FORMAT.md.
    /// </summary>
    public static class UnifParser
    {
        public static UnifDocument ParseFile(string path)
        {
            string text = System.IO.File.ReadAllText(path);
            return Parse(text);
        }

        public static UnifDocument Parse(string text)
        {
            // TODO(v1.0): tokenize blocks, dispatch on header name
            //   [UNIF] / [MESH] / [TRANSFORM] / [MATERIAL] / [NODE ...] /
            //   [CONNECTION] / [TEXTURE_EMBEDDED], populating UnifDocument.
            //   Numeric lists ("[a,b,c, ...]") parse via ParseFloatArray.
            throw new NotImplementedException(
                "UnifParser.Parse — implemented in the importer milestone");
        }

        internal static float[] ParseFloatArray(string token)
        {
            string trimmed = token.Trim().TrimStart('[').TrimEnd(']');
            if (trimmed.Length == 0) return Array.Empty<float>();

            string[] parts = trimmed.Split(',');
            var result = new float[parts.Length];
            for (int i = 0; i < parts.Length; i++)
            {
                result[i] = float.Parse(parts[i].Trim(),
                    System.Globalization.CultureInfo.InvariantCulture);
            }
            return result;
        }
    }
}
