"""Blender node type -> .unif node type + conversion status.

Mirrors docs/NODE_MAPPING.md. Keyed by Blender ``bl_idname``. The ``unif_type``
is the type string written into [NODE] blocks and resolved again on the Unity
side by NodeMap.cs.
"""

from enum import Enum


class Status(Enum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    BAKE_ONLY = "bake_only"
    NOT_SUPPORTED = "not_supported"


# bl_idname -> (unif_type, Status)
NODE_MAP = {
    # Output & shader
    "ShaderNodeOutputMaterial": ("MaterialOutput", Status.SUPPORTED),
    "ShaderNodeBsdfPrincipled": ("PrincipledBSDF", Status.SUPPORTED),
    "ShaderNodeEmission": ("Emission", Status.SUPPORTED),
    "ShaderNodeMixShader": ("MixShader", Status.PARTIAL),
    "ShaderNodeAddShader": ("AddShader", Status.PARTIAL),
    "ShaderNodeBsdfTransparent": ("TransparentBSDF", Status.SUPPORTED),
    "ShaderNodeBsdfGlass": ("GlassBSDF", Status.PARTIAL),
    "ShaderNodeSubsurfaceScattering": ("SubsurfaceScattering", Status.BAKE_ONLY),
    "ShaderNodeVolumeAbsorption": ("VolumeAbsorption", Status.NOT_SUPPORTED),
    "ShaderNodeVolumeScatter": ("VolumeScatter", Status.NOT_SUPPORTED),
    # Texture
    "ShaderNodeTexImage": ("ImageTexture", Status.SUPPORTED),
    "ShaderNodeNormalMap": ("NormalMap", Status.SUPPORTED),
    "ShaderNodeTexNoise": ("NoiseTexture", Status.SUPPORTED),
    "ShaderNodeTexVoronoi": ("VoronoiTexture", Status.SUPPORTED),
    "ShaderNodeTexMusgrave": ("MusgraveTexture", Status.PARTIAL),
    "ShaderNodeTexWave": ("WaveTexture", Status.PARTIAL),
    "ShaderNodeTexGradient": ("GradientTexture", Status.SUPPORTED),
    "ShaderNodeTexChecker": ("CheckerTexture", Status.SUPPORTED),
    "ShaderNodeTexBrick": ("BrickTexture", Status.BAKE_ONLY),
    "ShaderNodeTexEnvironment": ("EnvironmentTexture", Status.PARTIAL),
    # Color & math
    "ShaderNodeMixRGB": ("MixRGB", Status.SUPPORTED),
    "ShaderNodeMath": ("Math", Status.SUPPORTED),
    "ShaderNodeVectorMath": ("VectorMath", Status.SUPPORTED),
    "ShaderNodeValToRGB": ("ColorRamp", Status.SUPPORTED),
    "ShaderNodeHueSaturation": ("HueSaturationValue", Status.SUPPORTED),
    "ShaderNodeBrightContrast": ("BrightContrast", Status.SUPPORTED),
    "ShaderNodeGamma": ("Gamma", Status.SUPPORTED),
    "ShaderNodeInvert": ("Invert", Status.SUPPORTED),
    "ShaderNodeRGBCurve": ("RGBCurves", Status.PARTIAL),
    # Input / coordinate
    "ShaderNodeUVMap": ("UVMap", Status.SUPPORTED),
    "ShaderNodeTexCoord": ("TextureCoordinate", Status.SUPPORTED),
    "ShaderNodeMapping": ("Mapping", Status.SUPPORTED),
    "ShaderNodeVertexColor": ("VertexColor", Status.SUPPORTED),
    "ShaderNodeRGB": ("RGB", Status.SUPPORTED),
    "ShaderNodeValue": ("Value", Status.SUPPORTED),
    "ShaderNodeFresnel": ("Fresnel", Status.SUPPORTED),
    "ShaderNodeLayerWeight": ("LayerWeight", Status.PARTIAL),
    "ShaderNodeLightPath": ("LightPath", Status.NOT_SUPPORTED),
    "ShaderNodeObjectInfo": ("ObjectInfo", Status.PARTIAL),
}


def lookup(bl_idname):
    """Return ``(unif_type, Status)`` for a Blender node, or ``(None, None)``."""
    return NODE_MAP.get(bl_idname, (None, None))
