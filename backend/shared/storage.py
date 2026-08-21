# Shared Storage Module
# Contains GCS upload utilities for all routers

from google.cloud import storage
import os

# Default bucket
GCS_BUCKET = "shortcutai-backend.firebasestorage.app"

def upload_to_gcs(local_path, destination_blob_name, bucket_name=None):
    """
    Uploads a local file to Google Cloud Storage.
    Returns the public URL or None if upload fails.
    """
    try:
        storage_client = storage.Client()
        bucket_name = bucket_name or GCS_BUCKET
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        print(f"☁️ Uploading {local_path} to GCS bucket: {bucket_name}...")
        blob.upload_from_filename(local_path)
        
        # Make Public
        blob.make_public()
        url = blob.public_url
        
        # Ensure HTTPS
        if url.startswith("http://"):
            url = url.replace("http://", "https://")
            
        print(f"✅ GCS Public URL: {url}")
        return url
    except Exception as e:
        print(f"❌ GCS Upload Failed: {e}")
        return None


def generate_signed_upload_url(filename: str, content_type: str, user_id: str, bucket_name=None):
    """
    Generates a signed URL for direct PUT upload to GCS.
    Returns dict with upload_url and public_uri.
    """
    import uuid
    from datetime import timedelta
    
    try:
        storage_client = storage.Client()
        bucket_name = bucket_name or GCS_BUCKET
        bucket = storage_client.bucket(bucket_name)
        
        safe_filename = f"uploads/{user_id}/{uuid.uuid4()}_{filename}"
        blob = bucket.blob(safe_filename)
        
        upload_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="PUT",
            content_type=content_type,
        )
        
        public_uri = f"gs://{bucket_name}/{safe_filename}"
        
        return {
            "upload_url": upload_url,
            "public_uri": public_uri,
            "blob_path": safe_filename
        }
    except Exception as e:
        print(f"❌ Signed URL Generation Failed: {e}")
        raise e
