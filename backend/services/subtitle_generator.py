
import math
from typing import List


# ─────────────────────────────────────────────────────────────
# Fix 3: Shared Whisper Word-Level Timestamp Extractor
# ─────────────────────────────────────────────────────────────

def get_word_level_timestamps(audio_path: str, language: str = "hi") -> List[dict]:
    """
    Shared function for extracting word-level timings from any audio/video file.
    Uses the globally loaded Whisper model with word_timestamps=True for
    sub-100ms caption sync accuracy.

    Used by:
    - Trend Cloner (add_viral_captions in viral_editor.py)
    - Idea Studio render pipeline

    Args:
        audio_path: Path to audio or video file (Whisper accepts both).
        language:   ISO 639-1 language code hint ("hi" for Hindi/Hinglish).

    Returns:
        List of dicts: [{"word": str, "start": float, "end": float}, ...]
        Also includes the raw Whisper result as the last element under key "_raw"
        for callers that need the full segments list.
    """
    try:
        from viral_editor import get_whisper_model
        WHISPER_MODEL = get_whisper_model()
    except ImportError:
        import whisper
        WHISPER_MODEL = whisper.load_model("base")

    print(f"[Subtitle Generator] Transcribing for word-level timestamps: {audio_path}")
    result = WHISPER_MODEL.transcribe(audio_path, word_timestamps=True, language=language)

    word_timings = []
    for segment in result.get("segments", []):
        for word_info in segment.get("words", []):
            word_timings.append({
                "word": word_info.get("word", "").strip(),
                "start": word_info.get("start", 0.0),
                "end": word_info.get("end", 0.0),
            })

    # Attach raw result for callers that need full segment data (e.g. generate_ass)
    word_timings.append({"_raw": result})

    print(f"[Subtitle Generator] Extracted {len(word_timings) - 1} word timings.")
    return word_timings


def hex_to_ass_color(hex_str, alpha="00"):
    """
    Converts normal hex #RRGGBB to ASS &H[alpha][blue][green][red]
    """
    if not hex_str: return "&H00FFFFFF"
    
    # ASS uses BGR order
    # Input #RRGGBB -> R=0:2, G=2:4, B=4:6
    # Output &H[Alpha][B][G][R]
    
    clean = hex_str.lstrip('#')
    if len(clean) == 6:
        r, g, b = clean[0:2], clean[2:4], clean[4:6]
        return f"&H{alpha}{b}{g}{r}"
    return "&H00FFFFFF"

def generate_ass(segments, output_path, preset_config, platform="shorts", hook_boost=False, brand_kit=None, custom_hook_text=None):
    """
    Generates an .ass subtitle file from Whisper segments.
    
    segments: List of dicts checks for 'words' (karaoke) or 'text'.
    preset_config: Dict from SUBTITLE_PRESETS
    brand_kit: Optional Dict containing custom branding overrides (font, colors)
    custom_hook_text: Optional string to display prominently for the first 3 seconds (A/B testing)
    """
    if brand_kit is None:
        brand_kit = {}
    
    # 1. EXTRACT PRESET CONFIG & APPLY BRAND KIT OVERRIDES
    font_size = preset_config.get("font_size", 24)
    font_name = "Noto Sans Devanagari"  # Enforce Hindi Supported Default
    alignment = preset_config.get("ass_alignment", 2)
    primary_color = brand_kit.get("primary_color") or preset_config.get("primary_color", "&H00FFFFFF")
    outline_color = brand_kit.get("outline_color") or preset_config.get("outline_color", "&H00000000")
    back_color = preset_config.get("back_color", "&H80000000")
    highlight_color = preset_config.get("highlight_color", "&H0000FFFF")
    is_bold = -1 if preset_config.get("bold") else 0 # ASS: -1 is true, 0 is false
    outline_thickness = preset_config.get("outline_thickness", 3)  # Thicker for premium
    shadow_depth = preset_config.get("shadow_depth", 2)
    letter_spacing = preset_config.get("letter_spacing", 2)  # Premium spacing
    
    # Platform safe margins
    margin_v = 80  # Increased for better visibility
    if platform in ["shorts", "reels", "tiktok"]:
        if alignment == 2: # Bottom aligned
            margin_v = 180 # Move up above description/captions
        elif alignment == 5: # Center aligned
            margin_v = 60  # Slightly above center for readability
    
    # Header - PREMIUM PROFESSIONAL STYLE
    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},&H000000FF,{outline_color},{back_color},{is_bold},0,0,0,100,100,{letter_spacing},0,1,{outline_thickness},{shadow_depth},{alignment},100,100,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def format_time(seconds):
        # H:MM:SS.cs
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
        
    if custom_hook_text:
        # Add a prominent title card for the first 3 seconds
        end_time_str = format_time(3.0)
        # Using a Top-Center alignment (Alignment 8) with a large font size and animation
        # {\fscx150\fscy150} for pop, plus primary color
        ass_content += f"Dialogue: 1,0:00:00.00,{end_time_str},Default,,0,0,800,,{{\\a8\\fscx130\\fscy130}}{custom_hook_text}\n"

    # 2. ITERATE SEGMENTS
    for seg in segments:
        words = seg.get('words', [])
        
        # Fallback if no word timestamps (some whisper models)
        if not words:
            # Just emit full line
            start = format_time(seg['start'])
            end = format_time(seg['end'])
            text = seg['text'].strip()
            ass_content += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n"
            continue
            
        # KARAOKE MODE vs SENTENCE MODE
        mode = preset_config.get("highlight_mode", "none")
        
        if mode == "word":
            # Word-by-word with highlight
            # We usually create ONE line per 'segment' (sentence) but use {\k} tags?
            # Or creating separate events? 
            # Real 'Karaoke' uses {\k<duration>} tags inside one Dialogue line.
            # But specific 'highlight word while others are white' is easier with separate events 
            # OR using {\1c&H...&} tags.
            
            # Simple approach: Create one event for the WHOLE sentence, 
            # but use {\k} tags which FFMPEG renders as a fill effect?
            # Actually standard ASS karaoke is mostly for singing. 
            # For "Shorts style", we often want the current word to be distinct color instantly.
            # Tag: {\c&H(Color)&}Word{\c&H(Original)&}
            
            # Let's split into small clusters (3-4 words) or single words?
            # User wants "Viral" -> Often 1-3 words MAX on screen at once.
            
            # STRATEGY: Group 1-2 words per screen to maximize readability on mobile.
            chunk_size = 2
            word_chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
            
            for chunk in word_chunks:
                chunk_start = chunk[0]['start']
                chunk_end = chunk[-1]['end']
                
                # Check for Hook Boost (first 3 seconds)
                is_hook = hook_boost and chunk_start < 3.0
                
                # Construct ASS text line with highlights
                ass_line = ""
                
                # Apply Hook Boost Zoom if active
                if is_hook:
                    ass_line += r"{\fscx125\fscy125}" # 125% scale (STRONGER HOOK)
                    
                prev_end = chunk_start
                
                # For each word in this visible chunk
                for idx, word in enumerate(chunk):
                    # We need to animate the color change EXACTLY when the word starts.
                    # But ASS "Dialogue" line is static text for duration.
                    # To animate color, we can use {\t} or just split events.
                    # Splitting events causes flickering sometimes.
                    # Karaoke tags {\k} are best but tricky.
                    
                    # SIMPLER VIRAL TRICK: 
                    # Just generate Multiple Dialogue Lines for the SAME timeframe? 
                    # Top layer: Highlighted word. Bottom layer: Dim words.
                    # No, that's complex.
                    
                    # SIMPLEST: ONE Dialogue Event per Word?
                    # "I" (0-0.5s), "am" (0.5-1.0s)... 
                    # Only showing 1 word at a time? 
                    # User asked for "Word-by-word highlight (yellow)" inside a "Center aligned" block?
                    # Usually means: Full sentence is visible, current word turns yellow.
                    
                    # Let's try: One Dialogue Event per CHUNK.
                    # Inside, we use \t (transforms) or just raw Karaoke \k tags.
                    # Actually, creating overlapping events is easier for exact timing.
                    
                    # Let's DO: "Active Word" approach (One word at a time styling).
                    # Actually, for "Bold Viral", usually we see 1-2 words on screen. Not full sentence.
                    # Let's stick to showing just the chunk (3 words) and highlighting current.
                    
                    # To achieve "Word Highlight" within a static block:
                    # We create multiple events for the same chunk timeframe.
                    # Event 1 (t=0 to t=1): "Word1 Word2 Word3" (Word1 Yellow)
                    # Event 2 (t=1 to t=2): "Word1 Word2 Word3" (Word2 Yellow) -- Wait, this implies text stays same.
                    
                    # Refined:
                    # "Dialogue: 0,Start,End,Default,,0,0,0,,{\c&HFFFF00&}Word1{\c&HFFFFFF&} Word2 Word3"
                    # "Dialogue: 0,End1,End2,Default,,0,0,0,,Word1 {\c&HFFFF00&}Word2{\c&HFFFFFF&} Word3"
                    
                    # Correct. We iterate words in the chunk.
                    pass 

                # ACTUALLY, simpler "Alex Hormozi" style is often just 1-3 words on screen at once.
                # Let's default to that as it's safest and most "Viral".
                # 1 chunk = 1 subtitle event.
                # Highlight logic: If we want "Karaoke", we need to split this chunk into mini-events.
                
                current_time = chunk_start
                # We need to hold the text on screen from chunk_start to chunk_end.
                # But we change formatting as we progress.
                
                for w_idx, active_word in enumerate(chunk):
                    w_start = active_word['start']
                    w_end = active_word['end']
                    
                    # Build text string
                    formatted_text = ""
                    if is_hook: formatted_text += r"{\fscx120\fscy120}"

                    for i, w in enumerate(chunk):
                        # Join words with space
                        if i > 0: formatted_text += " "
                        
                        if i == w_idx:
                            # Active word: Highlight color and scale up to 115%
                            color = highlight_color if highlight_color else primary_color
                            formatted_text += f"{{\\1c{color}\\fscx115\\fscy115}}{w['word'].strip()}"
                        else:
                            # Inactive word: Primary color and normal size
                            formatted_text += f"{{\\1c{primary_color}\\fscx100\\fscy100}}{w['word'].strip()}"
                    
                    # Event Duration: From this word's start to next word's start (or chunk end)
                    next_start = chunk[w_idx+1]['start'] if w_idx+1 < len(chunk) else chunk_end
                    
                    # Ensure continuity (avoid gaps)
                    if w_start < prev_end: w_start = prev_end # Clamp
                    
                    start_s = format_time(w_start)
                    end_s = format_time(next_start)
                    
                    ass_content += f"Dialogue: 0,{start_s},{end_s},Default,,0,0,0,,{formatted_text}\n"
                    prev_end = next_start

        else:
             # Sentence Clean Mode
             # Just standard lines
             start = format_time(seg['start'])
             end = format_time(seg['end'])
             text = seg['text'].strip()
             ass_content += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    return output_path
