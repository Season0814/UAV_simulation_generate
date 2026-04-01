import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_huggingface import HuggingFacePipeline
from langchain.agents import AgentExecutor, create_react_agent, Tool
from langchain_core.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
import datetime
import math
import sys

# 1. Initialize Local LLM Pipeline
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
        return_full_text=False # Important: Set to False for newer LangChain versions to avoid repetition
    )

    # Create LangChain LLM wrapper
    llm = HuggingFacePipeline(pipeline=pipe)
except Exception as e:
    print(f"Failed to load model: {e}")
    sys.exit(1)

# 2. Define Tools
def get_current_time(input_str=""):
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculator(input_str):
    try:
        # Note: In production use a safer math library like numexpr
        return eval(input_str, {"__builtins__": {}}, {"math": math})
    except Exception as e:
        return f"Error: {e}"

tools = [
    Tool(
        name="Time",
        func=get_current_time,
        description="Useful for when you need to know the current time."
    ),
    Tool(
        name="Calculator",
        func=calculator,
        description="Useful for when you need to answer questions about math."
    )
]

# 3. Define Prompt (ReAct Style)
# We define it manually to avoid dependency on langchain hub
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

# 4. Initialize Agent
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True, 
    handle_parsing_errors=True,
    max_iterations=5
)

# 5. Run Loop
print("\n" + "="*50)
print("LangChain Agent Ready! (Type 'exit' to quit)")
print("="*50 + "\n")

while True:
    try:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        
        if not user_input.strip():
            continue
            
        # Run the agent
        response = agent_executor.invoke({"input": user_input})
        print(f"\nAgent: {response['output']}")
        
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Error: {e}")
