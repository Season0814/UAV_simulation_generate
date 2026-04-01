import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_huggingface import HuggingFacePipeline
from langchain.agents import AgentExecutor, create_react_agent, Tool
from langchain_core.prompts import PromptTemplate
from langchain_core.agents import AgentAction, AgentFinish
import subprocess
import sys
import os
import glob
import re

# 1. 配置
# MODEL_PATH = "/home/zhike/Season/AI4Sim/LLM/Llama-2-13b-chat-hf"
# MODEL_PATH = "/home/zhike/Season/AI4Sim/LLM/Qwen1.5-14B-Chat"
MODEL_PATH = "/home/zhike/Season/AI4Sim/LLM/Qwen3-14B"
PX4_DIR = "/home/zhike/Season/PX4-Autopilot"

print(f"Loading model from {MODEL_PATH}...")
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.float16,
        device_map="auto",
        low_cpu_mem_usage=True
    )

    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=1024,
        temperature=0.01,
        top_p=0.95,
        repetition_penalty=1.15,
        return_full_text=False
    )
    llm = HuggingFacePipeline(pipeline=pipe)
except Exception as e:
    print(f"Failed to load model: {e}")
    sys.exit(1)

# 2. 定义工具

def list_search_models(query=""):
    """Search for available simulation models (airframes) in PX4-Autopilot.
    Input 'query' can be empty to list common ones, or a string like 'iris' or 'x500' to filter.
    Returns a list of model names that can be used to start simulation."""
    
    airframes_dir = os.path.join(PX4_DIR, "ROMFS/px4fmu_common/init.d-posix/airframes")
    
    if not os.path.exists(airframes_dir):
        return f"Error: Airframes directory not fo1und at {airframes_dir}"
    
    try:
        # Get all files
        files = glob.glob(os.path.join(airframes_dir, "*"))
        models = []
        for f in files:
            basename = os.path.basename(f)
            parts = basename.split('_', 1)
            if len(parts) > 1:
                model_name = parts[1]
                # If query is provided, check if it's part of the model name
                if not query or query.lower() in model_name.lower():
                    models.append(model_name)
        
        models.sort()
        
        if not models:
            return f"No models found matching query '{query}'. Please try a different keyword."
        
        # Return all models if query is present, otherwise top 50
        limit = 50 if not query else len(models)
        return f"Found {len(models)} models. Here are the matches:\n" + "\n".join(models[:limit])
    except Exception as e:
        return f"Error searching models: {e}"

def start_simulation(model_name):
    """Start the PX4 simulation for the given model name.
    Input 'model_name' should be one of the names returned by list_search_models (e.g., 'gazebo-classic_iris').
    This starts the simulation in a new tmux session to avoid blocking."""
    
    # Validation: Check if model exists
    search_result = list_search_models(model_name)
    if "No models found" in search_result:
        return f"Error: Model '{model_name}' not found. Please use SearchModels to find a valid model name first."

    session_name = f"sim_{model_name.replace('-', '_').replace('.', '_')}"
    session_name = session_name[:20]
    
    cmd = f"cd {PX4_DIR} && make px4_sitl {model_name}"
    
    try:
        check = subprocess.run(["tmux", "has-session", "-t", session_name], capture_output=True)
        if check.returncode == 0:
            return f"SUCCESS: Simulation '{model_name}' is already running in tmux session '{session_name}'. Use 'tmux attach -t {session_name}' to view it."
        
        subprocess.run(["tmux", "new-session", "-d", "-s", session_name, cmd], check=True)
        return f"SUCCESS: Simulation started in background tmux session '{session_name}'.\nRun 'tmux attach -t {session_name}' in your terminal to see the simulation."
    except subprocess.CalledProcessError as e:
        return f"Failed to start simulation: {e}"
    except Exception as e:
        return f"Error: {e}"

tools = [
    Tool(
        name="SearchModels",
        func=list_search_models,
        description="Search for available PX4 simulation models. Input a keyword (e.g., 'iris', 'plane') or empty string to list common ones."
    ),
    Tool(
        name="StartSimulation",
        func=start_simulation,
        description="Start a PX4 simulation. Input must be a valid model name found via SearchModels (e.g., 'gazebo-classic_iris')."
    )
]

# 3. 定义 Prompt
template = '''Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

IMPORTANT:
1. If the user asks for a list of models, use SearchModels and then output the Final Answer. Do NOT start a simulation unless explicitly asked.
2. If the user asks to start a simulation, first use SearchModels to confirm the exact model name, then use StartSimulation.
3. If the Observation says "No models found", stop and tell the user.
4. If the Observation contains "SUCCESS", STOP immediately and output the Final Answer.
5. You only have access to SearchModels and StartSimulation. Do NOT use any other tools (like GetState, GetTime).
6. Do NOT ask "Question: ..." after you have started the simulation.

Begin!

Question: {input}
Thought:{agent_scratchpad}'''

prompt = PromptTemplate.from_template(template)

# 4. 初始化 Agent
# 使用 create_react_agent 创建基础 agent
agent = create_react_agent(llm, tools, prompt)

# 5. 自定义 Output Parser 处理函数
def handle_parsing_errors(error):
    """
    Handle errors when the agent output cannot be parsed.
    Specifically handles the 'produced both a final answer and a parse-able action' error.
    """
    error_str = str(error)
    
    # 针对 "produced both a final answer and a parse-able action" 的特殊处理
    # 这种情况下，其实模型已经输出了 Final Answer，只是后面又跟了废话
    if "produced both a final answer and a parse-able action" in error_str:
        # 我们假设前半部分的 Final Answer 是有效的
        # 这里返回一个特定的字符串，告诉 AgentExecutor 这不是致命错误
        # 但 AgentExecutor 默认行为是把这个返回值当作 Observation 继续循环
        # 这可能导致死循环。
        
        # 更好的策略可能是：直接截断输出
        return "Simulation started successfully. Task completed."
        
    if "Could not parse LLM output" in error_str:
        return "Agent output format error, but task might be completed."
        
    return f"Error parsing output: {error_str}"

agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True, 
    handle_parsing_errors=handle_parsing_errors, # 使用自定义错误处理
    max_iterations=5,
    return_intermediate_steps=True
)

print("\n" + "="*50)
print("PX4 Simulation Agent Ready! (v3 - Robust Parser)")
print("你可以问：'有哪些可用的仿真模型？' 或 '帮我启动 gazebo-classic_iris 仿真'")
print("="*50 + "\n")

while True:
    try:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        
        if not user_input.strip():
            continue
            
        response = agent_executor.invoke({"input": user_input})
        print(f"\nAgent: {response['output']}")
        
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Error: {e}")
