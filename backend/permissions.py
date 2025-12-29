from fastapi import HTTPException
from config import PLAN_FEATURES
from firebase_utils import get_user_profile

def validate_feature_access(user_id: str, feature_key: str):
    """
    Validates if a user's plan allows a specific feature.
    Raises 403 if not allowed.
    Returns the user's plan configuration.
    """
    profile = get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    
    plan_id = profile.get('plan', 'starter')
    # Fallback to starter if plan invalid
    plan_config = PLAN_FEATURES.get(plan_id, PLAN_FEATURES['starter'])

    # 1. Feature Boolean Check
    if not plan_config.get(feature_key, False):
        raise HTTPException(
            status_code=403, 
            detail=f"Feature '{feature_key}' is locked on the {plan_id.title()} plan. Please upgrade to access."
        )

    return profile, plan_config

def validate_concurrency(user_id: str):
    """
    Checks if user has exceeded max concurrent jobs.
    """
    profile = get_user_profile(user_id)
    plan_id = profile.get('plan', 'starter')
    plan_config = PLAN_FEATURES.get(plan_id, PLAN_FEATURES['starter'])
    
    max_jobs = plan_config.get('concurrent_jobs', 1)
    # TODO: Real concurrency check would utilize a 'jobs' collection pending count.
    # For now, we assume frontend limits, but backend should ideally count active DB jobs.
    # Placeholder for 'active_jobs' field in profile.
    active_jobs = profile.get('active_jobs', 0)
    
    if active_jobs >= max_jobs:
         raise HTTPException(
            status_code=429, 
            detail=f"Concurrent job limit reached ({active_jobs}/{max_jobs}). Upgrade for more."
        )
    return True
