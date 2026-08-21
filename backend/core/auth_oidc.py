from fastapi import Request, HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests
from config import SERVICE_ACCOUNT_EMAIL, WORKER_AUDIENCE

def verify_cloud_run_oidc_token(request: Request) -> str:
    """
    Verifies that the request contains a valid Google-signed OIDC ID token
    from the designated Cloud Tasks Service Account.
    Returns the email of the service account if valid.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
        
    token = auth_header.split(" ")[1]
    
    try:
        # Verify the OIDC token with Google's public keys
        # We strictly enforce the designated WORKER_AUDIENCE to prevent spoofing or misdelivery.
        request_adapter = requests.Request()
        id_info = id_token.verify_oauth2_token(token, request_adapter, audience=WORKER_AUDIENCE)
        
        email = id_info.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="OIDC token missing email claim")
            
        if email != SERVICE_ACCOUNT_EMAIL:
            raise HTTPException(
                status_code=403, 
                detail=f"Unauthorized service account: {email}. Expected {SERVICE_ACCOUNT_EMAIL}"
            )
            
        return email
        
    except ValueError as e:
        # Invalid token
        import logging
        logging.error(f"OIDC validation failed: {str(e)}. Expected audience: {WORKER_AUDIENCE}")
        raise HTTPException(status_code=401, detail=f"Invalid OIDC token: {str(e)}")
