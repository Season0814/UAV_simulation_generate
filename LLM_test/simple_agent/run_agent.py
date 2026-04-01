from llm_engine import LLMEngine
from tools import registry
from agent import ReActAgent
import sys

# Configuration
MODEL_PATH = "/home/zhike/Season/AI4KG/LLM/Llama-2-13b-chat-hf"

def main():
    print("Initializing Agent System...")
    
    # 1. Load LLM
    try:
        llm = LLMEngine(MODEL_PATH)
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    # 2. Initialize Agent with Tools
    agent = ReActAgent(llm, registry)
    
    print("\n" + "="*50)
    print("Agent is ready! You can ask it to:")
    print("1. Calculate math (e.g., 'What is 123 * 456?')")
    print("2. Check time (e.g., 'What time is it?')")
    print("3. Reverse strings (e.g., 'Reverse hello world')")
    print("Type 'exit' or 'quit' to stop.")
    print("="*50 + "\n")

    # 3. Chat Loop
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            if not user_input.strip():
                continue
                
            response = agent.run(user_input)
            print(f"\nAgent: {response}")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
