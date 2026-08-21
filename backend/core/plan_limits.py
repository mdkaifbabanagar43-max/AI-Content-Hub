
PLAN_LIMITS = {
    "starter": {
        "max_res": 720,
        "watermark": True,
        "concurrent": 1,
        "max_duration": 60,  # seconds
        "allowed_presets": ["bold_viral", "podcast_clean"], # Locked presets
        "hook_boost": False
    },
    "creator": {
        "max_res": 1080,
        "watermark": False,
        "concurrent": 3,
        "max_duration": 300,
        "allowed_presets": ["all"],
        "hook_boost": True
    },
    "agency": {
        "max_res": 2160,
        "watermark": False,
        "concurrent": 10,
        "max_duration": 1200,
        "allowed_presets": ["all"],
        "hook_boost": True
    },
    "free": {
        "max_res": 480,
        "watermark": True,
        "concurrent": 1,
        "max_duration": 30, # Preview only
        "allow_export": True,
        "allowed_presets": ["bold_viral"],
        "hook_boost": False
    }
}

DEFAULT_PLAN = "free"

def get_plan_limits(plan_name: str):
    return PLAN_LIMITS.get(plan_name, PLAN_LIMITS[DEFAULT_PLAN])

def enforce_rendering_params(plan_name: str, requested_height: int):
    """
    Returns (safe_height, needs_watermark)
    """
    limits = get_plan_limits(plan_name)
    max_res = limits["max_res"]
    
    # Force downgrade if requested > max
    safe_height = min(requested_height, max_res)
    
    # Force watermark if plan requires it
    needs_watermark = limits["watermark"]
    
    return safe_height, needs_watermark
