# Node Mapping Reference (v1.0)

Conversion status of Blender shader nodes → Unity Shader Graph.

Status legend:
- **Supported** — full 1:1 conversion.
- **Partial** — converts with caveats or via Custom HLSL.
- **Bake Only** — no node equivalent; baked to a texture on export.
- **Not Supported** — dropped (warning emitted).

## Output & Shader

| Blender Node          | Unity Equivalent        | Status        |
|-----------------------|-------------------------|---------------|
| Material Output       | Master Stack (Fragment) | Supported     |
| Principled BSDF       | Lit (PBR) Node          | Supported     |
| Emission              | Emission Node           | Supported     |
| Mix Shader            | Lerp / Alpha Blend      | Partial       |
| Add Shader            | Add Blend               | Partial       |
| Transparent BSDF      | Alpha Clip / Fade       | Supported     |
| Glass BSDF            | Custom HLSL             | Partial       |
| Subsurface Scattering | N/A                     | Bake Only     |
| Volume Absorption     | N/A                     | Not Supported |
| Volume Scatter        | N/A                     | Not Supported |

## Texture

| Blender Node        | Unity Equivalent   | Status    |
|---------------------|--------------------|-----------|
| Image Texture       | Sample Texture 2D  | Supported |
| Normal Map          | Normal Unpack Node | Supported |
| Noise Texture       | Simple Noise Node  | Supported |
| Voronoi Texture     | Voronoi Noise Node | Supported |
| Musgrave Texture    | Gradient Noise     | Partial   |
| Wave Texture        | Custom HLSL        | Partial   |
| Gradient Texture    | Gradient Node      | Supported |
| Checker Texture     | Checkerboard Node  | Supported |
| Brick Texture       | N/A                | Bake Only |
| Environment Texture | Cubemap Sample     | Partial   |

## Color & Math

| Blender Node         | Unity Equivalent    | Status    |
|----------------------|---------------------|-----------|
| Mix RGB              | Blend Node          | Supported |
| Math                 | Math Node (all ops) | Supported |
| Vector Math          | Vector Math Node    | Supported |
| Color Ramp           | Gradient Node       | Supported |
| Hue/Saturation/Value | HSV Node            | Supported |
| Bright/Contrast      | Contrast Node       | Supported |
| Gamma                | Power Node          | Supported |
| Invert               | One Minus Node      | Supported |
| RGB Curves           | Custom HLSL Curve   | Partial   |

## Input / Coordinate

| Blender Node       | Unity Equivalent          | Status        |
|--------------------|---------------------------|---------------|
| UV Map             | UV Node                   | Supported     |
| Texture Coordinate | UV / Position / Normal    | Supported     |
| Mapping            | Transform UV Node         | Supported     |
| Vertex Color       | Vertex Color Node         | Supported     |
| RGB                | Color Node                | Supported     |
| Value              | Float Node                | Supported     |
| Fresnel            | Fresnel Node              | Supported     |
| Layer Weight       | Fresnel Node              | Partial       |
| Light Path         | N/A                       | Not Supported |
| Object Info        | Object Position (partial) | Partial       |
