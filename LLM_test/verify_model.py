import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_PATH = "/home/zhike/Season/AI4KG/LLM/Llama-2-13b-chat-hf"

def verify():
    print(f"Loading model from {MODEL_PATH}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        # Explicitly use safetensors just to be sure, though it's default if bin is missing
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.float16,
            device_map="auto",
            low_cpu_mem_usage=True,
            use_safetensors=True
        )
        print("Model loaded successfully!")
        
        # Simple generation test
        inputs = tokenizer("Hello, how are you?", return_tensors="pt").to(model.device)
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=20)
        print("Generation test passed!")
        print("Output:", tokenizer.decode(outputs[0]))
        return True
    except Exception as e:
        print(f"Verification failed: {e}")
        return False

if __name__ == "__main__":
    verify()
