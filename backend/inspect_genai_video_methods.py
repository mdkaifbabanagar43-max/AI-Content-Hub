import inspect
import sys
import os

sys.path.insert(0, os.path.abspath("."))
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from google import genai

client = genai.Client(vertexai=True, project="shortcutai-backend", location="us-central1")

print("Methods on client.models:")
for name in dir(client.models):
    if not name.startswith("_"):
        print(f"  - {name}")

if hasattr(client.models, "generate_videos"):
    print("\nSignature of client.models.generate_videos:")
    print(inspect.signature(client.models.generate_videos))

if hasattr(client.models, "generate_video"):
    print("\nSignature of client.models.generate_video:")
    print(inspect.signature(client.models.generate_video))
