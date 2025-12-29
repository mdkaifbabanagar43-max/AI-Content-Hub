import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import storage
import os
import uuid
import datetime

# 1. Initialize Connection (Firestore only)
if not firebase_admin._apps:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(current_dir, "firebase-service-account.json")
    
    if os.path.exists(key_path):
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        print(f"🔥 Firebase Initialized with JSON: {key_path}")
    else:
        # Fallback to Default Credentials (Cloud Run)
        print(f"⚠️ {key_path} not found. Using Default Credentials (Cloud Run)...")
        firebase_admin.initialize_app()

db = firestore.client()
BUCKET_NAME = "leafy-oxide-480614-m4.firebasestorage.app"

# 2. Helper: Upload Video to Cloud (Direct Google Cloud Client + Signed URLs)
def upload_file(file_path, folder="videos"):
    print(f"☁️ Uploading {file_path} to Firebase...")
    try:
        # Determine Credential Source
        current_dir = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(current_dir, "firebase-service-account.json")
        
        if os.path.exists(key_path):
             storage_client = storage.Client.from_service_account_json(key_path)
        else:
             print("Using Default Credentials for Storage...")
             storage_client = storage.Client()

        bucket = storage_client.bucket(BUCKET_NAME)

        unique_name = f"{uuid.uuid4()}"
        
        # Preserve original extension (Merged logic for audio support)
        ext = os.path.splitext(file_path)[1]
        if not ext: ext = ".mp4"
        
        blob = bucket.blob(f"{folder}/{unique_name}{ext}")

        # Guess content type
        content_type = "video/mp4" if ext == ".mp4" else "audio/mpeg" if ext == ".mp3" else None
        
        blob.upload_from_filename(file_path, content_type=content_type, timeout=600)
        
        # ✅ Make Public (Simpler & More Robust due to Cert/Clock issues)
        blob.make_public()
        url = blob.public_url
        
        # Ensure HTTPS
        if url.startswith("http://"):
            url = url.replace("http://", "https://")
        
        print(f"✅ Upload Success: {url}")
        return url
    except Exception as e:
        print(f"❌ Upload Failed: {e}")
        # Print detailed traceback for debugging
        import traceback
        traceback.print_exc()
        return None

# 3. Helper: Save Project to Database
def save_project(title, type, video_url, script_summary=""):
    print(f"💾 Saving project: {title}...")
    try:
        doc_ref = db.collection("projects").document()
        doc_ref.set({
            "title": title,
            "type": type, # 'idea' or 'repurpose'
            "video_url": video_url,
            "script": script_summary,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id
    except Exception as e:
        print(f"❌ Database Save Failed: {e}")
        return None
# 4. Helper: Get User Profile & Check Credits
def get_user_profile(user_id):
    try:
        doc = db.collection("users").document(user_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"❌ Error fetching profile: {e}")
        return None

# 5. Helper: Deduct Credits
def deduct_credits(user_id, amount=None, task_type=None, duration_minutes=1): 
    # Logic: Amount overrides dynamic calc. If amount is None, calc using task_type.
    
    final_cost = 0
    if amount is not None:
        final_cost = amount
    elif task_type:
        # Import config here to avoid circular dependencies if any (lazy import)
        try:
            from config import CREDIT_COSTS
            base_rate = CREDIT_COSTS.get(task_type, 10) # Default 10 if missing
            final_cost = int(base_rate * duration_minutes)
            # Min cost 1
            if final_cost < 1: final_cost = 1
        except ImportError:
            print("⚠️ Config Import Failed. Defaulting to 10 credits.")
            final_cost = 10
            
    print(f"💰 Attempting to deduct {final_cost} credits for {user_id} (Task: {task_type})...")
    
    try:
        doc_ref = db.collection("users").document(user_id)
        
        # Transaction is safer but for MVP simple update is okay
        # Using atomic increment (decrement) is best practice
        doc_ref.update({
            "credits": firestore.Increment(-final_cost)
        })
        print(f"✅ Deducted {final_cost} credits.")
        return True
    except Exception as e:
        print(f"❌ Credit Deduction Failed: {e}")
        return False

# 6. Helper: Init User (if not exists)
def init_user_if_needed(user_id, email):
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        print(f"🆕 Creating new user profile for {email}")
        doc_ref.set({
            "email": email,
            "created_at": firestore.SERVER_TIMESTAMP
        })

# 7. Helper: Job Management
def create_job(user_id, job_type, metadata=None):
    """
    Creates a new job document in 'processing' state.
    Returns: job_id
    """
    try:
        job_ref = db.collection("users").document(user_id).collection("jobs").document()
        job_data = {
            "id": job_ref.id,
            "type": job_type,
            "status": "processing",
            "created_at": firestore.SERVER_TIMESTAMP,
            "credits_deducted": False,
            "metadata": metadata or {}
        }
        job_ref.set(job_data)
        print(f"🆕 Job Created: {job_ref.id} ({job_type})")
        return job_ref.id
    except Exception as e:
        print(f"❌ Failed to create job: {e}")
        return None

def update_job_status(user_id, job_id, status, error_msg=None):
    """
    Updates job status (e.g., to 'failed').
    """
    try:
        job_ref = db.collection("users").document(user_id).collection("jobs").document(job_id)
        update_data = {"status": status}
        if error_msg:
            update_data["error"] = error_msg
        
        job_ref.update(update_data)
        print(f"🔄 Job {job_id} Updated -> {status}")
    except Exception as e:
        print(f"❌ Failed to update job status: {e}")

def get_active_job_count(user_id):
    """
    Counts jobs with status='processing' for a user.
    """
    try:
        jobs_ref = db.collection("users").document(user_id).collection("jobs")
        # Query for processing jobs
        query = jobs_ref.where("status", "==", "processing")
        # Get count (efficient aggregation if available, or len of list)
        # Firestore python client supports aggregation queries in newer versions, 
        # but standard aggregation might be safer:
        results = query.stream()
        count = sum(1 for _ in results)
        return count
    except Exception as e:
        print(f"❌ Failed to count active jobs: {e}")
        return 0

