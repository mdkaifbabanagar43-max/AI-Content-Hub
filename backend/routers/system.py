"""
System Router
Health check, user profile, and system configuration endpoints
"""
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.firestore_client import get_user_profile
from core.plan_limits import PLAN_LIMITS
from config import PLAN_CAPABILITIES, PRICING_TIERS, CREDIT_COSTS

router = APIRouter()

@router.get("/")
def health_check():
    """Health check endpoint."""
    return {"status": "AI Systems Online", "engine": "Smart Model Selection"}

@router.get("/api/me")
async def get_current_user_profile(user_id: str = Depends(get_current_user)):
    """
    Returns the user profile with injected capabilities based on plan.
    This acts as the single source of truth for the frontend permissions.
    """
    profile = get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    plan_id = profile.get('plan', 'starter')
    capabilities = PLAN_CAPABILITIES.get(plan_id, PLAN_CAPABILITIES.get('starter', {}))
    
    # Inject Capabilities
    profile['capabilities'] = capabilities
    
    return profile

@router.get("/system-config")
def get_system_config():
    """Exposes backend configuration for frontend sync."""
    try:
        return {
            "limits": PLAN_LIMITS if 'PLAN_LIMITS' in dir() else {},
            "pricing": PRICING_TIERS,
            "costs": CREDIT_COSTS
        }
    except Exception:
        return {"error": "Config not found"}
