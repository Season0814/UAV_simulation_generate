import datetime
import math

class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name, func, description):
        self.tools[name] = {
            "func": func,
            "description": description
        }

    def get_tools_description(self):
        desc = ""
        for name, tool in self.tools.items():
            desc += f"{name}: {tool['description']}\n"
        return desc

    def execute(self, name, input_str):
        if name in self.tools:
            try:
                return str(self.tools[name]["func"](input_str))
            except Exception as e:
                return f"Error executing tool {name}: {str(e)}"
        return f"Tool {name} not found."

# Define some basic skills
def get_current_time(input_str=""):
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculator(input_str):
    """Safe evaluation of math expressions"""
    allowed_names = {"abs": abs, "round": round, "math": math}
    try:
        # Dangerous but simple for demo. In production use a safer parser.
        return eval(input_str, {"__builtins__": {}}, allowed_names)
    except Exception as e:
        return f"Error: {e}"

def reverse_string(input_str):
    return input_str[::-1]

# Initialize and register
registry = ToolRegistry()
registry.register("Time", get_current_time, "Get the current date and time. Input is ignored.")
registry.register("Calculator", calculator, "Calculate a math expression. Input should be a valid python math expression like '2 + 2'.")
registry.register("Reverse", reverse_string, "Reverse a given string. Input is the string to reverse.")
