# AI4Sim

Template-driven SDF generator for UAV simulation models. The project follows a “top-level framework template + component templates” pattern, decomposing a full SDF assembly task into atomic fragments (inertial, collision, visual, joints, sensors, propulsion) and composing them back into a simulation-ready model.

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

## Notes

- This repository does not include large model weights or generated artifacts by default. Download models locally and set `AI4SIM_MAIN_PATH` / `AI4SIM_7B_PATH`.
- The pipeline is template-constrained to produce strictly structured XML fragments, followed by basic XML validation and formatting during final assembly.
