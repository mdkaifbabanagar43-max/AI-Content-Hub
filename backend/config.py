
CREDIT_COSTS = {
    'idea_studio_script': 5,        # 1 Script = 5 Credits (Cheap)
    'repurposer_per_minute': 10,    # 1 Min Video Input = 10 Credits (CPU Work)
    'dubbing_per_minute': 20,       # 1 Min Dubbing = 20 Credits (TTS is premium)
    'voice_clone_training': 500,    # 1 Clone = 500 Credits (One-time fee)
    'trend_cloner_base': 10,        # Trend Cloner base cost (TTS, Captions)
    'trend_cloner_veo_per_scene': 25 # Per-scene Veo generation cost
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

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

PORT = os.getenv("PORT", "8001")
LOCAL_BASE_URL = os.getenv("LOCAL_BASE_URL", f"http://localhost:{PORT}")

# Cloud Tasks Config
CLOUD_TASKS_PROJECT = os.getenv("CLOUD_TASKS_PROJECT", "shortcutai-backend")
CLOUD_TASKS_LOCATION = os.getenv("CLOUD_TASKS_LOCATION", "us-central1")
CLOUD_TASKS_QUEUE_NAME = os.getenv("CLOUD_TASKS_QUEUE_NAME", "generation-queue")
CLOUD_TASKS_MAX_CONCURRENT = int(os.getenv("CLOUD_TASKS_MAX_CONCURRENT", "1"))
SERVICE_ACCOUNT_EMAIL = os.getenv("SERVICE_ACCOUNT_EMAIL", "cloud-tasks-invoker@shortcutai-backend.iam.gserviceaccount.com")
WORKER_AUDIENCE = os.getenv("WORKER_AUDIENCE", "https://ai-video-backend-sfxkkeql7q-uc.a.run.app")
WORKER_URL = os.getenv("WORKER_URL", f"{WORKER_AUDIENCE}/projects/_internal/tasks/generate-production")

# Scene-level quality-retry ceiling. CanonicalGenerationEngine clamps every
# request to this ceiling regardless of blueprint QualityStrategy.max_retries,
# making the previous magic hard-cap explicit and ops-tunable via env
# (e.g. MAX_SCENE_QUALITY_RETRIES=2 for higher-fidelity renders at 2x Veo cost).
MAX_SCENE_QUALITY_RETRIES = int(os.getenv("MAX_SCENE_QUALITY_RETRIES", "1"))

# Narrative-originality ceiling (Jaccard composite, originality_validator.py).
# Generated blueprints exceeding this similarity vs the source CloneBlueprint
# are rejected as verbatim clones. P3/Q5: centralized alongside other gates.
ORIGINALITY_THRESHOLD = float(os.getenv("ORIGINALITY_THRESHOLD", "0.40"))

class ModelRoutingConfig:
    """Centralized Model Routing Configuration based on the Audit."""
    
    # 1. Source Analysis & Scriptwriting
    SOURCE_ANALYSIS = "gemini-3.1-flash-lite"
    TREND_ANALYSIS = "gemini-3.1-flash-lite"
    NORMAL_STORY = "gemini-3.1-flash-lite"
    COMPLEX_STORY = "us.anthropic.claude-sonnet-4-6"
    
    # 2. Video & Image Generation
    REFERENCE_IMAGE = "gemini-2.5-flash-image"
    
    VIDEO_DEFAULT = "veo-3.1-generate-001"
    
    # CANDIDATE for A/B testing
    VIDEO_FAST = "veo-3.1-fast-generate-001"
    
    VIDEO_PREMIUM = "veo-3.1-generate-001"
    
    QUALITY_REVIEW = "gemini-3.1-flash-lite"
    QUALITY_REVIEW_ESCALATE = "gemini-3.1-pro-preview"
    
    # 3. Voice & Audio
    VOICE_DEFAULT = "eleven_flash_v2_5"
    VOICE_PREMIUM = "eleven_v3"
    VOICE_LONGFORM = "eleven_multilingual_v2"
    LIPSYNC = "lipsync-2"


