import os
import google.auth
from google import genai
from config import ModelRoutingConfig

def validate_production_models():
    """Explicit startup validation to check required models against GCP catalog."""
    try:
        print("🔍 Validating Production Model Configuration...")
        credentials, project = google.auth.default()
        client = genai.Client(vertexai=True, project=os.getenv('GOOGLE_CLOUD_PROJECT', 'shortcutai-backend'), location='us-central1')
        
        # Get list of model names
        available_models = [m.name.split('/')[-1] for m in client.models.list()]
        
        required_models = [
            ModelRoutingConfig.VIDEO_DEFAULT,
            ModelRoutingConfig.QUALITY_REVIEW,
            ModelRoutingConfig.SOURCE_ANALYSIS,
            ModelRoutingConfig.NORMAL_STORY,
            ModelRoutingConfig.REFERENCE_IMAGE
        ]
        
        missing = []
        for req in required_models:
            if req not in available_models:
                missing.append(req)
                
        if missing:
            err_msg = f"CRITICAL CONFIGURATION ERROR: Required models {missing} are NOT available in the GCP project model catalog. Validation failed."
            print(f"❌ {err_msg}")
            raise RuntimeError(err_msg)
            
        print("✅ Production Model Configuration Validation Passed!")
        
    except Exception as e:
        print(f"❌ Model Validation Failed: {e}")
        raise e
