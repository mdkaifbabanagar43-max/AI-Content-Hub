"""
Projects Router
Save and retrieve user projects
"""
from fastapi import APIRouter, Depends, HTTPException, Form
from pydantic import BaseModel
from firebase_admin import firestore

from core.auth import get_current_user
from core.firestore_client import db, get_user_projects, save_project

router = APIRouter()

# --- REQUEST MODELS ---
class SaveProjectRequest(BaseModel):
    user_id: str
    topic: str
    video_url: str
    script: str = ""
    start_time: str = ""
    platform: str = "tiktok"
    mood: str = "fast"

# --- ENDPOINTS ---
@router.post("/save-project")
def save_project_endpoint(request: SaveProjectRequest, user_id: str = Depends(get_current_user)):
    """Manual project save."""
    print(f"💾 Manual Save Request for: {request.topic}")
    try:
        doc_ref = db.collection('users').document(user_id).collection('projects').add({
            'topic': request.topic,
            'script': request.script[:500],
            'video_url': request.video_url,
            'created_at': firestore.SERVER_TIMESTAMP,
            'platform': request.platform,
            'mood': request.mood,
            'type': 'generated_v2'
        })
        print(f"✅ Project Saved: {doc_ref[1].id}")
        return {"success": True, "id": doc_ref[1].id}
    except Exception as e:
        print(f"❌ Save Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/my-projects")
@router.get("/api/projects")
def get_my_projects(user_id: str = Depends(get_current_user)):
    """Fetch projects for authenticated user."""
    print(f"Fetching projects for secure user: {user_id}")
    projects = get_user_projects(user_id)
    return {"projects": projects}

@router.delete("/api/projects/{project_id}")
def delete_project(project_id: str, user_id: str = Depends(get_current_user)):
    """Delete a project from the user's library."""
    try:
        doc_ref = db.collection('users').document(user_id).collection('projects').document(project_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Project not found")
        doc_ref.delete()
        print(f"Deleted project {project_id} for user {user_id}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
