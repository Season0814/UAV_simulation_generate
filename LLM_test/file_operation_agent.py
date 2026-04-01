import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_huggingface import HuggingFacePipeline
from langchain.agents import AgentExecutor, create_react_agent, Tool
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.prompts import PromptTemplate
import sys
import os

# 1. 设置模型路径
MODEL_PATH = "/home/zhike/Season/AI4KG/LLM/Llama-2-13b-chat-hf"

# 2. 设置 Agent 的安全工作目录
# 所有的文件操作（读/写/复制等）都会被限制在这个目录下
# 如果 Agent 尝试访问此目录之外的文件，会被拦截
WORK_DIR = "/home/zhike/Season/AI4KG/workspace"
os.makedirs(WORK_DIR, exist_ok=True)

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

# 3. 初始化文件管理工具集 (FileManagementToolkit)
# root_dir 参数是关键：它定义了 Agent 的操作边界
toolkit = FileManagementToolkit(
    root_dir=WORK_DIR,
    selected_tools=["read_file", "write_file", "list_directory"] # 只启用这三个安全工具
)
file_tools = toolkit.get_tools()

# 将文件工具与其他工具合并
tools = file_tools 

# 4. 定义 Prompt
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

# 5. 初始化 Agent
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True, 
    handle_parsing_errors=True,
    max_iterations=5
)

print(f"\nAgent 工作目录已设置为: {WORK_DIR}")
print("您可以让 Agent 创建文件、读取文件或列出目录内容。")
print("例如输入: 'Create a file named hello.txt with content Hello World'")

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
