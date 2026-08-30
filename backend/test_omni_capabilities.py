import os
import sys

sys.path.insert(0, os.path.abspath("."))
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from google import genai
from google.genai import types

project_id = "shortcutai-backend"
location = "us-central1"
model_id = "publishers/google/models/gemini-omni-1.1-flash-preview"

print(f"Connecting to {model_id} in {location}...")
client = genai.Client(vertexai=True, project=project_id, location=location)

try:
    print("\n1. Testing text generation / conversation...")
    response = client.models.generate_content(
        model=model_id,
        contents="Explain what video generation, editing, and multimodal capabilities you provide as gemini-omni-1.1-flash-preview in 2 short bullet points."
    )
    print("✅ Response:")
    print(response.text)
except Exception as e:
    print(f"❌ Text test error: {e}")

try:
    print("\n2. Checking model details & supported modalities...")
    m = client.models.get(model=model_id)
    print(f"Model object: {m}")
except Exception as e:
    print(f"Details error: {e}")
