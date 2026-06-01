using UnityEditor;
using UnityEditor.AssetImporters;
using UnityEngine;

namespace UniForge
{
    /// <summary>
    /// Custom inspector for imported .unif assets (spec §5.4): source file info,
    /// node count, texture list, re-import button, node-graph preview.
    /// </summary>
    [CustomEditor(typeof(UnifImporter))]
    public class UniForgeInspector : ScriptedImporterEditor
    {
        public override void OnInspectorGUI()
        {
            EditorGUILayout.LabelField("UniForge", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "Imported .unif asset. Source info, node count, and texture list " +
                "will appear here once the importer is implemented.",
                MessageType.Info);

            // TODO(v1.1): source_file, node count, texture list, graph preview.

            ApplyRevertGUI();
        }
    }
}
