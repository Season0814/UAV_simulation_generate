import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_huggingface import HuggingFacePipeline
from langchain.agents import AgentExecutor, create_react_agent, Tool
from langchain_core.prompts import PromptTemplate
import subprocess
import sys

# 1. 设置模型路径
MODEL_PATH = "/home/zhike/Season/AI4KG/LLM/Llama-2-13b-chat-hf"

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
        max_new_tokens=512,
        temperature=0.1,
        top_p=0.95,
        repetition_penalty=1.15,
        return_full_text=False
    )
    llm = HuggingFacePipeline(pipeline=pipe)
except Exception as e:
    print(f"Failed to load model: {e}")
    sys.exit(1)

# 2. 定义 Tmux 工具
def list_tmux_sessions(query=""):
    """List all running tmux sessions."""
    try:
        output = subprocess.check_output(["tmux", "list-sessions"], text=True)
        return output
    except subprocess.CalledProcessError:
        return "No tmux sessions found."
    except Exception as e:
        return f"Error listing sessions: {e}"

def read_tmux_pane(session_name):
    """Read the content of a specific tmux session pane. Input should be the session name."""
    try:
        # -p: print to stdout, -t: target session
        # capture-pane 默认只捕获可见区域，加上 -S -100 可以捕获最近100行
        output = subprocess.check_output(
            ["tmux", "capture-pane", "-p", "-t", session_name, "-S", "-100"], 
            text=True
        )
        return output
    except subprocess.CalledProcessError as e:
        return f"Error reading session '{session_name}': {e}"
    except Exception as e:
        return f"Error: {e}"

tools = [
    Tool(
        name="ListSessions",
        func=list_tmux_sessions,
        description="List all active tmux sessions. Use this first to find available sessions."
    ),
    Tool(
        name="ReadSession",
        func=read_tmux_pane,
        description="Read the text content of a tmux session. Input the session name (e.g. 'my_server')."
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

Begin!

Question: {input}
Thought:{agent_scratchpad}'''

prompt = PromptTemplate.from_template(template)

# 4. 初始化 Agent
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True, 
    handle_parsing_errors=True,
    max_iterations=5
)

print("\n" + "="*50)
print("Tmux Analyzer Agent Ready!")
print("我已经启动了一个名为 'my_server' 的测试 Session，里面有一个模拟的错误。")
print("你可以尝试问：'检查一下 my_server 这个 session 里有什么报错？'")
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
