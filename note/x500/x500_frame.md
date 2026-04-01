# X500 Frame Ontology

This document defines the physical structure and inertial properties of the X500 quadrotor frame for simulation generation, based on the `x500_base` model.

## 1. Component Overview: `base_link`

The primary structural component of the quadrotor. It serves as the parent link for all other components (motors, sensors).

### 1.1 Physical Properties
*   **Mass**: `2.0 kg` (Total mass including frame, battery, avionics, excluding rotors).
*   **Center of Mass (CoM)**: `[0, 0, 0]` (Geometric center assumption).
*   **Inertia Tensor**:
    *   `ixx`: `0.02166666666666667` kg·m²
    *   `iyy`: `0.02166666666666667` kg·m²
    *   `izz`: `0.04000000000000001` kg·m²
    *   `ixy`, `ixz`, `iyz`: `0.0`

### 1.2 Geometry & Visuals

The frame geometry uses specific meshes for high fidelity.

*   **Main Frame Visual**:
    *   **Mesh**: `model://x500_base/meshes/NXP-HGD-CF.dae`
    *   **Pose**: `0 0 .025 0 0 3.141592654`
*   **Motor Base Visuals (x4)**:
    *   **Mesh**: `model://x500_base/meshes/5010Base.dae`
    *   **Poses**:
        *   Front Right: `0.174 -0.174 .032 0 0 -.45`
        *   Rear Left: `-0.174 0.174 .032 0 0 -.45`
        *   Front Left: `0.174 0.174 .032 0 0 -.45`
        *   Rear Right: `-0.174 -0.174 .032 0 0 -.45`
*   **Flight Controller Visuals**:
    *   NXP FMUK66 planes with textures (`nxp.png`, `rd.png`).

### 1.3 Collision Geometry (Primitives)

The collision model is decomposed into primitive boxes for efficient physics calculation.

*   **Central Hub**: Box `0.353 x 0.353 x 0.05`
*   **Legs/Landing Gear**:
    *   Vertical parts: Box `0.015 x 0.015 x 0.21` (Rotated)
    *   Horizontal parts: Box `0.25 x 0.015 x 0.015`

### 1.4 Dimensions
*   **Motor Position**: +/- 0.174 m in X and Y from center.
*   **Wheelbase (Diagonal)**: ~500 mm (sqrt(0.174^2 + 0.174^2) * 2 = 0.492 m).

## 2. Simulation Implementation (SDF Snippet)

```xml
<link name="base_link">
  <inertial>
    <mass>2.0</mass>
    <inertia>
      <ixx>0.02166666666666667</ixx>
      <iyy>0.02166666666666667</iyy>
      <izz>0.04000000000000001</izz>
    </inertia>
  </inertial>
  <visual name="base_link_visual">
    <pose>0 0 .025 0 0 3.141592654</pose>
    <geometry>
      <mesh>
        <uri>model://x500_base/meshes/NXP-HGD-CF.dae</uri>
      </mesh>
    </geometry>
  </visual>
  <!-- Additional visuals for motor bases and collision boxes... -->
</link>
```
