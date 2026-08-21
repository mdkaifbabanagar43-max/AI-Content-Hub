
# SINGLE SOURCE OF TRUTH FOR SUBTITLE STYLES
# Used by Frontend (API) and Backend (FFmpeg)
# PREMIUM PROFESSIONAL EDITION - Scaled for 1080p (1920px Height)
# Reference Resolution: 1080x1920 (PlayResY = 1920)

SUBTITLE_PRESETS = {
    "bold_viral": {
        "id": "bold_viral",
        "label": "Bold Viral",
        "description": "Best for Reels & Shorts",
        "position": "center",
        "font_size": 70,  # ~4% of height (Standard Viral, reduced to prevent overflow)
        "font_weight": "Bold",
        "primary_color": "&H00FFFFFF",  # White
        "outline_color": "&H00000000",  # Black outline
        "back_color": "&H80000000",  # Semi-transparent black shadow
        "bold": True,
        "italic": False,
        "ass_alignment": 5,  # Center of screen
        "highlight_mode": "word",  # karaoke word-by-word
        "highlight_color": "&H0000FFFF",  # Yellow highlight
        "shadow": True,
        "outline_thickness": 5,  # Scaled up for 1920p
        "shadow_depth": 4,
        "font_name": "Arial Black",
        "letter_spacing": 3,
    },
    "podcast_clean": {
        "id": "podcast_clean",
        "label": "Podcast Clean",
        "description": "Professional & minimal",
        "position": "bottom",
        "font_size": 75,  # ~4.2% of height
        "font_weight": "Normal",
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "back_color": "&H60000000",
        "bold": False,
        "italic": False,
        "ass_alignment": 2,  # Bottom Center
        "highlight_mode": "sentence",  # no karaoke, full sentence
        "highlight_color": None,
        "shadow": True,
        "outline_thickness": 4,
        "shadow_depth": 3,
        "font_name": "Arial",
        "letter_spacing": 2,
    },
    "hook_focus": {
        "id": "hook_focus",
        "label": "Hook Focus",
        "description": "Boosts first 3 seconds",
        "position": "center",
        "font_size": 100,  # ~5.7% of height (HUGE)
        "font_weight": "Bold",
        "primary_color": "&H00FFFFFF", 
        "outline_color": "&H00FF00FF",  # Magenta/Pink outline for pop
        "back_color": "&H40000000",
        "bold": True,
        "italic": False,
        "ass_alignment": 5,  # Center
        "highlight_mode": "word",
        "highlight_color": "&H0000FF00",  # Bright Green highlight
        "shadow": True,
        "outline_thickness": 7,  # Extra thick
        "shadow_depth": 5,
        "font_name": "Impact",
        "letter_spacing": 4,
        "hook_boost": True  # Special flag for 120% scale
    },
    "minimal": {
        "id": "minimal",
        "label": "Minimal",
        "description": "Clean brand look",
        "position": "bottom",
        "font_size": 60,  # ~3.4% of height
        "font_weight": "Normal",
        "primary_color": "&H00F0F0F0",  # Slightly off-white
        "outline_color": "&H00000000",
        "back_color": "&H00000000",  # No shadow
        "bold": False,
        "italic": True,
        "ass_alignment": 2,
        "highlight_mode": "none",
        "highlight_color": None,
        "shadow": False,
        "outline_thickness": 2,
        "shadow_depth": 0,
        "font_name": "Arial",
        "letter_spacing": 1,
    },
    "premium_podcast": {
        "id": "premium_podcast",
        "label": "Premium Podcast",
        "description": "Ultra-professional interview style",
        "position": "bottom",
        "font_size": 80,  # ~4.7% of height
        "font_weight": "Bold",
        "primary_color": "&H00FFFFFF",  # White
        "outline_color": "&H00000000",  # Black
        "back_color": "&H90000000",  # Darker semi-transparent
        "bold": True,
        "italic": False,
        "ass_alignment": 2,  # Bottom center
        "highlight_mode": "word",  # Word karaoke for engagement
        "highlight_color": "&H0055FFFF",  # Gold/Amber highlight
        "shadow": True,
        "outline_thickness": 5,
        "shadow_depth": 4,
        "font_name": "Arial Black",
        "letter_spacing": 3,
    },
    "repurpose_pro": {
        "id": "repurpose_pro",
        "label": "Repurpose.io Pro",
        "description": "Bold yellow highlight with headline space",
        "position": "center",
        "font_size": 90,  # Big and bold
        "font_weight": "Bold",
        "primary_color": "&H00FFFFFF",  # White
        "outline_color": "&H00000000",  # Black
        "back_color": "&H90000000",  # Dark shadow
        "bold": True,
        "italic": False,
        "ass_alignment": 5,  # Center
        "highlight_mode": "word",
        "highlight_color": "&H0000FFFF",  # Yellow in BGR
        "shadow": True,
        "outline_thickness": 6,
        "shadow_depth": 5,
        "font_name": "Arial Black",
        "letter_spacing": 2,
    }
}
