
import os
from openai import OpenAI

api_key = os.environ.get("DEEPSEEK_API_KEY") or "sk-1b73586fde854a329ec187dc371f53ef"
base_url = "https://api.deepseek.com"

client = OpenAI(api_key=api_key, base_url=base_url)

try:
    print(f"Listing models from {base_url}...")
    models = client.models.list()
    for model in models.data:
        print(f" - {model.id}")
except Exception as e:
    print(f"Error listing models: {e}")
