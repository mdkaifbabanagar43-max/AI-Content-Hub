"""
Core Authentication Module
Extracts Firebase authentication logic from main.py
"""
import os
from typing import Optional
from fastapi import Header, HTTPException, Depends
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials

# --- FIREBASE INITIALIZATION ---
def init_firebase():
    """Initialize Firebase Admin SDK if not already initialized."""
    if not firebase_admin._apps:
        try:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {
                'projectId': os.getenv('GOOGLE_CLOUD_PROJECT', 'shortcutai-backend'),
            })
            print(f"🔥 Firebase Auth Initialized (Project: {os.getenv('GOOGLE_CLOUD_PROJECT', 'shortcutai-backend')})")
        except Exception as e:
            print(f"⚠️ Firebase Init Failed: {e}. Trying no-auth init...")
            firebase_admin.initialize_app()

# Initialize on module load
init_firebase()

# --- AUTH DEPENDENCY ---
async def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """
    FastAPI dependency that verifies Firebase ID token.
    Requires 'Authorization: Bearer <token>' header.
    Returns: user_id (uid)
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Missing or invalid Authorization header. Expected 'Bearer <token>'"
        )
    
    token = authorization.split("Bearer ")[1]

    try:
        decoded_token = firebase_auth.verify_id_token(token)
        user_id = decoded_token['uid']
        email = decoded_token.get('email', 'unknown')
        
        # Auto-Init User Config if missing
        from core.firestore_client import init_user_if_needed
        init_user_if_needed(user_id, email)
        
        return user_id
        
    except ValueError as e:
        print(f"❌ Auth Error (Invalid Token Format): {e}")
        raise HTTPException(status_code=401, detail="Invalid token format")
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token expired")
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Token revoked")
    except Exception as e:
        print(f"❌ Auth Critical Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

# Alias for backward compatibility
verify_token = get_current_user
