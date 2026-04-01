# X500 Propulsion Ontology

This document defines the propulsion system for the X500 quadrotor, including motors, propellers, and their physical/simulation properties.

## 1. Propulsion System Overview

The X500 uses a standard Quadrotor X configuration with 4 brushless DC motors and propellers.

### 1.1 Motor Attributes (Simulated)
*   **Max Rotational Velocity**: `1000.0 rad/s`.
*   **Motor Constant**: `8.54858e-06`.
*   **Moment Constant**: `0.016`.
*   **Time Constant (Up/Down)**: `0.0125` / `0.025` seconds.
*   **Rotor Drag Coefficient**: `8.06428e-05`.
*   **Rolling Moment Coefficient**: `1e-06`.

### 1.2 Rotor/Propeller Physical Properties
Properties for the combined rotor link (Propeller + Motor Bell):
*   **Mass**: `0.016076923076923075 kg`.
*   **Inertia**:
    *   `ixx`: `3.8464910483993325e-07`
    *   `iyy`: `2.6115851691700804e-05`
    *   `izz`: `2.649858234714004e-05`

## 2. Component Definitions

### 2.1 Rotor Links (x4)
*   **Visuals**:
    *   **Propeller**: `model://x500_base/meshes/1345_prop_ccw.stl` (or cw).
    *   **Motor Bell**: `model://x500_base/meshes/5010Bell.dae`.
*   **Collision**: Box `0.279 x 0.0169 x 0.0008` (Simplified blade).

### 2.2 Motor Joints
*   **Type**: `revolute`.
*   **Axis**: `0 0 1`.
*   **Limits**: Infinite (`-1e16` to `1e16`).

### 2.3 Motor Positions (Relative to Base Link)
*   **Rotor 0 (Front Right, CCW)**: `x: 0.174, y: -0.174, z: 0.06`.
*   **Rotor 1 (Rear Left, CCW)**: `x: -0.174, y: 0.174, z: 0.06`.
*   **Rotor 2 (Front Left, CW)**: `x: 0.174, y: 0.174, z: 0.06`.
*   **Rotor 3 (Rear Right, CW)**: `x: -0.174, y: -0.174, z: 0.06`.

## 3. Simulation Plugins (Gazebo Sim)

Each motor uses the `gz::sim::systems::MulticopterMotorModel` plugin.

### Plugin Parameters Template
```xml
<plugin filename="gz-sim-multicopter-motor-model-system"
  name="gz::sim::systems::MulticopterMotorModel">
  <jointName>rotor_0_joint</jointName>
  <linkName>rotor_0</linkName>
  <turningDirection>ccw</turningDirection>
  <timeConstantUp>0.0125</timeConstantUp>
  <timeConstantDown>0.025</timeConstantDown>
  <maxRotVelocity>1000.0</maxRotVelocity>
  <motorConstant>8.54858e-06</motorConstant>
  <momentConstant>0.016</momentConstant>
  <commandSubTopic>command/motor_speed</commandSubTopic>
  <motorNumber>0</motorNumber>
  <rotorDragCoefficient>8.06428e-05</rotorDragCoefficient>
  <rollingMomentCoefficient>1e-06</rollingMomentCoefficient>
  <rotorVelocitySlowdownSim>10</rotorVelocitySlowdownSim>
  <motorType>velocity</motorType>
</plugin>
```
