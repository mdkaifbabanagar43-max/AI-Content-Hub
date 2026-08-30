import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath("."))
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.ai_service import get_gemini_client

print("=" * 70)
print("🔍 CHECKING AVAILABLE MODELS IN GCP / VERTEX AI / GEMINI API")
print("=" * 70)

client = get_gemini_client()

try:
    print("\nFetching models list from Vertex AI / Google GenAI...")
    # List models via google-genai SDK
    models = list(client.models.list())
    print(f"Total models returned: {len(models)}")
    
    video_models = []
    omni_models = []
    flash_models = []
    all_names = []

    for m in models:
        name = getattr(m, 'name', '') or str(m)
        all_names.append(name)
        lower_name = name.lower()
        if "omni" in lower_name:
            omni_models.append(m)
        if "video" in lower_name or "veo" in lower_name:
            video_models.append(m)
        if "flash" in lower_name:
            flash_models.append(m)

    print("\n--- 🎬 VIDEO & VEO MODELS ---")
    if video_models:
        for vm in video_models:
            print(f"- {getattr(vm, 'name', vm)}")
    else:
        print("No models with 'video' or 'veo' in name explicitly listed in models.list()")

    print("\n--- ⚡ OMNI MODELS ---")
    if omni_models:
        for om in omni_models:
            print(f"- {getattr(om, 'name', om)}")
    else:
        print("No models with 'omni' in name explicitly listed in models.list()")

    print("\n--- ⚡ ALL FLASH MODELS ---")
    for fm in flash_models[:15]:
        print(f"- {getattr(fm, 'name', fm)}")

    print("\n--- 📋 FIRST 25 ALL AVAILABLE MODELS ---")
    for nm in all_names[:25]:
        print(f"- {nm}")

except Exception as e:
    import traceback
    print(f"Error listing models: {e}")
    traceback.print_exc()
