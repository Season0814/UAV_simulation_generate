import torch
import json
import re
import os
import xml.dom.minidom
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_huggingface import HuggingFacePipeline
from langchain.prompts import PromptTemplate

# Configuration
MODEL_PATH = os.getenv("AI4SIM_MAIN_PATH", "/home/zhike/Season/AI4Sim/LLM/Qwen3-14B")
TEMPLATE_DIR = "/home/zhike/Season/AI4Sim/generator/templates"
INSTANCE_DIR = "/home/zhike/Season/AI4Sim/generator/instance"

class UniversalSDFGenerator:
    def __init__(self, domain_model_paths=None):
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
                max_new_tokens=4096,
                temperature=0.1,
                top_p=0.95,
                repetition_penalty=1.15,
                return_full_text=False
            )
            self.llm = HuggingFacePipeline(pipeline=self.pipe)
            self.domain_llms = {}
            if domain_model_paths is None:
                auto_small = os.getenv("AI4SIM_7B_PATH")
                if auto_small:
                    domain_model_paths = {
                        "visual": auto_small,
                        "collision": auto_small,
                    }
            if isinstance(domain_model_paths, dict):
                _cache_by_path = {}
                for k, path in domain_model_paths.items():
                    try:
                        if os.path.abspath(path) == os.path.abspath(MODEL_PATH):
                            self.domain_llms[k] = self.llm
                            print(f"Using main LLM for domain '{k}'")
                            continue
                        if path in _cache_by_path:
                            self.domain_llms[k] = _cache_by_path[path]
                        else:
                            tok = AutoTokenizer.from_pretrained(path)
                            mdl = AutoModelForCausalLM.from_pretrained(
                                path,
                                torch_dtype=torch.float16,
                                device_map="auto",
                                low_cpu_mem_usage=True
                            )
                            pp = pipeline(
                                "text-generation",
                                model=mdl,
                                tokenizer=tok,
                                max_new_tokens=2048,
                                temperature=0.1,
                                top_p=0.95,
                                repetition_penalty=1.15,
                                return_full_text=False
                            )
                            _cache_by_path[path] = HuggingFacePipeline(pipeline=pp)
                            self.domain_llms[k] = _cache_by_path[path]
                        print(f"Loaded domain LLM for '{k}' from {path}")
                    except Exception as _:
                        print(f"Warning: failed to load domain LLM for '{k}', will use main LLM")
            print("Model loaded successfully.")
        except Exception as e:
            print(f"Failed to load model: {e}")
            raise

    def load_template_content(self, filename):
        path = os.path.join(TEMPLATE_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Template not found: {path}")
        with open(path, 'r') as f:
            return f.read()

    def generate_component(self, description, template_name, llm_override=None):
        """
        Generates an SDF component based on a description and a template.
        
        Args:
            description (str): Description of the component parameters.
            template_name (str): Name of the template file (e.g., 'visual.sdf.template').
            
        Returns:
            str: Generated XML content.
        """
        print(f"Generating component using template '{template_name}' for: {description}")
        
        template_content = self.load_template_content(template_name)
        
        prompt_template = """
        You are an expert SDF (Simulation Description Format) generator.
        Your task is to generate an XML component based on the user's description and the provided template.
        
        User Description: {description}
        
        Template:
        {template}
        
        Instructions:
        1. Analyze the description to extract values for the placeholders in the template (e.g., ${{visualName}}, ${{pose}}, ${{size}}).
        2. Fill in the template with the extracted values.
        3. Check the provided template for a 'Defaults' section (usually in comments). If a value is not explicitly provided in the User Description, use the value from the Defaults section.
        4. Output ONLY the filled XML content. Do not include markdown formatting or explanations.
        
        Output XML:
        """
        
        prompt = PromptTemplate(
            input_variables=["description", "template"], 
            template=prompt_template
        )
        chain = prompt | (llm_override if llm_override is not None else self.llm)
        response = chain.invoke({"description": description, "template": template_content})
        
        # Clean up response
        response = response.replace("```xml", "").replace("```", "").strip()
        
        # Remove </think> tag and everything before it if present (handling Qwen thinking process)
        if "</think>" in response:
            response = response.split("</think>")[-1].strip()
            
        return response

    def prettify_xml(self, xml_string):
        try:
            dom = xml.dom.minidom.parseString(xml_string)
            pretty_xml = dom.toprettyxml(indent="  ")
            # Remove empty lines
            return "\n".join([line for line in pretty_xml.split("\n") if line.strip()])
        except Exception as e:
            print(f"Warning: XML Prettify failed: {e}")
            return xml_string
    
    def parse_user_requirements(self, free_text):
        """
        Parse a free-form user requirement into structured per-component overrides.
        Returns a dict like:
        {
          "inertial": {"mass": 3.5, "ixx": 0.035, "iyy": 0.035, "izz": 0.065},
          "visual": {"uri": "model://custom/meshes/frame.dae", "scale": "1 1 1", "name": "base_link_visual"},
          "collision": {"shape": "cylinder", "radius": 0.25, "length": 0.15},
          "joints": [...],
          "sensors": {...}
        }
        """
        if not free_text or not free_text.strip():
            return {}
        
        prompt_template = """
        You are an expert in extracting structured constraints for SDF component generation.
        From the user's free-form requirements, extract only the relevant fields into a STRICT JSON
        object with up to five top-level keys: "inertial", "visual", "collision", "joints", "sensors".
        - inertial: {{ "target": string, "mass": number, "ixx": number, "iyy": number, "izz": number, (optional: "ixy","ixz","iyz": number) }}
        - visual: {{ "target": string, "name": string, "uri": string, "scale": "sx sy sz", (optional: "pose": "x y z r p y") }}
        - collision: either box or cylinder or sphere:
            - {{ "target": string, "shape": "box", "size": "sx sy sz" }} OR
            - {{ "target": string, "shape": "cylinder", "radius": number, "length": number }} OR
            - {{ "target": string, "shape": "sphere", "radius": number }}
        - joints: a list of objects with minimal fields if the user specified joint constraints
        - sensors: object with booleans or parameter maps if user specified sensor overrides
        
        If the user names a specific component such as "base link", preserve that as the "target".
        If the user says to keep a domain as default, omit that domain.
        
        If the user did not specify a domain, omit that top-level key.
        Output ONLY the JSON object, with no explanations or markdown fences.
        
        User Requirements:
        {free_text}
        """
        prompt = PromptTemplate(input_variables=["free_text"], template=prompt_template)
        chain = prompt | self.llm
        raw = chain.invoke({"free_text": free_text})
        cleaned = raw.strip().replace("```json", "").replace("```", "")
        # Attempt to locate JSON braces if extra text slipped through
        json_text = cleaned
        try:
            start = json_text.find("{")
            end = json_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_text = json_text[start:end+1]
            data = json.loads(json_text)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def normalize_component_key(self, text):
        if not text:
            return ""
        return re.sub(r'[^a-z0-9]+', '', str(text).lower())

    def should_apply_override(self, override_value, placeholder_name, comment_text):
        if not override_value:
            return False
        if not isinstance(override_value, dict):
            return True
        target = override_value.get("target")
        if not target:
            return True
        target_key = self.normalize_component_key(target)
        placeholder_key = self.normalize_component_key(placeholder_name)
        comment_key = self.normalize_component_key(comment_text)
        return bool(target_key) and (
            target_key in placeholder_key or
            target_key in comment_key
        )

    def build_prompt_override(self, override_value):
        if not isinstance(override_value, dict):
            return override_value
        return {
            k: v for k, v in override_value.items()
            if k not in {"target"}
        }

    def get_llm_for_domain(self, domain_key):
        if domain_key in self.domain_llms:
            return self.domain_llms[domain_key]
        return self.llm

    def generate_full_model(self, model_name, framework_template="test_model_base.sdf.template", user_requirements_text=None, user_requirements=None):
        """
        Generates a complete SDF model by parsing a framework template, extracting 
        placeholder comments, and generating each component via LLM.
        
        If user_requirements_text (free-form) or user_requirements (structured dict) are provided,
        the per-component prompts will include these overrides, which take precedence over template defaults.
        """
        print(f"Generating full model '{model_name}' using framework '{framework_template}'...")
        framework_content = self.load_template_content(framework_template)
        
        # Replace top-level variables
        framework_content = framework_content.replace("${modelName}", model_name)
        
        # Parse user requirements into a structured dict (once)
        overrides = user_requirements if isinstance(user_requirements, dict) else None
        if overrides is None and isinstance(user_requirements_text, str):
            overrides = self.parse_user_requirements(user_requirements_text)
        if overrides is None:
            overrides = {}
        
        # Pattern to match XML comments followed by a placeholder
        # e.g., <!-- Visual: Body \n Default pose: ... --> \n ${baseLinkVisual}
        pattern = re.compile(r'<!--\s*((?:(?!-->).)*?)\s*-->\s*\$\{([a-zA-Z0-9_]+)\}', re.DOTALL)
        
        matches = list(pattern.finditer(framework_content))
        total_components = len(matches)
        print(f"Found {total_components} components to generate.")
        
        for idx, match in enumerate(matches, 1):
            comment_text = match.group(1).strip()
            placeholder_name = match.group(2)
            
            # Determine template based on placeholder name or comment
            template_name = None
            if "Inertial" in placeholder_name or "Inertial" in comment_text:
                template_name = "inertial.sdf.template"
            elif "Visual" in placeholder_name or "Visual" in comment_text:
                template_name = "visual.sdf.template"
            elif "Collision" in placeholder_name or "Collision" in comment_text:
                template_name = "collision.sdf.template"
            elif "Joint" in placeholder_name or "Joint" in comment_text:
                template_name = "joint.sdf.template"
            elif "Sensors" in placeholder_name or "Sensors" in comment_text:
                template_name = "standard_sensors.sdf.template"
            else:
                print(f"[{idx}/{total_components}] Warning: Could not determine template for {placeholder_name}, skipping.")
                continue
                
            print(f"[{idx}/{total_components}] Generating {placeholder_name} using {template_name}...")
            
            # Construct the description for the LLM
            if template_name == "standard_sensors.sdf.template":
                description = "Generate the standard sensors block. Use the exact default values embedded in the template."
            else:
                description = f"Generate a {template_name.split('.')[0]} component with the following specifications:\n{comment_text}"
            
            # Attach user overrides for the corresponding domain, if present
            domain_key = None
            if template_name.startswith("inertial"):
                domain_key = "inertial"
            elif template_name.startswith("visual"):
                domain_key = "visual"
            elif template_name.startswith("collision"):
                domain_key = "collision"
            elif template_name.startswith("joint"):
                domain_key = "joints"
            
            if (
                domain_key and
                domain_key in overrides and
                overrides[domain_key] and
                self.should_apply_override(overrides[domain_key], placeholder_name, comment_text)
            ):
                try:
                    override_json = json.dumps(
                        self.build_prompt_override(overrides[domain_key]),
                        ensure_ascii=False
                    )
                except Exception:
                    override_json = str(self.build_prompt_override(overrides[domain_key]))
                description += f"\n\nUser overrides (take precedence over defaults):\n{override_json}"
            
            # Choose LLM for the domain and generate
            domain_llm = self.get_llm_for_domain(domain_key) if domain_key else self.llm
            component_xml = self.generate_component(description, template_name, llm_override=domain_llm)
            # Validate XML; if invalid and domain_llm is not main, fallback to main
            try:
                xml.dom.minidom.parseString(component_xml)
            except Exception:
                if domain_llm is not self.llm:
                    print(f"Fallback: regenerating {placeholder_name} with main LLM due to XML parse failure")
                    component_xml = self.generate_component(description, template_name, llm_override=self.llm)
            
            # Substitute the generated XML back into the framework
            # We replace the placeholder exactly
            framework_content = framework_content.replace(f"${{{placeholder_name}}}", component_xml)
            
        # Clean up and save the result
        # Replace test_model back to x500 to match the user's target model structure
        framework_content = framework_content.replace("test_model", "x500")
        
        output_dir = os.path.join(INSTANCE_DIR, model_name)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "model.sdf")
        
        final_xml = self.prettify_xml(framework_content)
        with open(output_path, 'w') as f:
            f.write(final_xml)
            
        print(f"\nSuccessfully generated full model at: {output_path}")
        return output_path

def main():
    generator = UniversalSDFGenerator()
    
    # Generate the complete x500_base SDF
    generator.generate_full_model(model_name="x500_base", framework_template="test_model_base.sdf.template")

if __name__ == "__main__":
    main()
