
# SINGLE SOURCE OF TRUTH FOR SUBTITLE STYLES
# Used by Frontend (API) and Backend (FFmpeg)

SUBTITLE_PRESETS = {
    "bold_viral": {
        "id": "bold_viral",
        "label": "Bold Viral",
        "description": "Best for Reels & Shorts",
        "position": "center",
        "font_size": 24, # ASS font size (approx)
        "font_weight": "Bold",
        "primary_color": "&H00FFFFFF", # White in ASS hex (ABGR)
        "outline_color": "&H00000000", # Black
        "back_color": "&H80000000", # Semi-transparent black shadow
        "bold": True,
        "italic": False,
        "alignment": 2, # 2=Bottom Center (legacy), 5=Top Left? No, ASS align: 1=Left, 2=Center, 3=Right (Subtitles). 5=TopLeft... 10=CenterCenter for drawtext? 
        # ASS Alignment: 1=Left, 2=Center, 3=Right (Bottom). 5=TopLeft, 6=TopCenter...
        # We want Center (5 or 2 depending on vertical margin). simpler: Alignment=2 (Bottom Center) but we control MarginV.
        # Actually for "Bold Viral" user said "Center aligned". So Alignment=5 (Top-Left) is wrong. 
        # Alignment=10 (Center of screen)? ASS uses numpad layout keys. 5 is center-center.
        "ass_alignment": 5, 
        "highlight_mode": "word", # karaoke
        "highlight_color": "&H0000FFFF", # Yellow-ish (ABGR: 00=Alpha, 00=Blue, FF=Green, FF=Red) -> Yellow is R=255, G=255, B=0. So ABGR = 0000FFFF.
        "shadow": True
    },
    "podcast_clean": {
        "id": "podcast_clean",
        "label": "Podcast Clean",
        "description": "Professional & minimal",
        "position": "bottom",
        "font_size": 18,
        "font_weight": "Normal",
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "back_color": "&H60000000",
        "bold": False,
        "italic": False,
        "ass_alignment": 2, # Bottom Center
        "highlight_mode": "sentence", # no karaoke
        "highlight_color": None,
        "shadow": True
    },
    "hook_focus": {
        "id": "hook_focus",
        "label": "Hook Focus",
        "description": "Boosts first 3 seconds",
        "position": "center",
        "font_size": 26,
        "font_weight": "Bold",
        "primary_color": "&H00FFFFFF", 
        "outline_color": "&H000000FF", # Red outline? Or just Strong shadow.
        "back_color": "&H40000000",
        "bold": True,
        "italic": False,
        "ass_alignment": 5, # Center
        "highlight_mode": "word",
        "highlight_color": "&H000080FF", # Orange (ABGR: 00=A, 00=B, 80=G, FF=R) -> Order is A,B,G,R in ASS? No, &H[Alpha][Blue][Green][Red].
        # Orange: R=255(FF), G=128(80), B=0(00). -> &H000080FF
        "shadow": False,
        "hook_boost": True # Special flag
    },
    "minimal": {
        "id": "minimal",
        "label": "Minimal",
        "description": "Clean brand look",
        "position": "bottom",
        "font_size": 14,
        "font_weight": "Normal",
        "primary_color": "&H00E0E0E0", # Light grey
        "outline_color": "&H00000000",
        "back_color": "&H00000000", # No shadow
        "bold": False,
        "italic": True,
        "ass_alignment": 2,
        "highlight_mode": "none",
        "highlight_color": None,
        "shadow": False
    }
}
