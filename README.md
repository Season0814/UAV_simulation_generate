# AI4Sim

面向无人机仿真模型（SDF）的模板驱动生成工具。项目以“顶层框架模板 + 组件级模板”的方式，将完整 SDF 组装任务拆解为惯性、碰撞、可视、关节、传感器、推进等原子片段的生成与回填，从而降低手工编写大规模 SDF 的工程成本。

## 目录结构

- `generator/`：生成器实现与模板库
  - `templates/`：SDF 框架模板与组件模板（惯性/可视/碰撞/关节/传感器/电机等）
  - `sdf_generator.py`：基础生成器（适合“框架 + 电机插件”这一类快速拼装）
  - `universal_sdf_generator.py`：通用生成器（解析框架占位符并逐组件生成、组装）
- `ontology/`：面向无人机的结构化知识整理（用于实现与论文撰写）
- `workspace/`：模型下载/验证等辅助脚本
- `instance/`、`generator/instance/`：生成输出（已在 `.gitignore` 中默认忽略）
- `LLM/`：本地大模型权重目录（体积很大，已在 `.gitignore` 中默认忽略）

## 运行方式

本项目默认使用本地 Hugging Face Transformers 推理管线加载模型。你需要准备好本地模型权重目录，并配置环境变量指向模型路径。

### 1) 设置模型路径

- 主模型（默认）：
  - `AI4SIM_MAIN_PATH=/home/zhike/Season/AI4Sim/LLM/Qwen3-14B`
- 可选：为部分物理域挂载小模型（例如 7B），用于加速/降低显存压力：
  - `AI4SIM_7B_PATH=/home/zhike/Season/AI4Sim/LLM/Qwen2.5-7B-Instruct`

### 2) 运行基础生成器（电机插件快速拼装）

```bash
python /home/zhike/Season/AI4Sim/generator/sdf_generator.py
```

输出会写入 `generator/instance/`。

### 3) 运行通用生成器（逐组件生成并组装完整模型）

```bash
python /home/zhike/Season/AI4Sim/generator/universal_sdf_generator.py
```

输出会写入 `generator/instance/<model_name>/model.sdf`。

## 说明

- 本仓库默认不包含任何大模型权重与生成产物；如需复现实验，请自行下载模型并设置 `AI4SIM_MAIN_PATH` / `AI4SIM_7B_PATH`。
- 生成流程基于模板约束输出严格的 XML 片段，并在组装阶段进行基本的 XML 校验与格式化。

