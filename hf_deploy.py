import sys
import os
from huggingface_hub import HfApi

token = os.environ.get("HF_TOKEN", "")
api = HfApi(token=token)

repo_id = "Tamanna1234/uniscraper-backend"

try:
    print("Creating Hugging Face Space...")
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker",
        exist_ok=True
    )
except Exception as e:
    print(f"Note: {e}")

print("Uploading backend files to Hugging Face (this may take a minute)...")
api.upload_folder(
    folder_path=r"c:\Users\Sajiya\Downloads\uniscraper-main\uniscraper-backend",
    repo_id=repo_id,
    repo_type="space",
    ignore_patterns=["venv/*", "__pycache__/*", ".pytest_cache/*", ".env", "*.pyc"]
)
print("Deployment to Hugging Face successfully initiated!")
print(f"Your space URL will be: https://huggingface.co/spaces/{repo_id}")
