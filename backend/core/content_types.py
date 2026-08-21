"""
Content Types Configuration
Defines content type rules for script generation and visual selection.
"""

CONTENT_TYPES = {
    "educational": {
        "label": "Educational",
        "tone": "informative",
        "script_structure": "hook → explain → example → recap",
        "pacing": "steady",
        "caption_style": "clean_readable",
        "visual_rules": {
            "prefer": ["expert_speaking", "demonstrations", "diagrams", "focused_person"],
            "avoid": ["party", "lifestyle", "abstract_motion"],
            "fallback": "calm person explaining concept"
        },
        "energy_curve": "medium"
    },
    "motivation": {
        "label": "Motivation",
        "tone": "inspirational",
        "script_structure": "challenge → struggle → breakthrough → triumph",
        "pacing": "building",
        "caption_style": "bold_impact",
        "visual_rules": {
            "prefer": ["human_triumph", "nature_epic", "athletic_achievement", "sunrise"],
            "avoid": ["office", "corporate", "static_objects"],
            "fallback": "person walking towards horizon"
        },
        "energy_curve": "low_to_high"
    },
    "history": {
        "label": "History",
        "tone": "narrative",
        "script_structure": "context → event → consequences → legacy",
        "pacing": "slow",
        "caption_style": "classic",
        "visual_rules": {
            "prefer": ["historical_footage", "old_photos", "monuments", "documents"],
            "avoid": ["modern_tech", "party", "lifestyle"],
            "fallback": "old building or historical monument"
        },
        "energy_curve": "low"
    },
    "story": {
        "label": "Story/Narrative",
        "tone": "dramatic",
        "script_structure": "setup → conflict → climax → resolution",
        "pacing": "varied",
        "caption_style": "cinematic",
        "visual_rules": {
            "prefer": ["emotional_faces", "journey", "conflict", "resolution"],
            "avoid": ["static_objects", "corporate", "graphs"],
            "fallback": "person in contemplation"
        },
        "energy_curve": "varied"
    },
    "explainer": {
        "label": "Explainer",
        "tone": "clear",
        "script_structure": "problem → solution → how_it_works → benefit",
        "pacing": "moderate",
        "caption_style": "clean_readable",
        "visual_rules": {
            "prefer": ["process_shots", "demonstrations", "before_after", "hands_working"],
            "avoid": ["abstract", "party", "unrelated_lifestyle"],
            "fallback": "person demonstrating concept"
        },
        "energy_curve": "medium"
    },
    "finance": {
        "label": "Finance/Crypto",
        "tone": "analytical",
        "script_structure": "hook → data → analysis → action",
        "pacing": "moderate",
        "caption_style": "professional",
        "visual_rules": {
            "prefer": ["charts", "trading_screens", "currency", "markets", "business_meeting"],
            "avoid": ["lifestyle", "party", "nature", "sports"],
            "fallback": "person analyzing data on screen"
        },
        "energy_curve": "medium",
        "domain_keywords": ["trading", "market", "cryptocurrency", "bitcoin", "stocks", "investment"]
    },
    "podcast": {
        "label": "Podcast-style",
        "tone": "conversational",
        "script_structure": "opener → point_1 → point_2 → takeaway",
        "pacing": "natural",
        "caption_style": "podcast_clean",
        "visual_rules": {
            "prefer": ["talking_head", "casual_conversation", "coffee_chat", "podcast_setup"],
            "avoid": ["intense_action", "abstract", "corporate"],
            "fallback": "person speaking casually"
        },
        "energy_curve": "natural"
    }
}

# Scene categories for visual matching
SCENE_CATEGORIES = {
    "entity": {
        "description": "Concrete objects, people, places",
        "visual_strategy": "domain_specific",
        "fallback": "neutral object related to topic",
        "examples": ["bitcoin", "person", "car", "building"]
    },
    "abstract": {
        "description": "Emotions, concepts, feelings",
        "visual_strategy": "human_emotion",
        "fallback": "calm human face closeup",
        "examples": ["anxiety", "success", "love", "fear"]
    },
    "event": {
        "description": "Actions, processes, changes",
        "visual_strategy": "metaphorical_motion",
        "fallback": "generic motion or charts",
        "examples": ["crash", "growth", "transformation", "journey"]
    }
}

# Category-safe fallbacks (NEVER random lifestyle)
CATEGORY_FALLBACKS = {
    "entity": [
        "focused person working",
        "professional at desk",
        "hands on keyboard"
    ],
    "abstract": [
        "calm face closeup",
        "person thinking peacefully",
        "thoughtful human expression"
    ],
    "event": [
        "time lapse city movement",
        "chart graph animation",
        "walking forward motion"
    ],
    "neutral": [
        "person walking slowly neutral",
        "calm human movement",
        "peaceful face closeup"
    ]
}

# Max retries for clip validation (fail fast)
MAX_CLIP_RETRIES = 2

def get_content_type_config(content_type: str) -> dict:
    """Get config for a content type, defaults to educational."""
    return CONTENT_TYPES.get(content_type, CONTENT_TYPES["educational"])

def get_category_fallback(category: str) -> str:
    """Get a safe fallback query for a category."""
    fallbacks = CATEGORY_FALLBACKS.get(category, CATEGORY_FALLBACKS["neutral"])
    import random
    return random.choice(fallbacks)

def get_visual_rules(content_type: str) -> dict:
    """Get visual preference rules for a content type."""
    config = get_content_type_config(content_type)
    return config.get("visual_rules", {})
