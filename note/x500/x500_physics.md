# X500 Physics Ontology

This document defines the physics environment and aerodynamic properties for the X500 quadrotor simulation in Gazebo Sim.

## 1. Physics Engine Configuration (World File)

Gazebo Sim typically uses the DART physics engine by default, though others (Bullet, ODE) are supported.

### 1.1 Physics Parameters
*   **Gravity**: `0 0 -9.8` (Standard Earth Gravity).
*   **Step Size (max_step_size)**: `0.004` seconds (250 Hz physics update).
*   **Real Time Factor**: `1.0` (Target real-time speed).

### 1.2 Ground Plane
*   **Model**: `ground_plane`.
*   **Friction**: High friction coefficients to prevent sliding.
*   **Restitution**: Low to prevent bouncing.

## 2. Aerodynamics (Base Link)

### 2.1 Drag Properties
*   **Linear/Angular Drag**: Can be simulated using `gz-sim-lift-drag-system`.
*   **Note**: Basic models often rely on linear damping in the link definition or the motor model's drag coefficients.

### 2.2 Wind (Optional)
*   **Plugin**: `gz-sim-wind-effects-system`.
*   **Usage**: Defines global wind velocity and gusts affecting all `lift-drag` enabled links.

## 3. Simulation Implementation (World File Snippet)

```xml
<physics name="1ms" type="ignored">
  <max_step_size>0.004</max_step_size>
  <real_time_factor>1.0</real_time_factor>
</physics>

<!-- Wind Plugin Example (in World) -->
<plugin filename="gz-sim-wind-effects-system"
        name="gz::sim::systems::WindEffects">
  <force_approximation_scaling_factor>1</force_approximation_scaling_factor>
  <horizontal>
    <magnitude>
      <time_for_rise>10</time_for_rise>
      <sin>
        <amplitude_percent>0.05</amplitude_percent>
        <period>60</period>
      </sin>
      <noise type="gaussian">
       <mean>0</mean>
       <stddev>0.0002</stddev>
      </noise>
    </magnitude>
    <direction>
      <time_for_rise>30</time_for_rise>
      <sin>
        <amplitude>5</amplitude>
        <period>20</period>
      </sin>
    </direction>
  </horizontal>
  <vertical>
    <noise type="gaussian">
     <mean>0</mean>
     <stddev>0.0002</stddev>
    </noise>
  </vertical>
</plugin>
```
