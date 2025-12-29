
CREDIT_COSTS = {
    'idea_studio_script': 5,        # 1 Script = 5 Credits (Cheap)
    'repurposer_per_minute': 10,    # 1 Min Video Input = 10 Credits (CPU Work)
    'dubbing_per_minute': 20,       # 1 Min Dubbing = 20 Credits (TTS is premium)
    'voice_clone_training': 500     # 1 Clone = 500 Credits (One-time fee)
}

PRICING_TIERS = {
    'starter': {
        'name': 'Starter',
        'price': 1900,  # $19
        'credits': 500, # ≈ 25 mins Dubbing OR 50 mins Repurposing
        'width': 720,
        'height': 1280,
        'limits': {
            'max_video_duration': 600,  # Max 10 min upload
            'storage_gb': 10,
            'watermark': True,
            'allow_4k': False
        }
    },
    'creator': {
        'name': 'Creator',
        'price': 4900,  # $49
        'credits': 2000, # ≈ 100 mins Dubbing OR 200 mins Repurposing
        'width': 1080,
        'height': 1920,
        'limits': {
            'max_video_duration': 1800, # Max 30 min upload
            'storage_gb': 50,
            'watermark': False,
            'allow_4k': True
        }
    },
    'agency': {
        'name': 'Agency',
        'price': 19900, # $199
        'credits': 10000, # Bulk usage
        'width': 1080,
        'height': 1920,
        'limits': {
            'max_video_duration': 3600, # Max 60 min upload
            'storage_gb': 200,
            'watermark': False,
            'allow_4k': True
        }
    },
    'free': {
        'name': 'Free',
        'price': 0,
        'credits': 15, # Trial
        'width': 720,
        'height': 1280,
        'limits': {
            'max_video_duration': 60, # 1 min
            'storage_gb': 1,
            'watermark': True,
            'allow_4k': False,
            'width': 720,  # QA Fix
            'height': 1280
        }
    }
}

# Feature Access Configuration - The Single Source of Truth
PLAN_FEATURES = {
    "starter": {
        "idea_studio": True,
        "script_generation": True,
        "repurposer_basic": True,
        "repurposer_smart_crop": False,
        "dubbing": True,
        "premium_voices": False,
        "watermark_free": False,
        "max_video_minutes": 10,
        "max_resolution": "720p",
        "priority_rendering": False,
        "bulk_upload": False,
        "concurrent_jobs": 1
    },

    "creator": {
        "idea_studio": True,
        "script_generation": True,
        "repurposer_basic": True,
        "repurposer_smart_crop": True,
        "dubbing": True,
        "premium_voices": True,
        "watermark_free": True,
        "max_video_minutes": 30,
        "max_resolution": "1080p",
        "priority_rendering": True,
        "bulk_upload": False,
        "concurrent_jobs": 2
    },

    "agency": {
        "idea_studio": True,
        "script_generation": True,
        "repurposer_basic": True,
        "repurposer_smart_crop": True,
        "dubbing": True,
        "premium_voices": True,
        "watermark_free": True,
        "max_video_minutes": 60,
        "max_resolution": "4k",
        "priority_rendering": True,
        "bulk_upload": True,
        "concurrent_jobs": 10
    }
}

# Alias for backward compatibility if needed, or refactor usages to PLAN_FEATURES
PLAN_CAPABILITIES = PLAN_FEATURES
QUALITY_TIERS = PRICING_TIERS
