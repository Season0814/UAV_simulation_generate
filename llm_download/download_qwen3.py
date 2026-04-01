from huggingface_hub import snapshot_download
import os

model_id = "Qwen/Qwen3-14B"
local_dir = "/home/zhike/Season/AI4Sim/LLM/Qwen3-14B"

os.makedirs(local_dir, exist_ok=True)

print(f"Starting download of {model_id} to {local_dir}...")
try:
    snapshot_download(
        repo_id=model_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False,
        resume_download=True
    )
    print("Download completed successfully!")
except Exception as e:
    print(f"Error downloading model: {e}")
