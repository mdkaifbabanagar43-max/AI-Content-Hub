import os
import sys

sys.path.insert(0, os.path.abspath("."))
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from google import genai

regions = ["us-central1", "us-east4", "us-west1", "europe-west4", "asia-northeast1"]
target = "publishers/google/models/gemini-omni-1.1-flash-preview"

for reg in regions:
    print(f"\nTesting region: {reg} ...")
    try:
        c = genai.Client(vertexai=True, project="shortcutai-backend", location=reg)
        m = c.models.get(model=target)
        print(f"🎉 FOUND in {reg}! -> {m}")
        break
    except Exception as e:
        err = str(e)
        if "404" in err:
            print(f"  404 Not Found in {reg}")
        else:
            print(f"  Error in {reg}: {err[:100]}")
