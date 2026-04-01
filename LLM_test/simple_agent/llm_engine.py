import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, StoppingCriteria, StoppingCriteriaList
import os

class StopOnTokens(StoppingCriteria):
    def __init__(self, stop_token_ids):
        self.stop_token_ids = stop_token_ids

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        for stop_ids in self.stop_token_ids:
            if torch.eq(input_ids[0][-len(stop_ids):], stop_ids).all():
                return True
        return False

class LLMEngine:
    def __init__(self, model_path):
        self.model_path = model_path
        self.tokenizer = None
        self.model = None
        self._load_model()

    def _load_model(self):
        print(f"Loading model from {self.model_path}...")
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model path {self.model_path} does not exist.")
            
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16,
                device_map="auto",
                low_cpu_mem_usage=True
            )
            print(f"Model loaded successfully! Device map: {self.model.hf_device_map}")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise e

    def generate(self, prompt, max_new_tokens=512, temperature=0.7, stop_sequences=None):
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        # Setup stopping criteria if needed
        stopping_criteria = None
        if stop_sequences:
            stop_token_ids = [self.tokenizer(stop_seq, return_tensors="pt").input_ids[0].to(self.model.device) for stop_seq in stop_sequences]
            # Remove start token if present (often added by tokenizer)
            # This is a bit tricky, simplistic approach:
            stop_token_ids = [ids[1:] if ids[0] == self.tokenizer.bos_token_id else ids for ids in stop_token_ids]
            stopping_criteria = StoppingCriteriaList([StopOnTokens(stop_token_ids)])

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=temperature,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id,
                stopping_criteria=stopping_criteria
            )
            
        response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        return response
