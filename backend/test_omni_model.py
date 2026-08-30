import os
import sys

sys.path.insert(0, os.path.abspath("."))
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.ai_service import get_gemini_client

client = get_gemini_client()

target_ids = [
    "publishers/google/models/gemini-omni-1.1-flash-preview",
    "gemini-omni-1.1-flash-preview",
    "google/gemini-omni-1.1-flash-preview"
]

print("=" * 70)
print("🔍 TESTING EXACT MODEL: gemini-omni-1.1-flash-preview")
print("=" * 70)

for mid in target_ids:
    print(f"\nProbing Model ID: {mid}")
    try:
        m = client.models.get(model=mid)
        print(f"✅ MODEL FOUND & ACCESSIBLE!")
        print(f"   Name: {getattr(m, 'name', 'N/A')}")
        print(f"   Display Name: {getattr(m, 'display_name', 'N/A')}")
        print(f"   Description: {getattr(m, 'description', 'N/A')}")
        print(f"   Supported Actions: {getattr(m, 'supported_actions', 'N/A')}")
        print(f"   Input Token Limit: {getattr(m, 'input_token_limit', 'N/A')}")
        print(f"   Output Token Limit: {getattr(m, 'output_token_limit', 'N/A')}")
    except Exception as e:
        print(f"❌ Could not get model: {e}")

print("\n--- Testing generate_content with gemini-omni-1.1-flash-preview ---")
for mid in target_ids:
    try:
        response = client.models.generate_content(
            model=mid,
            contents="Hello! Tell me in 1 short sentence what video or multimodal capabilities you support."
        )
        print(f"✅ Generation Response from {mid}:")
        print(f"   {response.text}")
        break
    except Exception as e:
        print(f"❌ Generation test failed for {mid}: {e}")
