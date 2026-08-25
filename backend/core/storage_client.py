"""
Storage Client Module
Google Cloud Storage operations extracted from main.py
"""
import os
import uuid
import shutil
import datetime
from typing import Optional
from google.cloud import storage
from google.oauth2 import service_account

# --- GCS CLIENT ---
_storage_client = None

def get_storage_client():
    """Get or create Storage client with proper credentials."""
    global _storage_client
    if _storage_client is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        key_path = os.path.join(backend_dir, "service-account.json")
        
        if os.path.exists(key_path):
            try:
                creds = service_account.Credentials.from_service_account_file(key_path)
                _storage_client = storage.Client(credentials=creds)
                print("[GCS] Initialized with service account")
            except Exception as e:
                print(f"[WARNING] Failed to load service account: {e}")
                # Try ADC fallback
                try:
                    _storage_client = storage.Client()
                    print("[GCS] Fallback initialized with ADC")
                except Exception as adc_err:
                    _storage_client = None
                    raise Exception(f"Failed to initialize GCS with service account or ADC: {adc_err}")
        else:
            try:
                # Try loading with ADC (Application Default Credentials)
                _storage_client = storage.Client()
                print("[GCS] Initialized with Application Default Credentials (ADC)")
            except Exception as adc_err:
                _storage_client = None
                print(f"[WARNING] ADC Initialization failed: {adc_err}")
                raise Exception("service-account.json not found and ADC initialization failed.")
    
    if _storage_client is None:
        raise Exception("GCS client is not initialized.")
    return _storage_client

# --- BUCKET NAMES ---
UPLOAD_BUCKET = os.getenv("GCS_BUCKET_NAME", "shortcutai-user-uploads-2026")
FIREBASE_BUCKET = UPLOAD_BUCKET

# --- UPLOAD FUNCTIONS ---
def upload_to_gcs(local_path: str, destination_blob_name: str, bucket_name: str = None) -> Optional[str]:
    """
    Upload a file to GCS and return public URL.
    Uses UPLOAD_BUCKET by default.
    """
    try:
        client = get_storage_client()
        bucket_name = bucket_name or FIREBASE_BUCKET
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        print(f"[GCS] Uploading {local_path} to GCS bucket: {bucket_name}...")
        blob.upload_from_filename(local_path, timeout=600)
        


        url = generate_signed_get_url(destination_blob_name, bucket_name, expiration_hours=168)
        
        # Ensure HTTPS
        if url and url.startswith("http://"):
            url = url.replace("http://", "https://")
            
        print(f"[SUCCESS] GCS URL: {url}")
        return url
    except Exception as e:
        print(f"[ERROR] GCS Upload Failed: {e}. Falling back to local serving.")
        filename = os.path.basename(destination_blob_name)
        from config import TEMP_DIR, LOCAL_BASE_URL
        dest_path = os.path.join(TEMP_DIR, filename)
        if os.path.abspath(local_path) != os.path.abspath(dest_path):
            try:
                shutil.copy2(local_path, dest_path)
            except Exception as copy_err:
                print(f"[WARNING] Failed to copy local file for fallback: {copy_err}")
                return None
        return f"{LOCAL_BASE_URL}/temp/{filename}"

def upload_file(file_path: str, folder: str = "videos") -> Optional[str]:
    """
    Upload file to GCS Storage bucket with auto-generated name.
    """
    try:
        client = get_storage_client()
        bucket = client.bucket(FIREBASE_BUCKET)
        
        # Preserve original extension
        ext = os.path.splitext(file_path)[1] or ".mp4"
        unique_name = f"{uuid.uuid4()}{ext}"
        blob = bucket.blob(f"{folder}/{unique_name}")
        
        # Guess content type
        content_type = "video/mp4" if ext == ".mp4" else "audio/mpeg" if ext == ".mp3" else None
        
        blob.upload_from_filename(file_path, content_type=content_type, timeout=600)
        


        url = generate_signed_get_url(f"{folder}/{unique_name}", FIREBASE_BUCKET, expiration_hours=168)
        
        # Ensure HTTPS
        if url and url.startswith("http://"):
            url = url.replace("http://", "https://")
        
        print(f"[SUCCESS] Upload Success: {url}")
        return url
    except Exception as e:
        print(f"[ERROR] Upload Failed: {e}. Falling back to local serving.")
        filename = os.path.basename(file_path)
        from config import TEMP_DIR, LOCAL_BASE_URL
        dest_path = os.path.join(TEMP_DIR, filename)
        if os.path.abspath(file_path) != os.path.abspath(dest_path):
            try:
                shutil.copy2(file_path, dest_path)
            except Exception as copy_err:
                print(f"[WARNING] Failed to copy local file: {copy_err}")
                return None
        return f"{LOCAL_BASE_URL}/temp/{filename}"

def generate_signed_upload_url(filename: str, content_type: str = "video/mp4") -> dict:
    """
    Generate a signed URL for direct PUT upload to GCS.
    Works natively on Cloud Run using IAM Credentials API.
    Returns: {"upload_url": str, "gcs_path": str}
    """
    try:
        import google.auth
        
        client = get_storage_client()
        safe_filename = os.path.basename(filename)
        blob_name = f"raw_uploads/{uuid.uuid4()}_{safe_filename}"
        bucket = client.bucket(UPLOAD_BUCKET)
        blob = bucket.blob(blob_name)
        
        creds, _ = google.auth.default()
        service_account_email = "835818829937-compute@developer.gserviceaccount.com"
        
        # Determine if we need impersonated credentials
        if not hasattr(creds, 'signer') and not hasattr(creds, 'sign_bytes'):
            from google.auth import impersonated_credentials
            creds = impersonated_credentials.Credentials(
                source_credentials=creds,
                target_principal=service_account_email,
                target_scopes=["https://www.googleapis.com/auth/devstorage.read_write", "https://www.googleapis.com/auth/iam"]
            )
        
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=15),
            method="PUT",
            content_type=content_type,
            credentials=creds
        )
        
        return {"upload_url": url, "gcs_path": blob_name}
    except Exception as e:
        print(f"[ERROR] Signed Upload URL Generation Failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate secure upload URL: {str(e)}")

def download_from_gcs(gcs_path: str, local_path: str, bucket_name: str = None) -> bool:
    """Download a file from GCS to local path with strict path traversal protection."""
    try:
        client = get_storage_client()
        bucket_name = bucket_name or UPLOAD_BUCKET
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)
        blob.download_to_filename(local_path)
        print(f"[SUCCESS] Downloaded {gcs_path} to {local_path}")
        return True
    except Exception as e:
        print(f"[WARNING] GCS Download Failed: {e}. Checking local cache.")
        # Local fallback: only allow exact basename within TEMP_DIR
        from config import TEMP_DIR
        safe_filename = os.path.basename(gcs_path)
        local_src = os.path.join(TEMP_DIR, safe_filename)
        if os.path.exists(local_src) and os.path.isfile(local_src):
            try:
                shutil.copy2(local_src, local_path)
                print(f"[SUCCESS] Local Fallback: Copied {local_src} to {local_path}")
                return True
            except Exception as copy_err:
                print(f"[WARNING] Failed to copy local cached file: {copy_err}")
        return False

def download_gcs_uri(gcs_uri: str, destination_path: str) -> None:
    """
    Download a fully-qualified gs://<bucket>/<object> URI to a local path.

    Unlike download_from_gcs (scoped to UPLOAD_BUCKET with local-cache
    fallback), this handles ARBITRARY buckets — e.g. Vertex AI Veo staging
    buckets returned by generation jobs — and FAILS CLOSED by raising on any
    error so callers treat it as a generation failure.

    Replaces the legacy `subprocess ["gsutil", "cp", ...]` calls: the gsutil
    binary is not guaranteed to exist inside Cloud Run containers.
    """
    if not gcs_uri or not gcs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI (expected gs://bucket/object): {gcs_uri!r}")

    bucket_name, _, blob_path = gcs_uri[5:].partition("/")
    if not bucket_name or not blob_path:
        raise ValueError(f"Malformed GCS URI: {gcs_uri!r}")

    client = get_storage_client()
    print(f"[GCS] Downloading {gcs_uri} -> {destination_path}")
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.download_to_filename(destination_path)
    print(f"[SUCCESS] Downloaded {gcs_uri} to {destination_path}")

def generate_signed_get_url(blob_name: str, bucket_name: str = None, expiration_hours: int = 1) -> Optional[str]:
    """Generate a signed URL for GET (download) access."""
    try:
        import google.auth
        
        client = get_storage_client()
        bucket_name = bucket_name or UPLOAD_BUCKET
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        creds, _ = google.auth.default()
        service_account_email = "835818829937-compute@developer.gserviceaccount.com"
        
        # Use impersonated credentials if ADC can't sign natively
        if not hasattr(creds, 'signer') and not hasattr(creds, 'sign_bytes'):
            from google.auth import impersonated_credentials
            creds = impersonated_credentials.Credentials(
                source_credentials=creds,
                target_principal=service_account_email,
                target_scopes=["https://www.googleapis.com/auth/devstorage.read_write", "https://www.googleapis.com/auth/iam"]
            )
        
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=expiration_hours),
            method="GET",
            credentials=creds
        )
        return url
    except Exception as e:
        print(f"[WARNING] Signed URL Gen Failed: {e}")
        return None
