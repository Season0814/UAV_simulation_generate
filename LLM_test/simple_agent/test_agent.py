from llm_engine import LLMEngine
from tools import registry
from agent import ReActAgent
import sys

# Configuration
MODEL_PATH = "/home/zhike/Season/AI4KG/LLM/Llama-2-13b-chat-hf"

def test_math():
    print("Initializing Agent System for Test...")
    llm = LLMEngine(MODEL_PATH)
    agent = ReActAgent(llm, registry)
    
    query = "What is 123 * 456?"
    print(f"\nQuery: {query}")
    response = agent.run(query)
    print(f"\nFinal Response: {response}")

if __name__ == "__main__":
    test_math()
