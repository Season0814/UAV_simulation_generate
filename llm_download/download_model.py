import os
from huggingface_hub import snapshot_download

# Configuration
MODEL_ID = "NousResearch/Llama-2-13b-chat-hf"
LOCAL_DIR = "/home/zhike/Season/AI4KG/LLM/Llama-2-13b-chat-hf"

def download_model():
    print(f"Starting download of {MODEL_ID} to {LOCAL_DIR}...")
    print("This may take a significant amount of time depending on your internet connection.")
    
    try:
        snapshot_download(
            repo_id=MODEL_ID,
            local_dir=LOCAL_DIR,
            local_dir_use_symlinks=False,
            resume_download=True
        )
        print("Download completed successfully!")
    except Exception as e:
        print(f"An error occurred during download: {e}")

if __name__ == "__main__":
    # Create directory if it doesn't exist
    os.makedirs(LOCAL_DIR, exist_ok=True)
    download_model()
