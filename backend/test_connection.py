import os
import vertexai
from vertexai.generative_models import GenerativeModel
from google.api_core.exceptions import ResourceExhausted, PermissionDenied, NotFound

# --- CONFIGURATION ---
PROJECT_ID = "leafy-oxide-480614-m4"
LOCATION = "us-central1"

# 📋 The "Hit List" - We try these in order:
MODELS_TO_TRY = [
    "gemini-2.0-flash-exp",   # The absolute newest (Experimental)
    "gemini-1.5-flash-002",   # The current standard (Likely the one you need)
    "gemini-1.5-flash-001",   # The old one (Likely failing)
    "gemini-1.5-flash",       # Generic tag (Auto-routes to default)
    "gemini-1.0-pro"          # Old reliable
]

def test_connection():
    print(f"Testing connection for Project: {PROJECT_ID} in {LOCATION}...\n")
    
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
    except Exception as e:
        print(f"❌ INIT ERROR: {str(e)}")
        return

    # Loop through models
    for model_name in MODELS_TO_TRY:
        print(f"👉 Testing: {model_name}...", end=" ")
        try:
            model = GenerativeModel(model_name)
            response = model.generate_content("Are you active?")
            
            # If we get here, IT WORKS
            print(f"\n✅ SUCCESS! Model '{model_name}' is LIVE.")
            print(f"📝 Response: {response.text}\n")
            print(f"🔥 ACTION: Update your code to use model_name='{model_name}'")
            return 
            
        except NotFound:
            print("❌ 404 Not Found (Skipping)")
        except ResourceExhausted:
            print("\n⛔ 429 QUOTA EXCEEDED (Your account is still locked)")
            return # Stop here, because a lock affects all models
        except Exception as e:
            print(f"\n⚠️ Error: {str(e)}")

    print("\n❌ All models failed.")

if __name__ == "__main__":
    test_connection()