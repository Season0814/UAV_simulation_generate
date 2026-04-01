import re
import time

class ReActAgent:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools
        self.max_steps = 5
        
        # Improved System Prompt for Llama 2
        # Note: Llama 2 Chat uses [INST] <<SYS>> ... <</SYS>> ... [/INST] format
        self.system_prompt = """<<SYS>>
You are a helpful AI assistant with access to the following tools:

{tool_descriptions}

To use a tool, you MUST use the following format:
Thought: Do I need to use a tool? Yes
Action: [The name of the tool]
Action Input: [The input to the tool]
Observation: [The result of the tool]

When you have a response for the user, or if you don't need to use a tool, you MUST use the format:
Thought: Do I need to use a tool? No
Final Answer: [Your response to the user]
<</SYS>>

[INST] User: {user_input} [/INST]
"""

    def run(self, user_input):
        tool_desc = self.tools.get_tools_description()
        prompt = self.system_prompt.format(tool_descriptions=tool_desc, user_input=user_input)
        
        print(f"\n{'='*20} Agent Thinking {'='*20}")
        
        for i in range(self.max_steps):
            # Generate
            print(f"[Step {i+1}] Generatng...")
            response = self.llm.generate(prompt, max_new_tokens=256, stop_sequences=["Observation:"])
            
            # Append response to prompt for next turn (if needed)
            # But wait, we need to parse it first.
            
            # Simple cleanup
            response = response.strip()
            print(f"[Step {i+1}] LLM Output:\n{response}")

            # Check for Final Answer
            if "Final Answer:" in response:
                return response.split("Final Answer:")[-1].strip()

            # Check for Action
            action_match = re.search(r"Action:\s*(.*)", response)
            input_match = re.search(r"Action Input:\s*(.*)", response)

            if action_match and input_match:
                action = action_match.group(1).strip()
                action_input = input_match.group(1).strip()
                
                print(f"[Step {i+1}] Executing Tool: {action} with Input: {action_input}")
                
                observation = self.tools.execute(action, action_input)
                print(f"[Step {i+1}] Observation: {observation}")
                
                # Update prompt with the observation
                # We need to construct the history.
                # Llama 2 context window is 4096.
                prompt += f"\n{response}\nObservation: {observation}\n"
            else:
                # If no action found, maybe it just chatted.
                print(f"[Step {i+1}] No action detected.")
                if "Do I need to use a tool? No" in response:
                     # It probably forgot "Final Answer:"
                     return response.split("Do I need to use a tool? No")[-1].strip()
                
                prompt += f"\n{response}\n"
                
        return "Agent timed out."
