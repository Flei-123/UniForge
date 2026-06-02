using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.AssetImporters;
using UnityEngine;

namespace UniForge
{
    /// <summary>
    /// Custom inspector for imported .unif assets (spec §5.4): source file info,
    /// object/material/texture counts, and a texture list.
    /// </summary>
    [CustomEditor(typeof(UnifImporter))]
    public class UniForgeInspector : ScriptedImporterEditor
    {
        private UnifDocument _doc;
        private string _error;

        public override void OnEnable()
        {
            base.OnEnable();
            ParseSummary();
        }

        private void ParseSummary()
        {
            _doc = null;
            _error = null;
            try
            {
                string path = ((ScriptedImporter)target).assetPath;
                _doc = UnifParser.ParseFile(path);
            }
            catch (System.Exception e)
            {
                _error = e.Message;
            }
        }

        public override void OnInspectorGUI()
        {
            EditorGUILayout.LabelField("UniForge", EditorStyles.boldLabel);

            if (_error != null)
                EditorGUILayout.HelpBox("Could not read .unif: " + _error, MessageType.Error);
            else if (_doc != null)
                DrawSummary(_doc);

            EditorGUILayout.Space();
            ApplyRevertGUI();
        }

        private void DrawSummary(UnifDocument doc)
        {
            EditorGUILayout.LabelField("Format version", string.IsNullOrEmpty(doc.Version) ? "—" : doc.Version);
            EditorGUILayout.LabelField("Generator", doc.Generator ?? "—");
            EditorGUILayout.LabelField("Source", doc.SourceFile ?? "—");

            int materials = doc.Objects.Sum(o => o.Materials.Count);
            int nodes = doc.Objects.Sum(o => o.Materials.Sum(m => m.Nodes.Count));
            EditorGUILayout.LabelField("Objects", doc.Objects.Count.ToString());
            EditorGUILayout.LabelField("Materials", materials.ToString());
            EditorGUILayout.LabelField("Shader nodes", nodes.ToString());
            EditorGUILayout.LabelField("Embedded textures", doc.EmbeddedTextures.Count.ToString());

            // Referenced (non-embedded) textures, collected across all materials.
            var referenced = new SortedSet<string>();
            foreach (UnifObject obj in doc.Objects)
                foreach (UnifMaterial mat in obj.Materials)
                    foreach (UnifNode node in mat.Nodes)
                        if (node.Type == "ImageTexture"
                            && node.Attributes.TryGetValue("path", out string p)
                            && !doc.EmbeddedTextures.ContainsKey(p))
                            referenced.Add(p);

            if (doc.EmbeddedTextures.Count > 0 || referenced.Count > 0)
            {
                EditorGUILayout.Space();
                EditorGUILayout.LabelField("Textures", EditorStyles.boldLabel);
                foreach (string name in doc.EmbeddedTextures.Keys.OrderBy(n => n))
                    EditorGUILayout.LabelField("• " + name, "embedded");
                foreach (string name in referenced)
                    EditorGUILayout.LabelField("• " + name, "file");
            }
        }

        // Re-parse when the asset is reimported via Apply.
        protected override void Apply()
        {
            base.Apply();
            ParseSummary();
        }
    }
}
