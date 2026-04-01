# X500 Control Ontology

This document defines the control interface and communication protocols between the Gazebo Sim environment and the PX4 flight stack.

## 1. PX4-Gazebo Bridge (Gazebo Sim)

Unlike Gazebo Classic, which used a direct plugin (`libgazebo_mavlink_interface.so`), Gazebo Sim typically communicates with PX4 via a middleware bridge (e.g., `MicroXRCEAgent` or `px4_gz_bridge`).

### 1.1 Actuator Control
PX4 sends motor commands which are bridged to Gazebo topics subscribed by the `MulticopterMotorModel` plugins.

*   **Command Topic**: `/command/motor_speed` (or namespaced).
*   **Message Type**: `gz.msgs.Actuators` (typically).
*   **Motor Mapping**:
    *   Index 0: Front Right (CCW)
    *   Index 1: Rear Left (CCW)
    *   Index 2: Front Left (CW)
    *   Index 3: Rear Right (CW)

### 1.2 Sensor Data
Gazebo publishes sensor data to topics which are bridged back to PX4.

*   **IMU**: `/imu`
*   **Magnetometer**: `/magnetometer`
*   **Barometer**: `/air_pressure`
*   **NavSat (GPS)**: `/navsat`

## 2. PX4 Mixer (Airframe Config)

The mixer defines how pilot inputs (Roll, Pitch, Yaw, Thrust) are mixed into the 4 motor outputs.

### 2.1 Mixer File: `romfs/px4fmu_common/mixers/quad_x.main.mix`
Standard Quad-X mixing logic:
*   **Roll**: Differential thrust between left and right motors.
*   **Pitch**: Differential thrust between front and rear motors.
*   **Yaw**: Differential torque (CW vs CCW motors).
*   **Thrust**: Common thrust to all motors.
