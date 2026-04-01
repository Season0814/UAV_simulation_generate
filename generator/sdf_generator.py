import torch
import json
import re
import os
import xml.dom.minidom
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_huggingface import HuggingFacePipeline
from langchain.prompts import PromptTemplate

# 1. Configuration
MODEL_PATH = "/home/zhike/Season/AI4Sim/LLM/Qwen3-14B"
TEMPLATE_DIR = "/home/zhike/Season/AI4Sim/generator/templates"
INSTANCE_DIR = "/home/zhike/Season/AI4Sim/generator/instance"

class SDFGenerator:
    def __init__(self):
        print(f"Loading model from {MODEL_PATH}...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
            self.model = AutoModelForCausalLM.from_pretrained(
                MODEL_PATH,
                torch_dtype=torch.float16,
                device_map="auto",
                low_cpu_mem_usage=True
            )
            
            self.pipe = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_new_tokens=4096,  # Increased for full XML output
                temperature=0.1,  # Low temperature for deterministic code generation
                top_p=0.95,
                repetition_penalty=1.15,
                return_full_text=False
            )
            self.llm = HuggingFacePipeline(pipeline=self.pipe)
            print("Model loaded successfully.")
        except Exception as e:
            print(f"Failed to load model: {e}")
            raise

    def load_template_content(self, filename):
        path = os.path.join(TEMPLATE_DIR, filename)
        with open(path, 'r') as f:
            return f.read()

    def generate_model_info(self, description):
        """Extract model name and base URI from description."""
        print("Extracting model parameters...")
        prompt_template = """
        You are an expert PX4 model configuration assistant.
        Based on the user's description, determine the Model Name and Base Model URI.
        
        User Description: {description}
        
        Return ONLY a valid JSON object with keys "modelName" and "baseModelURI".
        Example: {{"modelName": "my_quad", "baseModelURI": "model://x500_base"}}
        Do not include markdown formatting or extra text.
        JSON Output:
        """
        prompt = PromptTemplate(input_variables=["description"], template=prompt_template)
        chain = prompt | self.llm
        response = chain.invoke({"description": description})
        
        # Clean up response to ensure valid JSON
        try:
            # Simple regex extraction for JSON-like structure
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return data
            else:
                print(f"Warning: Could not parse JSON from model info response: {response}")
                # Fallback
                return {"modelName": "custom_x500", "baseModelURI": "model://x500_base"}
        except Exception as e:
            print(f"Error parsing model info: {e}")
            return {"modelName": "custom_x500", "baseModelURI": "model://x500_base"}

    def generate_motor_configs(self, description, motor_template_content):
        """Generate motor configurations based on description."""
        print("Generating motor configurations...")
        prompt_template = """
        You are an expert PX4 motor configuration generator.
        Based on the user's description, generate the XML configuration for ALL motors using the provided template.
        
        User Description: {description}
        
        Template to use for EACH motor:
        {template}
        
        Instructions:
        1. Analyze the description to determine the number of motors and their properties (jointName, linkName, turningDirection, motorNumber).
        2. Generate the XML block for EACH motor by filling in the template variables: ${{jointName}}, ${{linkName}}, ${{turningDirection}}, ${{motorNumber}}.
        3. Concatenate all motor XML blocks into a single string.
        4. Output ONLY the XML content. Do not include markdown code blocks (```xml) or explanations.
        
        Output XML:
        """
        
        prompt = PromptTemplate(
            input_variables=["description", "template"], 
            template=prompt_template
        )
        chain = prompt | self.llm
        response = chain.invoke({"description": description, "template": motor_template_content})
        
        # Clean up markdown if present
        response = response.replace("```xml", "").replace("```", "").strip()
        
        # Remove </think> tag and everything before it if present
        if "</think>" in response:
            response = response.split("</think>")[-1].strip()
            
        return response

    def run(self, description):
        print(f"Generating model for: {description}")
        
        # 1. Load Templates
        framework_template = self.load_template_content("model_framework.sdf.template")
        motor_template = self.load_template_content("motor_model.sdf.template")
        
        # 2. Get Model Info
        model_info = self.generate_model_info(description)
        model_name = model_info.get("modelName", "custom_model")
        base_uri = model_info.get("baseModelURI", "model://x500_base")
        print(f"Model Name: {model_name}, Base URI: {base_uri}")
        
        # 3. Generate Motor Plugins
        motor_plugins = self.generate_motor_configs(description, motor_template)
        
        # 4. Assemble Final SDF
        # Replace framework placeholders
        final_sdf = framework_template.replace("${modelName}", model_name)
        final_sdf = final_sdf.replace("${baseModelURI}", base_uri)
        final_sdf = final_sdf.replace("${motorPlugins}", motor_plugins)

        # 5. Prettify XML
        try:
            # Parse the XML string
            dom = xml.dom.minidom.parseString(final_sdf)
            # Prettify the XML (indent=2 spaces)
            final_sdf = dom.toprettyxml(indent="  ")
            
            # Remove empty lines introduced by minidom
            final_sdf = "\n".join([line for line in final_sdf.split("\n") if line.strip()])
            
        except Exception as e:
            print(f"Warning: XML Prettify failed: {e}")
            # Fallback to original if parsing fails
        
        # 6. Save to File
        output_filename = f"{model_name}.sdf"
        output_path = os.path.join(INSTANCE_DIR, output_filename)
        
        with open(output_path, 'w') as f:
            f.write(final_sdf)
            
        print(f"Successfully generated model at: {output_path}")
        return output_path

if __name__ == "__main__":
    generator = SDFGenerator()
    
    # Example usage based on user context
    user_request = "Generate a standard quadcopter UAV model named 'my_UAV' based on 'model://UAV_base'. It has 4 motors. Motor 0 (ccw) at rotor_0_joint/rotor_0, Motor 1 (ccw) at rotor_1_joint/rotor_1, Motor 2 (cw) at rotor_2_joint/rotor_2, Motor 3 (cw) at rotor_3_joint/rotor_3."
    generator.run(user_request)
