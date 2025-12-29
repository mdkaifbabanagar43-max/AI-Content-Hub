
import math

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

def generate_ass(segments, output_path, preset_config, platform="shorts", hook_boost=False):
    """
    Generates an .ass subtitle file from Whisper segments.
    
    segments: List of dicts checks for 'words' (karaoke) or 'text'.
    preset_config: Dict from SUBTITLE_PRESETS
    """
    
    # 1. EXTRACT PRESET CONFIG
    font_size = preset_config.get("font_size", 20)
    alignment = preset_config.get("ass_alignment", 2)
    primary_color = preset_config.get("primary_color", "&H00FFFFFF")
    outline_color = preset_config.get("outline_color", "&H00000000")
    back_color = preset_config.get("back_color", "&H80000000")
    highlight_color = preset_config.get("highlight_color", "&H0000FFFF")
    is_bold = -1 if preset_config.get("bold") else 0 # ASS: -1 is true, 0 is false
    
    # Platform safe margins
    # Shorts/Reels need huge bottom margin to avoid UI
    margin_v = 50
    if platform in ["shorts", "reels", "tiktok"]:
        if alignment == 2: # Bottom aligned
            margin_v = 150 # Move up above description/captions
    
    # Header
    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 384  ; Low res reference for relative sizing, ffmpeg scales it? Usually best to match video. 
               ; Actually 1080x1920 reference is better if we want pixel perfect.
               ; Let's assume 720p base (720x1280) for calculations.
PlayResY: 280
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},{primary_color},&H000000FF,{outline_color},{back_color},{is_bold},0,0,0,100,100,0,0,1,2,1,{alignment},10,10,{margin_v},1

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
            
            # STRATEGY: Group 2-3 words per screen to maximize readability on mobile.
            chunk_size = 3
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
                    ass_line += r"{\fscx120\fscy120}" # 120% scale
                    
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
                        # Join words
                        color = primary_color
                        if i == w_idx:
                            color = highlight_color if highlight_color else primary_color
                        
                        # Add space
                        if i > 0: formatted_text += " "
                        
                        # Word with color tag
                        # {\c&H...&}Word
                        formatted_text += f"{{\c{color}&}}{w['word'].strip()}"
                    
                    # Add end tag to reset? No, next tag overrides.
                    
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
