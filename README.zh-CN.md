# AI4Sim

面向无人机仿真模型的模板驱动 SDF 生成器。本项目采用“顶层框架模板 + 组件模板”的模式，把完整 SDF 的组装任务拆解为更原子化的片段（inertial、collision、visual、joint、sensor、propulsion），再组合为可用于仿真的模型。

English README: [README.md](file:///home/zhike/Season/AI4Sim/README.md)

## 仓库结构

- `generator/`：生成器与模板库
  - `ontology/`：框架模板与组件模板（inertial/visual/collision/joint/sensors/motors 等）
  - `sdf_generator.py`：基础生成器（快速拼装“framework + motor plugins”）
  - `universal_sdf_generator.py`：通用生成器（解析框架占位符，逐组件组装完整模型）
- `note/`：无人机相关结构化知识笔记
- `llm_download/`：辅助脚本（例如模型下载/校验）
- `instance/`、`generator/instance/`：生成产物输出目录（默认通过 `.gitignore` 忽略）
- `LLM/`：本地模型权重（体积很大，默认通过 `.gitignore` 忽略）

## 使用方法

本项目通过 Hugging Face Transformers 加载本地模型。请先准备好本地权重，并通过环境变量配置模型路径。

## 提示词使用指南（生成 SDF）

本项目的“提示词”就是一段自然语言描述（`user_description`），用于驱动生成器产出 SDF。你可以用它来：

- 生成完整物理模型（links / joints / collisions / sensors）
- 生成电机插件（motor plugins）
- 生成成对模型：base（物理）+ model（引用 base 并包含电机插件）

### 一次生成 base（物理）+ model（电机插件）（推荐）

在 Python 里直接调用 [universal_sdf_generator.py](file:///home/zhike/Season/AI4Sim/generator/universal_sdf_generator.py) 的 `generate_model_pair()`：

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

输出位置：

- `generator/instance/test3/test3/model.sdf`：顶层模型（包含 `<include merge="true">model://test3_base</include>` + 电机插件）
- `generator/instance/test3/test3_base/model.sdf`：base 物理模型（links / joints / collisions / sensors / meshes）


### 电机提示词怎么写

电机“位置/方向/编号”支持几种常见写法（无需完全一致，关键是包含 joint、link、cw/ccw、编号信息）：

- `Motor 0 (ccw) at rotor_0_joint/rotor_0`
- `Motor 1: joint rotor_1_joint, link rotor_1, direction ccw, motorNumber 1`
- `Rotor 2: joint rotor_2_joint, link rotor_2, turningDirection cw, motorNumber 2`

电机参数覆盖使用 `key=value` 形式（会对 4 个电机插件统一生效）：

- 常用键：`timeConstantUp`, `timeConstantDown`, `maxRotVelocity`, `motorConstant`, `momentConstant`
- 其它也支持：`commandSubTopic`, `rotorDragCoefficient`, `rollingMomentCoefficient`, `rotorVelocitySlowdownSim`, `motorType`

注意：为了避免像 `1200.` / `0.018.` 这种尾部标点混入数值，解析时会自动剥离 value 末尾的 `.` `,` `;` `:` 等标点；但写提示词时仍建议用逗号或换行分隔更稳。

### 1) 配置模型路径

- 主模型（默认）：
  - `AI4SIM_MAIN_PATH=/home/zhike/Season/AI4Sim/LLM/Qwen3-14B`
- 可选：为某些物理域指定更小的模型（例如 7B），以降低显存并提升吞吐：
  - `AI4SIM_7B_PATH=/home/zhike/Season/AI4Sim/LLM/Qwen2.5-7B-Instruct`

### 2) 运行基础生成器（仅电机插件）

```bash
python /home/zhike/Season/AI4Sim/generator/sdf_generator.py
```

输出写入 `generator/instance/`。

### 3) 运行通用生成器（完整组装）

```bash
python /home/zhike/Season/AI4Sim/generator/universal_sdf_generator.py
```

输出写入 `generator/instance/<model_name>/model.sdf`。

如果你调用的是 `generate_model_pair(model_name=..., ...)`，输出结构为：

- `generator/instance/<model_name>/<model_name>/model.sdf`
- `generator/instance/<model_name>/<model_name>_base/model.sdf`（或你传入的 `base_model_name`）

## 在 Gazebo Sim 8 中运行

环境准备：

- 安装 Gazebo Sim 8（gz-sim8）及其依赖。
- 确认已安装/可找到多旋翼电机系统插件（模型使用 `gz-sim-multicopter-motor-model-system`）。
- 确保 `gz` / `gz sim` / `gz topic` / `gz service` 在 `PATH` 中可用。

前置条件（以 `test1` 为例）：

- 顶层模型：`generator/instance/test1/test1/model.sdf` 和 `model.config`（URI：`model://test1`）
- Base 模型：`generator/instance/test1/test1_base/model.sdf` 和 `model.config`（URI：`model://test1_base`）
- 网格资源包：`generator/instance/test_model_base/meshes/*`（SDF 中使用：`model://test_model_base/meshes/...`）

### 1) 配置资源路径（必须在启动 `gz sim` 之前设置）

```bash
export GZ_SIM_RESOURCE_PATH=/home/zhike/Season/AI4Sim/generator/instance/test1:/home/zhike/Season/AI4Sim/generator/instance
export IGN_GAZEBO_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH
```

### 2) 启动 Gazebo

```bash
gz sim -r -v 4 empty.sdf
```

### 3) 把模型 spawn 到正在运行的 world 里

新开一个终端执行：

```bash
gz service -s /world/empty/create \
  --reqtype gz.msgs.EntityFactory --reptype gz.msgs.Boolean --timeout 5000 \
  --req 'sdf_filename: "model://test1", name: "test1", pose: { position: { x: 0, y: 0, z: 0.3 } }'
```

### 4) 起飞（手动发送电机转速）

先确认电机指令 topic：

```bash
gz topic -l | grep motor_speed
gz topic -i -t /test1/command/motor_speed
```

持续发送固定转速（建议循环发送，按 Ctrl+C 停止循环）：

```bash
while true; do
  gz topic -t /test1/command/motor_speed -m gz.msgs.Actuators -p 'velocity: 600 velocity: 600 velocity: 600 velocity: 600'
  sleep 0.1
done
```

停桨：

```bash
gz topic -t /test1/command/motor_speed -m gz.msgs.Actuators -p 'velocity: 0 velocity: 0 velocity: 0 velocity: 0'
```

注意：这里是开环控制（没有姿态控制器），可能会漂移甚至翻滚。想稳定悬停需要接控制器（例如 PX4 SITL）或增加控制系统插件。

## 备注

- 本仓库默认不包含大模型权重与生成产物。请在本地下载模型并设置 `AI4SIM_MAIN_PATH` / `AI4SIM_7B_PATH`。
- 生成流程受模板约束，产出的 XML 片段会在最终组装阶段做基础校验与格式化。
- `generator/ontology/*.sdf` 目录下的模板文件由对应的 `generator/ontology/*.owl` 本体文件生成得到，并在此基础上进行了人工微调，形成当前版本。
