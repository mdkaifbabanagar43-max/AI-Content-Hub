from google.cloud import storage
import os

def set_cors_configuration(bucket_name):
    """Sets the CORS configuration for the bucket."""
    
    # Authenticate
    key_path = "firebase-service-account.json"
    if os.path.exists(key_path):
        print(f"🔑 Using Service Account: {key_path}")
        storage_client = storage.Client.from_service_account_json(key_path)
    else:
        print("⚠️ No Service Account found. Using Default Credentials.")
        storage_client = storage.Client()

    bucket = storage_client.get_bucket(bucket_name)

    # Configure CORS policies
    cors_configuration = [
        {
            "origin": ["*"],  # Allow all origins (Localhost + Production)
            "method": ["GET", "OPTIONS", "HEAD"],
            "responseHeader": ["Content-Type", "Access-Control-Allow-Origin", "x-goog-resumable"],
            "maxAgeSeconds": 3600
        }
    ]

    bucket.cors = cors_configuration
    bucket.patch()

    print(f"✅ CORS configuration set for bucket {bucket.name}")
    print(f"Policy: {bucket.cors}")

if __name__ == "__main__":
    # Target Bucket from firebase_utils.py
    BUCKET_NAME = "leafy-oxide-480614-m4.firebasestorage.app"
    try:
        set_cors_configuration(BUCKET_NAME)
    except Exception as e:
        print(f"❌ Failed to set CORS: {e}")
