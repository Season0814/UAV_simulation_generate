# X500 Sensors Ontology

This document defines the sensor suite for the X500 quadrotor simulation, including IMU, GPS, Magnetometer, and Barometer, configured for Gazebo Sim.

## 1. Primary Sensors (Flight Control)

The following sensors are attached to the `base_link` in `x500_base/model.sdf`.

### 1.1 Inertial Measurement Unit (IMU)
*   **Type**: `imu`.
*   **Update Rate**: `250 Hz`.
*   **Noise Model**: Gaussian.
    *   **Gyroscope**:
        *   Mean: `0.0`
        *   StdDev: `0.0008726646` rad/s.
    *   **Accelerometer**:
        *   Mean: `0.0`
        *   StdDev (X/Y): `0.00637` m/s².
        *   StdDev (Z): `0.00686` m/s².

### 1.2 Magnetometer
*   **Type**: `magnetometer`.
*   **Update Rate**: `100 Hz`.
*   **Noise Model**: Gaussian.
    *   StdDev: `0.0001` (in Tesla, but sensor reports Gauss - *Note: SDF comment says "noise is in tesla but sensor reports data in gauss"*).

### 1.3 Barometer (Air Pressure)
*   **Type**: `air_pressure`.
*   **Update Rate**: `50 Hz`.
*   **Noise Model**: Gaussian.
    *   Mean: `0`
    *   StdDev: `3` Pa.

### 1.4 GNSS / GPS (NavSat)
*   **Type**: `navsat`.
*   **Update Rate**: `30 Hz`.
*   **Configuration**: Standard Gazebo Sim NavSat sensor.

## 2. Simulation Implementation (SDF Snippet)

Sensors are attached to the `base_link` via `<sensor>` tags.

### IMU Sensor Example
```xml
<sensor name="imu_sensor" type="imu">
  <gz_frame_id>base_link</gz_frame_id>
  <always_on>1</always_on>
  <update_rate>250</update_rate>
  <imu>
    <angular_velocity>
      <x>
        <noise type="gaussian">
          <mean>0.0</mean>
          <stddev>0.0008726646</stddev>
        </noise>
      </x>
      <!-- Repeat for Y, Z -->
    </angular_velocity>
    <linear_acceleration>
      <x>
        <noise type="gaussian">
          <mean>0.0</mean>
          <stddev>0.00637</stddev>
        </noise>
      </x>
      <!-- Repeat for Y, Z -->
    </linear_acceleration>
  </imu>
</sensor>
```
