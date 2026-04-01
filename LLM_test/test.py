import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import sys
import os

# Configuration
MODEL_PATH = "/home/zhike/Season/AI4KG/LLM/Llama-2-13b-chat-hf"

def load_model():
    print(f"Loading model from {MODEL_PATH}...")
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model path {MODEL_PATH} does not exist.")
        return None, None
        
    try:
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        
        # Load model with automatic device mapping (uses all available GPUs)
        # 13B model in fp16 takes ~26GB, so it needs >1 GPU (e.g. 2x 4090)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.float16,
            device_map="auto",
            low_cpu_mem_usage=True
        )
        print(f"Model loaded successfully! Device map: {model.hf_device_map}")
        return tokenizer, model
    except Exception as e:
        print(f"Error loading model: {e}")
        return None, None

def chat_loop(tokenizer, model):
    print("\n--- Starting Chat (Type 'exit' to quit) ---")
    
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", "quit"]:
                break
                
            if not user_input.strip():
                continue

            # Format prompt for Llama 2 Chat
            prompt = f"[INST] {user_input} [/INST]"
            
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=512,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    pad_token_id=tokenizer.eos_token_id
                )
                
            response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            print(f"Bot: {response}")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error during generation: {e}")

if __name__ == "__main__":
    tokenizer, model = load_model()
    if model:
        chat_loop(tokenizer, model)
