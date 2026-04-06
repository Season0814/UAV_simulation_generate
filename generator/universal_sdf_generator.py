import torch
import json
import re
import os
import xml.dom.minidom
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_huggingface import HuggingFacePipeline
from langchain.prompts import PromptTemplate

# Configuration
MODEL_PATH = os.getenv("AI4SIM_MAIN_PATH", "/home/zhike/Season/AI4Sim/LLM/Qwen3-14B")
TEMPLATE_DIR = "/home/zhike/Season/AI4Sim/generator/ontology"
INSTANCE_DIR = "/home/zhike/Season/AI4Sim/generator/instance"
OPENAI_ENV_DEFAULT = "/home/zhike/Season/AI4Sim/LLM/ChatGPT5.4/.env"
DOMAIN_MODEL_DEFAULT = "/home/zhike/Season/AI4Sim/LLM/Qwen2.5-7B-Instruct"
DOMAIN_DEVICE_DEFAULT = 0

def _render_template(template_content, values):
    rendered = template_content
    for k, v in values.items():
        rendered = rendered.replace("${" + str(k) + "}", str(v))
    rendered = re.sub(r"<!--[\s\S]*?-->", "", rendered)
    return rendered.strip()

def _extract_motor_specs(user_text):
    if not isinstance(user_text, str) or not user_text.strip():
        return []
    text = user_text.strip()
    text = re.sub(r"ro\s+tor", "rotor", text, flags=re.IGNORECASE)
    specs = []
    def _clean_name(s):
        if s is None:
            return ""
        s = str(s).strip().strip('"').strip("'")
        s = re.sub(r"\s+", "", s)
        s = re.sub(r"[\s\.,;:]+$", "", s)
        return s
    pattern_a = re.compile(
        r"Rotor\s*(\d+)\s*:\s*joint\s*([A-Za-z0-9_:\-\.]+)\s*,\s*link\s*([A-Za-z0-9_:\-\.]+)\s*,\s*turningDirection\s*(cw|ccw)\s*,\s*motorNumber\s*(\d+)",
        re.IGNORECASE,
    )
    for m in pattern_a.finditer(text):
        specs.append(
            {
                "rotorId": int(m.group(1)),
                "jointName": _clean_name(m.group(2)),
                "linkName": _clean_name(m.group(3)),
                "turningDirection": m.group(4).lower(),
                "motorNumber": int(m.group(5)),
            }
        )

    if specs:
        return specs

    pattern_c = re.compile(
        r"Motor\s*(\d+)\s*:\s*joint\s*([A-Za-z0-9_:\-\.\s]+?)\s*,\s*link\s*([A-Za-z0-9_:\-\.\s]+?)\s*,\s*(?:direction|turningDirection)\s*(cw|ccw)(?:\s*,\s*motorNumber\s*(\d+))?",
        re.IGNORECASE,
    )
    for m in pattern_c.finditer(text):
        motor_number = int(m.group(1))
        specs.append(
            {
                "rotorId": motor_number,
                "jointName": _clean_name(m.group(2)),
                "linkName": _clean_name(m.group(3)),
                "turningDirection": m.group(4).lower(),
                "motorNumber": int(m.group(5)) if m.group(5) is not None else motor_number,
            }
        )

    if specs:
        return specs

    pattern_b = re.compile(
        r"Motor\s*(\d+)\s*\((cw|ccw)\)\s*at\s*([A-Za-z0-9_:\-\.]+)/([A-Za-z0-9_:\-\.]+)",
        re.IGNORECASE,
    )
    for m in pattern_b.finditer(text):
        motor_number = int(m.group(1))
        specs.append(
            {
                "rotorId": motor_number,
                "jointName": _clean_name(m.group(3)),
                "linkName": _clean_name(m.group(4)),
                "turningDirection": m.group(2).lower(),
                "motorNumber": motor_number,
            }
        )
    return specs

def _build_default_motor_specs():
    return [
        {"rotorId": 0, "jointName": "rotor_0_joint", "linkName": "rotor_0", "turningDirection": "ccw", "motorNumber": 0},
        {"rotorId": 1, "jointName": "rotor_1_joint", "linkName": "rotor_1", "turningDirection": "ccw", "motorNumber": 1},
        {"rotorId": 2, "jointName": "rotor_2_joint", "linkName": "rotor_2", "turningDirection": "cw", "motorNumber": 2},
        {"rotorId": 3, "jointName": "rotor_3_joint", "linkName": "rotor_3", "turningDirection": "cw", "motorNumber": 3},
    ]

def _extract_motor_param_overrides(user_text):
    if not isinstance(user_text, str) or not user_text.strip():
        return {}
    text = user_text
    keys = [
        "timeConstantUp",
        "timeConstantDown",
        "maxRotVelocity",
        "motorConstant",
        "momentConstant",
        "commandSubTopic",
        "rotorDragCoefficient",
        "rollingMomentCoefficient",
        "rotorVelocitySlowdownSim",
        "motorType",
    ]
    overrides = {}
    for k in keys:
        m = re.search(rf"\b{re.escape(k)}\s*=\s*([^\s,;]+)", text, flags=re.IGNORECASE)
        if not m:
            continue
        v = m.group(1).strip().strip('"').strip("'")
        v = re.sub(r"[\s\.,;:]+$", "", v)
        overrides[k] = v
    return overrides

def _apply_motor_param_overrides_to_plugin_xml(plugin_xml, overrides):
    if not overrides:
        return plugin_xml
    out = plugin_xml
    for k, v in overrides.items():
        pattern = re.compile(rf"(<{re.escape(k)}>\s*)[^<]*(\s*</{re.escape(k)}>)")
        out = pattern.sub(lambda m: f"{m.group(1)}{v}{m.group(2)}", out)
    return out

def _apply_rotor_name_mapping_to_sdf(sdf_xml_text, link_map, joint_map):
    root = ET.fromstring(sdf_xml_text)

    for link in root.findall(".//link"):
        name = link.get("name")
        if name in link_map:
            link.set("name", link_map[name])

    for joint in root.findall(".//joint"):
        name = joint.get("name")
        if name in joint_map:
            joint.set("name", joint_map[name])
        parent = joint.find("parent")
        child = joint.find("child")
        if parent is not None and parent.text:
            p = parent.text.strip()
            if p in link_map:
                parent.text = link_map[p]
        if child is not None and child.text:
            c = child.text.strip()
            if c in link_map:
                child.text = link_map[c]

    for node in root.findall(".//gz_frame_id"):
        if node.text:
            t = node.text.strip()
            if t in link_map:
                node.text = link_map[t]

    return ET.tostring(root, encoding="unicode")

def _load_env_file(env_file_path):
    if not env_file_path:
        return
    try:
        with open(env_file_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and value and (key not in os.environ or not os.environ.get(key)):
                    os.environ[key] = value
    except FileNotFoundError:
        return

def _normalize_openai_chat_completions_url(base_url):
    if not base_url:
        return ""
    url = base_url.strip().rstrip("/")
    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return url + "/chat/completions"
    return url + "/v1/chat/completions"

class OpenAIChatCompletionsLLM:
    def __init__(self, api_key, base_url, model, temperature=0.1, top_p=0.95, max_tokens=4096):
        self.api_key = api_key
        self.url = _normalize_openai_chat_completions_url(base_url)
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.last_usage = {}
        self.usage_totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def reset_usage(self):
        self.last_usage = {}
        self.usage_totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def invoke(self, prompt):
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        if not self.url:
            raise RuntimeError("OPENAI_BASE_URL is not set")
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="ignore") if e.fp else str(e)
            raise RuntimeError(f"OpenAI API HTTPError: {e.code} {e.reason}: {err}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"OpenAI API URLError: {e.reason}") from e

        data = json.loads(raw) if raw else {}
        usage = data.get("usage") if isinstance(data, dict) else None
        if isinstance(usage, dict):
            self.last_usage = dict(usage)
            for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
                try:
                    self.usage_totals[k] = int(self.usage_totals.get(k, 0)) + int(usage.get(k, 0) or 0)
                except Exception:
                    pass
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return raw

class LazyLocalHuggingFaceLLM:
    def __init__(self, model_path, max_new_tokens=4096, temperature=0.1, top_p=0.95, repetition_penalty=1.15):
        self.model_path = model_path
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.repetition_penalty = repetition_penalty
        self._llm = None

    def _ensure_loaded(self):
        if self._llm is not None:
            return
        print(f"Loading local main model from {self.model_path}...")
        tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch.float16,
            device_map="auto",
            low_cpu_mem_usage=True
        )
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            repetition_penalty=self.repetition_penalty,
            return_full_text=False
        )
        self._llm = HuggingFacePipeline(pipeline=pipe)
        print("Local main model loaded successfully.")

    def invoke(self, prompt):
        self._ensure_loaded()
        return self._llm.invoke(prompt)

class FallbackLLM:
    def __init__(self, primary_llm, fallback_llm):
        self.primary_llm = primary_llm
        self.fallback_llm = fallback_llm
        self._warned = False

    def invoke(self, prompt):
        if self.primary_llm is None:
            return self.fallback_llm.invoke(prompt)
        try:
            return self.primary_llm.invoke(prompt)
        except Exception as e:
            if not self._warned:
                print(f"Warning: main LLM failed, using local fallback: {e}")
                self._warned = True
            return self.fallback_llm.invoke(prompt)

class UniversalSDFGenerator:
    def __init__(self, domain_model_paths=None):
        backend = (os.getenv("AI4SIM_LLM_BACKEND") or "auto").strip().lower()
        domain_device = int(os.getenv("AI4SIM_DOMAIN_DEVICE", str(DOMAIN_DEVICE_DEFAULT)))

        if domain_model_paths is None:
            domain_default_path = os.getenv("AI4SIM_DOMAIN_PATH", DOMAIN_MODEL_DEFAULT)
            domain_model_paths = {
                "visual": domain_default_path,
                "collision": domain_default_path,
                "inertial": domain_default_path,
                "joints": domain_default_path,
            }

        self.domain_llms = {}
        self.llm = None

        local_fallback = LazyLocalHuggingFaceLLM(MODEL_PATH)

        if backend in {"auto", "openai"}:
            env_file = os.getenv("AI4SIM_OPENAI_ENV_FILE", OPENAI_ENV_DEFAULT)
            _load_env_file(env_file)

            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            base_url = os.getenv("OPENAI_BASE_URL", "").strip()
            model = os.getenv("OPENAI_MODEL", "").strip()
            if not model:
                model = os.getenv("AI4SIM_OPENAI_MODEL", "gpt-5.4").strip()

            primary = None
            if api_key and base_url and model:
                primary = OpenAIChatCompletionsLLM(
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    temperature=0.1,
                    top_p=0.95,
                    max_tokens=4096,
                )
                print(f"Using OpenAI-compatible API as main LLM (model={model})")
            self.llm = FallbackLLM(primary_llm=primary, fallback_llm=local_fallback)
        else:
            self.llm = local_fallback

        if isinstance(domain_model_paths, dict):
            _cache_by_path = {}
            _failed_paths = set()
            for k, path in domain_model_paths.items():
                if path in _failed_paths:
                    print(f"Warning: failed to load domain LLM for '{k}', will use main LLM")
                    continue
                try:
                    if path in _cache_by_path:
                        self.domain_llms[k] = _cache_by_path[path]
                    else:
                        tok = AutoTokenizer.from_pretrained(path)
                        use_cuda = torch.cuda.is_available()
                        dtype = torch.float16 if use_cuda else torch.float32
                        device_map = "auto" if use_cuda else None
                        mdl = AutoModelForCausalLM.from_pretrained(
                            path,
                            torch_dtype=dtype,
                            device_map=device_map,
                            low_cpu_mem_usage=True
                        )
                        pipe_kwargs = {
                            "model": mdl,
                            "tokenizer": tok,
                            "max_new_tokens": 2048,
                            "temperature": 0.1,
                            "top_p": 0.95,
                            "repetition_penalty": 1.15,
                            "return_full_text": False,
                        }
                        if use_cuda and device_map is None:
                            pipe_kwargs["device"] = domain_device
                        pp = pipeline("text-generation", **pipe_kwargs)
                        _cache_by_path[path] = HuggingFacePipeline(pipeline=pp)
                        self.domain_llms[k] = _cache_by_path[path]
                    print(f"Loaded domain LLM for '{k}' from {path}")
                except Exception as _:
                    print(f"Warning: failed to load domain LLM for '{k}', will use main LLM")
                    _failed_paths.add(path)

    def load_template_content(self, filename):
        path = os.path.join(TEMPLATE_DIR, filename)
        if not os.path.exists(path):
            if not filename.endswith(".template"):
                alt_path = path + ".template"
                if os.path.exists(alt_path):
                    path = alt_path
                else:
                    raise FileNotFoundError(f"Template not found: {path}")
            else:
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
        full_prompt = prompt.format(description=description, template=template_content)
        llm = llm_override if llm_override is not None else self.llm
        response = llm.invoke(full_prompt) if hasattr(llm, "invoke") else str(llm(full_prompt))
        
        # Clean up response
        response = response.replace("```xml", "").replace("```", "").strip()
        
        # Remove </think> tag and everything before it if present (handling Qwen thinking process)
        if "</think>" in response:
            response = response.split("</think>")[-1].strip()

        m = re.search(r"<([A-Za-z_][\w:.-]*)(\s[^>]*)?>[\s\S]*?</\1>", response)
        if m:
            response = m.group(0).strip()
        else:
            m = re.search(r"<([A-Za-z_][\\w:.-]*)(\\s[^>]*)?/>", response)
            if m:
                response = m.group(0).strip()
            else:
                start = response.find("<")
                end = response.rfind(">")
                if start != -1 and end != -1 and end > start:
                    response = response[start:end + 1].strip()
            
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
        full_prompt = prompt.format(free_text=free_text)
        raw = self.llm.invoke(full_prompt) if hasattr(self.llm, "invoke") else str(self.llm(full_prompt))
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

    def generate_full_model(self, model_name, framework_template="model_base.sdf", user_requirements_text=None, user_requirements=None, output_dir=None):
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
                template_name = "inertial.sdf"
            elif "Visual" in placeholder_name or "Visual" in comment_text:
                template_name = "visual.sdf"
            elif "Collision" in placeholder_name or "Collision" in comment_text:
                template_name = "collision.sdf"
            elif "Joint" in placeholder_name or "Joint" in comment_text:
                template_name = "joint.sdf"
            elif "Sensors" in placeholder_name or "Sensors" in comment_text:
                template_name = "standard_sensors.sdf"
            else:
                print(f"[{idx}/{total_components}] Warning: Could not determine template for {placeholder_name}, skipping.")
                continue
                
            print(f"[{idx}/{total_components}] Generating {placeholder_name} using {template_name}...")
            
            # Construct the description for the LLM
            if template_name == "standard_sensors.sdf":
                description = "Generate the standard sensors block. Use the exact default values embedded in the template."
            else:
                description = f"Generate a {template_name.split('.')[0]} component with the following specifications:\n{comment_text}"

            if template_name == "joint.sdf":
                m = re.match(r"rotor(\d+)Joint$", placeholder_name)
                if m:
                    rotor_idx = int(m.group(1))
                    joint_template = self.load_template_content("joint.sdf")
                    component_xml = _render_template(
                        joint_template,
                        {
                            "jointName": f"rotor_{rotor_idx}_joint",
                            "parentLink": "base_link",
                            "childLink": f"rotor_{rotor_idx}",
                            "axisXyz": "0 0 1",
                        },
                    )
                    framework_content = framework_content.replace(f"${{{placeholder_name}}}", component_xml)
                    continue
            
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
        framework_content = re.sub(r"<!--[\s\S]*?-->", "", framework_content)
        
        if output_dir is None:
            output_dir = os.path.join(INSTANCE_DIR, model_name)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "model.sdf")
        
        final_xml = self.prettify_xml(framework_content)
        with open(output_path, 'w') as f:
            f.write(final_xml)
            
        print(f"\nSuccessfully generated full model at: {output_path}")
        return output_path

    def generate_model_pair(self, model_name, user_description, base_model_name=None, pair_root_dir=None):
        motor_specs = _extract_motor_specs(user_description)
        if not motor_specs:
            motor_specs = _build_default_motor_specs()

        motor_specs = sorted(
            motor_specs,
            key=lambda s: int(s.get("motorNumber", s.get("rotorId", 0))),
        )
        motor_param_overrides = _extract_motor_param_overrides(user_description)

        if base_model_name is None:
            base_model_name = f"{model_name}_base"

        if pair_root_dir is None:
            pair_root_dir = os.path.join(INSTANCE_DIR, model_name)
        base_output_dir = os.path.join(pair_root_dir, base_model_name)
        motor_output_dir = os.path.join(pair_root_dir, model_name)

        base_path = self.generate_full_model(
            model_name=base_model_name,
            framework_template="model_base.sdf",
            user_requirements_text=user_description,
            output_dir=base_output_dir,
        )

        link_map = {}
        joint_map = {}
        for i, spec in enumerate(motor_specs[:4]):
            link_map[f"rotor_{i}"] = spec["linkName"]
            joint_map[f"rotor_{i}_joint"] = spec["jointName"]

        if link_map or joint_map:
            with open(base_path, "r", encoding="utf-8", errors="ignore") as f:
                base_text = f.read()
            updated = _apply_rotor_name_mapping_to_sdf(base_text, link_map=link_map, joint_map=joint_map)
            updated = self.prettify_xml(updated)
            with open(base_path, "w", encoding="utf-8") as f:
                f.write(updated)

        motor_template = self.load_template_content("motor_model.sdf")
        motor_plugins = []
        for spec in motor_specs[:4]:
            plugin_xml = _render_template(
                motor_template,
                {
                    "jointName": spec["jointName"],
                    "linkName": spec["linkName"],
                    "turningDirection": spec["turningDirection"],
                    "motorNumber": spec["motorNumber"],
                },
            )
            plugin_xml = _apply_motor_param_overrides_to_plugin_xml(plugin_xml, motor_param_overrides)
            motor_plugins.append(plugin_xml)
        motor_plugins_text = "\n\n".join(motor_plugins).strip()

        framework_template = self.load_template_content("model_framework.sdf")
        final_sdf = framework_template.replace("${modelName}", model_name)
        final_sdf = final_sdf.replace("${baseModelURI}", f"model://{base_model_name}")
        final_sdf = final_sdf.replace("${motorPlugins}", motor_plugins_text)
        final_sdf = re.sub(r"<!--[\s\S]*?-->", "", final_sdf)

        os.makedirs(motor_output_dir, exist_ok=True)
        output_path = os.path.join(motor_output_dir, "model.sdf")

        final_xml = self.prettify_xml(final_sdf)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_xml)

        return {"base_model_path": base_path, "model_path": output_path}

def main():
    generator = UniversalSDFGenerator()
    
    # Generate the complete x500_base SDF
    generator.generate_full_model(model_name="x500_base", framework_template="model_base.sdf")

if __name__ == "__main__":
    main()
