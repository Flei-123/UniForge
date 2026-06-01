using System.Collections.Generic;

namespace UniForge
{
    /// <summary>
    /// Maps .unif node types to their Unity Shader Graph equivalents and
    /// conversion status. Mirrors docs/NODE_MAPPING.md and the Blender-side
    /// node_map.py.
    /// </summary>
    public static class NodeMap
    {
        public enum Status { Supported, Partial, BakeOnly, NotSupported }

        public readonly struct Mapping
        {
            public readonly string UnityEquivalent;
            public readonly Status Status;

            public Mapping(string unityEquivalent, Status status)
            {
                UnityEquivalent = unityEquivalent;
                Status = status;
            }
        }

        // .unif node type -> Unity Shader Graph equivalent + status.
        public static readonly Dictionary<string, Mapping> Map = new Dictionary<string, Mapping>
        {
            // Output & shader
            { "MaterialOutput", new Mapping("Master Stack (Fragment)", Status.Supported) },
            { "PrincipledBSDF", new Mapping("Lit (PBR) Node", Status.Supported) },
            { "Emission", new Mapping("Emission Node", Status.Supported) },
            { "MixShader", new Mapping("Lerp / Alpha Blend", Status.Partial) },
            { "AddShader", new Mapping("Add Blend", Status.Partial) },
            { "TransparentBSDF", new Mapping("Alpha Clip / Fade", Status.Supported) },
            { "GlassBSDF", new Mapping("Custom HLSL", Status.Partial) },
            { "SubsurfaceScattering", new Mapping("N/A", Status.BakeOnly) },
            { "VolumeAbsorption", new Mapping("N/A", Status.NotSupported) },
            { "VolumeScatter", new Mapping("N/A", Status.NotSupported) },
            // Texture
            { "ImageTexture", new Mapping("Sample Texture 2D", Status.Supported) },
            { "NormalMap", new Mapping("Normal Unpack Node", Status.Supported) },
            { "NoiseTexture", new Mapping("Simple Noise Node", Status.Supported) },
            { "VoronoiTexture", new Mapping("Voronoi Noise Node", Status.Supported) },
            { "MusgraveTexture", new Mapping("Gradient Noise", Status.Partial) },
            { "WaveTexture", new Mapping("Custom HLSL", Status.Partial) },
            { "GradientTexture", new Mapping("Gradient Node", Status.Supported) },
            { "CheckerTexture", new Mapping("Checkerboard Node", Status.Supported) },
            { "BrickTexture", new Mapping("N/A", Status.BakeOnly) },
            { "EnvironmentTexture", new Mapping("Cubemap Sample", Status.Partial) },
            // Color & math
            { "MixRGB", new Mapping("Blend Node", Status.Supported) },
            { "Math", new Mapping("Math Node (all ops)", Status.Supported) },
            { "VectorMath", new Mapping("Vector Math Node", Status.Supported) },
            { "ColorRamp", new Mapping("Gradient Node", Status.Supported) },
            { "HueSaturationValue", new Mapping("HSV Node", Status.Supported) },
            { "BrightContrast", new Mapping("Contrast Node", Status.Supported) },
            { "Gamma", new Mapping("Power Node", Status.Supported) },
            { "Invert", new Mapping("One Minus Node", Status.Supported) },
            { "RGBCurves", new Mapping("Custom HLSL Curve", Status.Partial) },
            // Input / coordinate
            { "UVMap", new Mapping("UV Node", Status.Supported) },
            { "TextureCoordinate", new Mapping("UV / Position / Normal", Status.Supported) },
            { "Mapping", new Mapping("Transform UV Node", Status.Supported) },
            { "VertexColor", new Mapping("Vertex Color Node", Status.Supported) },
            { "RGB", new Mapping("Color Node", Status.Supported) },
            { "Value", new Mapping("Float Node", Status.Supported) },
            { "Fresnel", new Mapping("Fresnel Node", Status.Supported) },
            { "LayerWeight", new Mapping("Fresnel Node", Status.Partial) },
            { "LightPath", new Mapping("N/A", Status.NotSupported) },
            { "ObjectInfo", new Mapping("Object Position (partial)", Status.Partial) },
        };

        public static bool TryGet(string unifType, out Mapping mapping) =>
            Map.TryGetValue(unifType, out mapping);
    }
}
