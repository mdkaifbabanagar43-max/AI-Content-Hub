import os
import sys

sys.path.insert(0, os.path.abspath("."))
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from google import genai
from google.genai import types

project_id = "shortcutai-backend"
locations = ["us-central1", "us"]

candidate_models = [
    "gemini-omni-1.1-flash-preview",
    "publishers/google/models/gemini-omni-1.1-flash-preview",
    "google/gemini-omni-1.1-flash-preview"
]

print("=" * 70)
print("🎬 TESTING client.models.generate_videos WITH GEMINI OMNI FLASH")
print("=" * 70)

for loc in locations:
    print(f"\n--- Location: {loc} ---")
    client = genai.Client(vertexai=True, project=project_id, location=loc)
    for model_name in candidate_models:
        print(f"Testing generate_videos with model='{model_name}'...")
        try:
            op = client.models.generate_videos(
                model=model_name,
                prompt="A cute cartoon puppy jumping on green grass, bright sunlight, 5 seconds.",
                config=types.GenerateVideosConfig(
                    aspect_ratio="9:16",
                    duration_seconds=5,
                    fps=24
                )
            )
            print(f"🎉 OPERATION STARTED SUCCESSFULLY!")
            print(f"   Operation: {op}")
            break
        except Exception as e:
            print(f"   ❌ Error: {e}")
