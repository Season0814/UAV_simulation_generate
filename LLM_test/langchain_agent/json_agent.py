import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Configuration
MODEL_PATH = "/home/zhike/Season/AI4KG/LLM/Llama-2-13b-chat-hf"

# Define tools with JSON schemas
TOOLS_SCHEMA = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "The temperature unit"
                }
            },
            "required": ["location"]
        }
    }
]

def get_weather(location, unit="celsius"):
    # Mock function
    return json.dumps({"location": location, "temperature": "22", "unit": unit, "condition": "Sunny"})

SYSTEM_PROMPT = """You are a helpful assistant with access to the following functions:
{tools_schema}

To use a function, you must respond with a JSON object in the following format:
{{
    "function": "function_name",
    "arguments": {{
        "arg1": "value1",
        "arg2": "value2"
    }}
}}

If you don't need to use a function, just respond with plain text.
"""

class JSONAgent:
    def __init__(self):
        print(f"Loading model from {MODEL_PATH}...")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.float16,
            device_map="auto",
            low_cpu_mem_usage=True
        )
        
    def generate(self, user_input):
        # Construct prompt
        formatted_schema = json.dumps(TOOLS_SCHEMA, indent=2)
        prompt = f"[INST] <<SYS>>\n{SYSTEM_PROMPT.format(tools_schema=formatted_schema)}\n<</SYS>>\n\nUser: {user_input} [/INST]"
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=True,
                temperature=0.1 # Low temp for structured output
            )
            
        response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        return response

    def run(self, user_input):
        print(f"\nThinking...")
        response = self.generate(user_input)
        print(f"Raw LLM Output: {response}")
        
        # Try to parse JSON
        try:
            # Simple heuristic to find JSON blob
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = response[start:end]
                action = json.loads(json_str)
                
                if "function" in action and action["function"] == "get_weather":
                    print(f"\nCreating Tool Call: {action['function']}({action['arguments']})")
                    result = get_weather(**action['arguments'])
                    print(f"Tool Result: {result}")
                    
                    # Optional: Feed back to LLM (omitted for brevity)
                    return f"The weather in {action['arguments']['location']} is Sunny, 22 degrees."
        except Exception as e:
            print(f"JSON Parsing failed: {e}")
            
        return response

if __name__ == "__main__":
    agent = JSONAgent()
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        print(f"Agent: {agent.run(user_input)}")
