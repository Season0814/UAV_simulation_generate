import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_huggingface import HuggingFacePipeline
from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.tools import ShellTool
from langchain_core.prompts import PromptTemplate
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

# 2. 初始化 Shell 工具
# ShellTool 允许 Agent 执行任意 Shell 命令并获取输出
# 警告：这是一个非常强大的工具，Agent 可以执行 rm -rf 等危险命令
# 在生产环境中，建议封装成更安全的特定命令工具
shell_tool = ShellTool()
shell_tool.description = shell_tool.description + f" args {shell_tool.args}".replace("{", "{{").replace("}", "}}")

tools = [shell_tool]

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
print("Terminal Agent Ready! (小心：Agent 可以执行系统命令)")
print("你可以问：'当前目录下有什么文件？' 或 '查看系统 Python 版本'")
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
