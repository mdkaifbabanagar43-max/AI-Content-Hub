import os
import sys

sys.path.insert(0, os.path.abspath("."))
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.ai_service import get_gemini_client

client = get_gemini_client()

candidate_models = [
    "gemini-omni-flash-preview",
    "gemini-omni-flash",
    "gemini-2.5-flash-omni",
    "omni-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "veo-3.1-generate-001",
    "veo-2.0-generate-001",
    "imagen-3.0-generate-002"
]

print("=" * 70)
print("🔍 TESTING CANDIDATE MODEL ENDPOINTS ON YOUR GCP PROJECT")
print("=" * 70)

for model_id in candidate_models:
    try:
        # Test basic retrieval
        m = client.models.get(model=model_id)
        print(f"✅ AVAILABLE: {model_id} -> {m}")
    except Exception as e:
        err_msg = str(e)
        if "404" in err_msg or "NotFound" in err_msg or "not found" in err_msg.lower():
            print(f"❌ NOT FOUND / NOT ENABLED: {model_id}")
        else:
            print(f"⚠️ ERROR for {model_id}: {err_msg[:120]}")
