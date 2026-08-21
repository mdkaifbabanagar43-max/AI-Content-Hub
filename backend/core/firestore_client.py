"""
Firestore Client Module
Consolidates all Firestore operations from main.py and firebase_utils.py
"""
import os
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional, Dict, Any

# --- FIRESTORE CLIENT ---
_db = None

def get_db():
    """Get or create Firestore client singleton."""
    global _db
    if _db is None:
        if not firebase_admin._apps:
            try:
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred, {
                    'projectId': os.getenv('GOOGLE_CLOUD_PROJECT', 'shortcutai-backend'),
                })
            except Exception:
                firebase_admin.initialize_app()
        _db = firestore.client()
        print("🔥 Firestore Client Initialized")
    return _db

# Initialize on import
db = get_db()

# --- USER HELPERS ---
def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch user profile from Firestore."""
    try:
        doc = db.collection("users").document(user_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"❌ Error fetching profile: {e}")
        return None

def update_user_profile(user_id: str, data: Dict[str, Any]) -> bool:
    """Update user profile fields in Firestore."""
    try:
        db.collection("users").document(user_id).set(data, merge=True)
        return True
    except Exception as e:
        print(f"❌ Error updating profile: {e}")
        return False

def init_user_if_needed(user_id: str, email: str):
    """Create user profile if it doesn't exist."""
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        print(f"🆕 Creating new user profile for {email}")
        doc_ref.set({
            "email": email,
            "credits": 500,  # Starter tier credits
            "plan": "starter",
            "created_at": firestore.SERVER_TIMESTAMP
        })

# --- JOB MANAGEMENT ---
def create_job(user_id: str, job_type: str, metadata: Optional[Dict] = None) -> Optional[str]:
    """Creates a new job document in 'processing' state. Returns job_id."""
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

def update_job_status(user_id: str, job_id: str, status: str, error_msg: str = None, **kwargs):
    """
    Updates a job's status. Accepts kwargs for extra fields.
    """
    try:
        job_ref = db.collection("users").document(user_id).collection("jobs").document(job_id)
        update_data = {"status": status}
        if error_msg:
            update_data["error"] = error_msg
            
        update_data.update(kwargs)
        
        job_ref.update(update_data)
        print(f"🔄 Job {job_id} Updated -> {status}")
    except Exception as e:
        print(f"❌ Failed to update job status: {e}")

def get_active_job_count(user_id: str) -> int:
    """Counts jobs with status='processing' for a user."""
    try:
        jobs_ref = db.collection("users").document(user_id).collection("jobs")
        query = jobs_ref.where("status", "==", "processing")
        results = query.stream()
        return sum(1 for _ in results)
    except Exception as e:
        print(f"❌ Failed to count active jobs: {e}")
        return 0

def get_job_status(user_id: str, job_id: str) -> Optional[dict]:
    """Get the current status of a job."""
    try:
        job_ref = db.collection("users").document(user_id).collection("jobs").document(job_id)
        doc = job_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"❌ Failed to get job status: {e}")
        return None


# --- PROJECT HELPERS ---
def save_project(user_id: str = None, title: str = "", type: str = "", video_url: str = "", script_summary: str = "") -> Optional[str]:
    """Save a project to Firestore."""
    try:
        if user_id:
            doc_ref = db.collection('users').document(user_id).collection('projects').document()
        else:
            doc_ref = db.collection("projects").document()
            
        doc_ref.set({
            "title": title,
            "type": type,
            "video_url": video_url,
            "script": script_summary,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        print(f"💾 Project saved: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        print(f"❌ Database Save Failed: {e}")
        return None

def get_user_projects(user_id: str) -> list:
    """Fetch user's projects ordered by creation date."""
    try:
        projects_ref = db.collection('users').document(user_id).collection('projects')
        docs = projects_ref.order_by('created_at', direction=firestore.Query.DESCENDING).limit(50).stream()
        
        projects = []
        for doc in docs:
            data = doc.to_dict()
            if 'created_at' in data and data['created_at']:
                data['created_at'] = data['created_at'].isoformat()
            data['id'] = doc.id
            projects.append(data)
        return projects
    except Exception as e:
        print(f"❌ Error fetching projects: {e}")
        return []
