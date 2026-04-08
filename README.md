# AI4Sim

Template-driven SDF generator for UAV simulation models. The project follows a “top-level framework template + component templates” pattern, decomposing a full SDF assembly task into atomic fragments (inertial, collision, visual, joints, sensors, propulsion) and composing them back into a simulation-ready model.

中文说明见 [README.zh-CN.md](file:///home/zhike/Season/AI4Sim/README.zh-CN.md)

## Repository Structure

- `generator/`: generators and the template library
  - `ontology/`: framework template(s) and component templates (inertial/visual/collision/joint/sensors/motors, etc.)
  - `sdf_generator.py`: baseline generator (quick assembly for “framework + motor plugins”)
  - `universal_sdf_generator.py`: universal generator (parses placeholders and assembles a full model component-by-component)
- `note/`: structured UAV knowledge notes
- `llm_download/`: helper scripts (e.g., model download/verification)
- `instance/`, `generator/instance/`: generated outputs (ignored by default via `.gitignore`)
- `LLM/`: local model weights (very large, ignored by default via `.gitignore`)

## Usage

The project loads local models via Hugging Face Transformers. Prepare your local model weights and configure environment variables to point to the correct paths.

## Prompt Guide (Generating SDF)

In this project, a “prompt” is simply a natural-language description (`user_description`) that drives the generator to produce SDF output. You can use it to:

- Generate the full physical model (links / joints / collisions / sensors)
- Generate motor plugins
- Generate a paired model: base (physical) + model (includes base + motors)

### Generate base (physical) + model (motors) in one call (Recommended)

Call `generate_model_pair()` from [universal_sdf_generator.py](file:///home/zhike/Season/AI4Sim/generator/universal_sdf_generator.py):

```bash
python - << 'PY'
from generator.universal_sdf_generator import UniversalSDFGenerator

desc = (
  "Generate a quadcopter model named 'test3'. "
  "Motor 0 (ccw) at rotor_0_joint/rotor_0, "
  "Motor 1 (ccw) at rotor_1_joint/rotor_1, "
  "Motor 2 (cw) at rotor_2_joint/rotor_2, "
  "Motor 3 (cw) at rotor_3_joint/rotor_3. "
  "Set timeConstantUp=0.02, timeConstantDown=0.04, maxRotVelocity=1200. "
  "Set motorConstant=9.0e-06, momentConstant=0.018."
)

g = UniversalSDFGenerator()
paths = g.generate_model_pair(model_name="test3", user_description=desc)
print(paths)
PY
```

Output locations:

- `generator/instance/test3/test3/model.sdf`: top-level model (includes `<include merge="true">model://test3_base</include>` + motor plugins)
- `generator/instance/test3/test3_base/model.sdf`: base physical model (links / joints / collisions / sensors / meshes)


### Motor prompt patterns

Motor “placement / direction / index” supports several common formats (the exact wording is flexible as long as joint, link, cw/ccw, and index are present):

- `Motor 0 (ccw) at rotor_0_joint/rotor_0`
- `Motor 1: joint rotor_1_joint, link rotor_1, direction ccw, motorNumber 1`
- `Rotor 2: joint rotor_2_joint, link rotor_2, turningDirection cw, motorNumber 2`

Motor parameter overrides use `key=value` (applies to all 4 motor plugins):

- Common keys: `timeConstantUp`, `timeConstantDown`, `maxRotVelocity`, `motorConstant`, `momentConstant`
- Also supported: `commandSubTopic`, `rotorDragCoefficient`, `rollingMomentCoefficient`, `rotorVelocitySlowdownSim`, `motorType`

Note: to avoid trailing punctuation getting into numeric values (e.g., `1200.` / `0.018.`), parsing strips trailing `.`, `,`, `;`, `:` from the value. For best stability, separate values with commas or newlines.

### 1) Configure Model Paths

- Main model (default):
  - `AI4SIM_MAIN_PATH=/home/zhike/Season/AI4Sim/LLM/Qwen3-14B`
- Optional: assign a smaller model (e.g., 7B) for selected physical domains to reduce memory and improve throughput:
  - `AI4SIM_7B_PATH=/home/zhike/Season/AI4Sim/LLM/Qwen2.5-7B-Instruct`

### 2) Run the Baseline Generator (Motor Plugins)

```bash
python /home/zhike/Season/AI4Sim/generator/sdf_generator.py
```

Outputs are written to `generator/instance/`.

### 3) Run the Universal Generator (Full Assembly)

```bash
python /home/zhike/Season/AI4Sim/generator/universal_sdf_generator.py
```

Outputs are written to `generator/instance/<model_name>/model.sdf`.

If you call `generate_model_pair(model_name=..., ...)`, outputs are written to:

- `generator/instance/<model_name>/<model_name>/model.sdf`
- `generator/instance/<model_name>/<model_name>_base/model.sdf` (or your custom `base_model_name`)

## Run in Gazebo Sim 8

Environment setup:

- Install Gazebo Sim 8 (gz-sim8) and its dependencies.
- Make sure the multicopter motor system plugin is available (the model uses `gz-sim-multicopter-motor-model-system`).
- Ensure `gz`, `gz sim`, `gz topic`, and `gz service` are on your `PATH`.

Prerequisites (example: `test1`):

- Top model: `generator/instance/test1/test1/model.sdf` and `model.config` (URI: `model://test1`)
- Base model: `generator/instance/test1/test1_base/model.sdf` and `model.config` (URI: `model://test1_base`)
- Mesh package: `generator/instance/test_model_base/meshes/*` (URI used in SDF: `model://test_model_base/meshes/...`)

### 1) Set resource paths (must be set before starting `gz sim`)

```bash
export GZ_SIM_RESOURCE_PATH=/home/zhike/Season/AI4Sim/generator/instance/test1:/home/zhike/Season/AI4Sim/generator/instance
export IGN_GAZEBO_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH
```

### 2) Start Gazebo

```bash
gz sim -r -v 4 empty.sdf
```

### 3) Spawn the model into the running world

In another terminal:

```bash
gz service -s /world/empty/create \
  --reqtype gz.msgs.EntityFactory --reptype gz.msgs.Boolean --timeout 5000 \
  --req 'sdf_filename: "model://test1", name: "test1", pose: { position: { x: 0, y: 0, z: 0.3 } }'
```

### 4) Takeoff (manual motor speed command)

Find the motor command topic:

```bash
gz topic -l | grep motor_speed
gz topic -i -t /test1/command/motor_speed
```

Send a constant motor speed (repeat in a loop for a stable input stream; stop with Ctrl+C):

```bash
while true; do
  gz topic -t /test1/command/motor_speed -m gz.msgs.Actuators -p 'velocity: 600 velocity: 600 velocity: 600 velocity: 600'
  sleep 0.1
done
```

Stop motors:

```bash
gz topic -t /test1/command/motor_speed -m gz.msgs.Actuators -p 'velocity: 0 velocity: 0 velocity: 0 velocity: 0'
```

Note: this is open-loop control (no attitude controller), so the vehicle may drift or flip. For stable hover, connect a controller (e.g., PX4 SITL) or add a control system plugin.

## Notes

- This repository does not include large model weights or generated artifacts by default. Download models locally and set `AI4SIM_MAIN_PATH` / `AI4SIM_7B_PATH`.
- The pipeline is template-constrained to produce strictly structured XML fragments, followed by basic XML validation and formatting during final assembly.
- The SDF templates under `generator/ontology/*.sdf` were generated from the corresponding OWL files under `generator/ontology/*.owl`, then manually refined into their current form.
