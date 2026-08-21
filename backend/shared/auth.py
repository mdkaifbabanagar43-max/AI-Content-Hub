# Shared Authentication Module
# Contains verify_token dependency for all routers

from fastapi import Header, HTTPException, Depends
import firebase_admin
from firebase_admin import auth as firebase_auth

# Import from firebase_utils (already initializes Firebase)
try:
    from firebase_utils import init_user_if_needed
except ImportError:
    def init_user_if_needed(user_id, email):
        print(f"⚠️ init_user_if_needed not available, skipping for {user_id}")

AUTH_OK = True

async def verify_token(authorization: str = Header(...)):
    """Verifies Firebase ID token. Requires 'Authorization: Bearer <token>' header."""
    if not AUTH_OK:
        return "mock_user_id"
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header. Expected 'Bearer <token>'")
    
    token = authorization.split("Bearer ")[1]
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        user_id = decoded_token['uid']
        email = decoded_token.get('email', 'unknown')
        
        # Auto-Init User Config if missing
        init_user_if_needed(user_id, email)
        
        return user_id
    except ValueError as e:
        print(f"❌ Auth Error (Invalid Token Format): {e}")
        raise HTTPException(status_code=401, detail="Invalid token format")
    except firebase_auth.ExpiredIdTokenError as e:
        print(f"❌ Auth Error (Expired): {e}")
        raise HTTPException(status_code=401, detail="Token expired")
    except firebase_auth.RevokedIdTokenError as e:
        print(f"❌ Auth Error (Revoked): {e}")
        raise HTTPException(status_code=401, detail="Token revoked")
    except Exception as e:
        print(f"❌ Auth Critical Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
