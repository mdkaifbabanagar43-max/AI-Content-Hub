import os
import sys
import time

sys.path.insert(0, os.path.abspath("."))
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from google import genai

project_id = "shortcutai-backend"
location = "us-central1"
model_id = "publishers/google/models/gemini-omni-1.1-flash-preview"

print(f"Connecting to {model_id} in {location}...")
client = genai.Client(vertexai=True, project=project_id, location=location)

for attempt in range(3):
    try:
        print(f"Attempt {attempt+1}: Generating with {model_id}...")
        response = client.models.generate_content(
            model=model_id,
            contents="Say 'Hello from Gemini Omni 1.1 Flash Preview!' and list your 2 key features in 1 sentence."
        )
        print("🎉 SUCCESSFUL RESPONSE FROM OMNI FLASH:")
        print(response.text)
        break
    except Exception as e:
        print(f"  Attempt {attempt+1} error: {e}")
        time.sleep(2)
