import os
import sys

# Add backend directory to sys.path to allow relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ai_service import get_gemini_client, get_gemini_model, GEMINI_MODEL_NAME

def test_new_client():
    print("--- Testing New GenAI Client ---")
    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents="Say 'Hello, World!' and nothing else."
        )
        print("✅ New Client Response:", response.text)
    except Exception as e:
        print("❌ New Client Failed:", e)

def test_legacy_wrapper():
    print("\n--- Testing Legacy Wrapper ---")
    try:
        model = get_gemini_model()
        response = model.generate_content("Say 'Hello, Legacy World!' and nothing else.")
        print("✅ Legacy Wrapper Response:", response.text)
    except Exception as e:
        print("❌ Legacy Wrapper Failed:", e)

if __name__ == "__main__":
    test_new_client()
    test_legacy_wrapper()
