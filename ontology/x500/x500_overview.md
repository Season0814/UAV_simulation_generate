# X500 Quadrotor Simulation Ontology Overview

This document provides a high-level overview of the simulation ontology for the X500 quadrotor, based on the PX4 autopilot standard and **Gazebo Sim (formerly Ignition)** environment. It defines the file structure required for simulation and the hierarchical decomposition of the drone components.

## 1. Simulation File Structure

The X500 model is typically split into a base model (`x500_base`) containing geometry and sensors, and a top-level model (`x500`) that includes the base and adds motor plugins.

### 1.1 Model Definition Files

*   **`x500_base/model.sdf`**: Defines the physical structure.
    *   **Base Link**: Main frame, flight controller visuals, collision geometry.
    *   **Rotor Links**: Propellers and motor bells (visuals and inertia).
    *   **Joints**: Revolute joints connecting rotors to the base.
    *   **Sensors**: IMU, Magnetometer, Barometer, NavSat (GPS).
*   **`x500/model.sdf`**: The functional simulation model.
    *   **Include**: Includes `model://x500_base`.
    *   **Plugins**: Adds `gz::sim::systems::MulticopterMotorModel` for each motor and `gz::sim::systems::MotorFailureSystem`.
*   **`model.config`**: Metadata file for Gazebo model database.

### 1.2 Geometry Files (Assets)
Located in `x500_base/meshes/`:
*   **`NXP-HGD-CF.dae`**: Main frame visual.
*   **`5010Base.dae`**: Motor base visual.
*   **`5010Bell.dae`**: Motor bell visual.
*   **`1345_prop_ccw.stl`**: Counter-clockwise propeller.
*   **`1345_prop_cw.stl`**: Clockwise propeller.

### 1.3 Environment Files
*   **`*.sdf` (World)**: Defines the simulation environment (physics, lighting, terrain).

### 1.4 PX4 Configuration
*   **`ROMFS/px4fmu_common/init.d-posix/airframes/4001_x500`**: Airframe startup script defining mixer and gains.

## 2. Component Hierarchy (Ontology Structure)

1.  **Frame (`x500_frame.md`)**
    *   Base Link properties (Mass, Inertia, Geometry).
    *   Landing Gear (Collisions).

2.  **Propulsion (`x500_propulsion.md`)**
    *   Motor Plugins (`gz::sim::systems::MulticopterMotorModel`).
    *   Propeller Physical Properties.

3.  **Sensors (`x500_sensors.md`)**
    *   IMU (`gz-sim-imu-system`).
    *   Magnetometer (`gz-sim-magnetometer-system`).
    *   Barometer (`gz-sim-air-pressure-system`).
    *   NavSat (`gz-sim-navsat-system`).

4.  **Control & Interface (`x500_control.md`)**
    *   PX4-Gazebo Bridge.
    *   Control Topics (`/command/motor_speed`).

5.  **Physics (`x500_physics.md`)**
    *   World Physics Parameters (Gravity, Step Size).

## 3. Usage Guide for LLM Agents

*   **Agent 1 (Frame Builder)**: Use `x500_frame.md` to define `x500_base` structure.
*   **Agent 2 (Propulsion Engineer)**: Use `x500_propulsion.md` to add rotors to `x500_base` and motor plugins to `x500`.
*   **Agent 3 (Sensor Specialist)**: Use `x500_sensors.md` to add sensors to `x500_base`.
*   **Agent 4 (System Integrator)**: Use `x500_control.md` to verify topics and integration.
