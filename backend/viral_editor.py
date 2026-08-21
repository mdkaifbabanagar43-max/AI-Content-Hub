import os
import random
import requests
import concurrent.futures
import time
import re
import gc
import numpy as np

from core.subtitle_presets import SUBTITLE_PRESETS
from services.subtitle_generator import generate_ass
from core.plan_limits import get_plan_limits

# LAZY LOADING GLOBALS

WHISPER_MODEL = None



def get_whisper_model():

    global WHISPER_MODEL

    import whisper

    if WHISPER_MODEL is None:

        print("⏳ Loading Whisper Model (Lazy)...")

        # QA UPGRADE: Use 'small' model (vs 'base') to fix hallucinations

        # 'small' is approx 2x slower but much better at English grammar/context

        WHISPER_MODEL = whisper.load_model("small")

        print("✅ Whisper Model Loaded (Small).")

    return WHISPER_MODEL



def get_moviepy():

    print("⏳ Importing MoviePy (Lazy)...")

    from moviepy.editor import (

        VideoFileClip, AudioFileClip, concatenate_videoclips, 

        CompositeVideoClip, TextClip, ColorClip, vfx, CompositeAudioClip

    )

    from moviepy.video.fx.all import resize, crop, fadein, fadeout

    from moviepy.editor import clips_array

    from moviepy.config import change_settings

    import platform

    

    # Configuration

    if platform.system() == "Windows":

        change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"})

    else:

        # Linux / Cloud Run (ImageMagick installed via Dockerfile)

        # Default usually works, or explicitly strict

        # change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"}) 

        pass 

    

    return {

        "VideoFileClip": VideoFileClip,

        "AudioFileClip": AudioFileClip,

        "concatenate_videoclips": concatenate_videoclips,

        "CompositeVideoClip": CompositeVideoClip,

        "TextClip": TextClip,

        "ColorClip": ColorClip,

        "vfx": vfx,

        "CompositeAudioClip": CompositeAudioClip,

        "resize": resize,

        "crop": crop,

        "clips_array": clips_array

    }



# --- VISUAL TRANSLATION LAYER (DP Layer) ---
# Converts abstract script sentences to concrete, searchable stock footage queries

def generate_visual_search_term(sentence_text: str, main_topic: str = None) -> str:
    """
    Uses LLM to translate abstract script sentences into concrete visual queries.
    
    Example:
    - Input: "It feels like I'm drowning in debt"
    - Output: "man stressed looking at bills papers"
    
    This prevents generic/irrelevant stock footage (e.g., "drowning" → swimmer)
    """
    try:
        from services.ai_service import generate_text
        
        # Build the Director of Photography prompt
        topic_hint = f"The overall topic is about: {main_topic}." if main_topic else ""
        
        prompt = f"""You are a Director of Photography creating visual search queries for stock footage.

TASK: Convert this script sentence into a CONCRETE, PHYSICAL search query for Pexels.

SENTENCE: "{sentence_text}"
{topic_hint}

RULES (STRICT):
1. Output ONLY the search query (3-6 words max)
2. IGNORE abstract words: "mistake", "future", "thinking", "journey", "success"
3. CONVERT abstractions to PHYSICAL ACTIONS:
   - "I was confused" → "person scratching head computer"
   - "Drowning in debt" → "stressed man looking bills"
   - "Feeling overwhelmed" → "woman holding head papers desk"
   - "Bitcoin is crashing" → "red crypto chart screen falling"
   - "Making money online" → "person smiling laptop money"
4. If sentence mentions specific nouns (Bitcoin, Tesla, Gold, iPhone), INCLUDE them
5. PREFER: Human faces, physical actions, real objects
6. AVOID: Abstract backgrounds, generic landscapes, animations

OUTPUT: Only the search query, nothing else."""

        response_text = generate_text(prompt, temperature=0.2)
        translated_query = response_text.strip().strip('"').strip("'")
        
        # Validation: Ensure we got a reasonable query
        if len(translated_query) < 3 or len(translated_query) > 100:
            print(f"⚠️ Visual Translation returned invalid query, using fallback")
            return sentence_text[:50] if sentence_text else "person working"
        
        print(f"🎬 Visual Translation: '{sentence_text[:40]}...' → '{translated_query}'")
        return translated_query
        
    except Exception as e:
        print(f"⚠️ Visual Translation failed: {e}. Using raw sentence.")
        # Fallback: Extract nouns from sentence (simple heuristic)
        words = sentence_text.split()[:5] if sentence_text else ["person", "working"]
        return " ".join(words)


PEXELS_API_KEY = "vYq0ChyYQyeAFemzLivZTmfOnpLcLOreQ5zl9mxtGa2u3TcXngZtpDLz"



# --- 2. PARALLEL DOWNLOAD ENGINE ---



def download_clip(term, output_dir, orientation="portrait", used_links=None, min_width=720, main_topic=None, mood="informative"):

    """

    Searches Pexels and finds file closest to 'min_width' but >= 'min_width' if possible.

    Supports 4K (3840), 1080p (1920), 720p (720).

    """

    log_start = time.time()

    if used_links is None:

        used_links = set()



    try:

        # A. SEARCH

        headers = {"Authorization": PEXELS_API_KEY}

        

        # QA UPGRADE: Force Realism & Context Anchoring

        # STEP 0: VISUAL TRANSLATION (DP Layer)
        # Convert abstract terms to concrete, searchable visuals using LLM
        # e.g., "drowning in debt" → "stressed man looking at bills"
        translated_term = term
        try:
            # Only translate if term looks like a sentence (has spaces and is long enough)
            if len(term) > 15 and ' ' in term:
                translated_term = generate_visual_search_term(term, main_topic)
            else:
                # Short terms like "Bitcoin" don't need translation
                translated_term = term
        except Exception as e:
            print(f"⚠️ Visual Translation skipped: {e}")
            translated_term = term

        # 1. Context Anchoring: If term is vague, prepend main topic
        final_query = translated_term

        if main_topic and len(main_topic) > 2:
             # Heuristic: If main_topic words are not in term, prepend them
             if main_topic.lower() not in translated_term.lower():
                 final_query = f"{main_topic} {translated_term}"

        

        # 2. STYLE PRESETS (Visual Consistency)
        # Default to Cinematic for professional look
        style_suffix = "cinematic 4k moody lighting"
        
        if mood:
             m = mood.lower()
             # === EXPLICIT STYLE PRESETS ===
             if 'cinematic' in m:
                 style_suffix = "4k cinematic lighting moody dark atmosphere"
             elif 'bright' in m or 'corporate' in m or 'happy' in m:
                 style_suffix = "bright corporate happy sunlight clean"
             elif 'tech' in m or 'future' in m or 'cyber' in m:
                 style_suffix = "futuristic neon cyber dark background tech"
             # === EMOTION-BASED FALLBACKS ===
             elif 'scary' in m or 'horror' in m:
                 style_suffix = "dark gloomy horror cinematic shadows"
             elif 'fast' in m or 'action' in m or 'urgent' in m:
                 style_suffix = "fast action motion blur dynamic"
             elif 'sad' in m or 'emotional' in m:
                 style_suffix = "sad slow rain emotional cinematic"
             elif 'calm' in m or 'peaceful' in m:
                 style_suffix = "calm peaceful serene natural light"
             elif 'fun' in m or 'energetic' in m:
                 style_suffix = "bright colorful energetic fun"
             elif 'informative' in m or 'educational' in m:
                 style_suffix = "clean professional 4k educational"

        query_term = f"{final_query} {style_suffix}"


        

        # Increase per_page to find more candidates (avoid getting stuck on a single 4k-only result)

        # Fetching 15 results to ensure variety if we need multiple clips for same term

        url = f"https://api.pexels.com/videos/search?query={query_term}&per_page=15&orientation={orientation}"

        r = requests.get(url, headers=headers, timeout=5)

        

        if r.status_code != 200:

             print(f"❌ Pexels API Error ({r.status_code}): {r.text}")

             return None

        

        download_url = None

        if r.status_code == 200:

            data = r.json()

            if data.get('videos'):

                candidates = []

                # target_width = 720 if orientation == "portrait" else 1280 # OLD



                for video in data['videos']:

                    # Check if this video ID or link has already been used

                    # Use video ID for robustness

                    vid_id = video.get('id')

                    if vid_id in used_links:

                        continue



                    # Find valid files within this video object

                    # valid_files = [] # OLD

                    # for vfile in video['video_files']: # OLD

                    #     w = vfile.get('width', 0) # OLD

                    #     # We prefer <= 1080p # OLD

                    #     valid_files.append(vfile) # OLD



                    # if not valid_files: continue # OLD



                    # Pick best file for this video

                    # Strategy: STRICT RAM SAFETY - Max 1080p, Target 720p # OLD

                    

                    # 1. Filter out anything larger than 1080p (Save RAM) # OLD

                    # safe_files = [v for v in valid_files if v.get('width', 9999) <= 1920 and v.get('height', 9999) <= 1920] # OLD

                    

                    # if not safe_files: # OLD

                    #     continue # Skip this video if no safe files # OLD

                        

                    # 2. Find closest to Target # OLD

                    # Target: 720w for Portrait, 1280w (720h) for Landscape # OLD

                    # target_dim = 720 if orientation == "portrait" else 1280 # OLD

                    # key_dim = 'width' # Use width as primary comparator # OLD

                    

                    # Sort by proximity to target_dim # OLD

                    # safe_files.sort(key=lambda x: abs(x.get(key_dim, 0) - target_dim)) # OLD

                    

                    # selected_file = safe_files[0] # OLD



                    # Filter and Sort files for this video

                    # We want the smallest file that is >= min_width

                    # If none >= min_width, take the largest available.

                    

                    video_files = video.get('video_files', [])

                    

                    # 1. Filter out known bad formats (m3u8, hls) if any, usually Pexels sends mp4

                    

                    # 2. Sort by width

                    video_files.sort(key=lambda x: x.get('width', 0))

                    

                    best_file = None

                    

                    # Strategy: Linear scan for first file >= min_width

                    for vfile in video_files:

                        if vfile.get('width', 0) >= min_width:

                            best_file = vfile

                            break

                    

                    # Fallback: If no file is >= min_width (e.g. asking for 4K but only HD available), take largest

                    if not best_file and video_files:

                        best_file = video_files[-1]

                        

                    if best_file:

                        candidates.append({

                            'link': best_file['link'],

                            'id': vid_id,

                            'width': best_file.get('width'),

                            'height': best_file.get('height')

                        })



                # Select from candidates

                if candidates:

                    # Pick random from top 3 to ensure variety

                    choice = random.choice(candidates[:3]) 

                    download_url = choice['link']

                    # Mark as used (Thread-safe concern? used_links is passed via closure in ThreadPool logic usually needs lock, 

                    # but for simple sets in Python generic threads it might be racy. 

                    # Ideally we lock. For now, we accept minor race condition risk for speed.)

                    used_links.add(choice['id'])

                    

                    print(f"   -> Found Clip for '{term}': {choice['width']}x{choice['height']} (ID: {choice['id']})")

                else:

                     print(f"⚠️ Pexels found videos for '{term}' but all were previously used or invalid.")



        

        if not download_url:

            print(f"⚠️ No suitable (new) video found for: {term}")

            return None



        # C. DOWNLOAD

        safe_term = "".join([c for c in term if c.isalnum()])[:10]

        filename = f"{safe_term}_{random.randint(1000,9999)}.mp4"

        d_path = os.path.join(output_dir, filename)

        

        print(f"[LOG] Starting Download '{term}' -> {filename}")

        r_vid = requests.get(download_url, stream=True, timeout=20)

        if r_vid.status_code == 200:

            with open(d_path, 'wb') as f:

                for chunk in r_vid.iter_content(chunk_size=16384): # Bigger chunks for speed

                    f.write(chunk)

            print(f"[LOG] Downloaded: {filename} ({time.time() - log_start:.2f}s)")

            return d_path

            

    except Exception as e:

        print(f"❌ Error downloading '{term}': {e}")

    

    return None



def batch_download_videos(terms, output_dir=None, orientation="portrait", main_topic=None, mood="informative", min_width=720, min_height=1280):
    if output_dir is None:
        from config import TEMP_DIR
        output_dir = os.path.join(TEMP_DIR, "temp_clips")

    """

    Executes parallel downloads for all terms.

    """

    if not os.path.exists(output_dir):

        os.makedirs(output_dir)

        

    print(f"[LOG] Starting Batch Download: {time.time()} (Min Width: {min_width})")

    t_start = time.time()

    used_links = set()

    downloaded_paths = []

    

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all tasks and keep a reference to the future mapped to its index
        future_to_index = {executor.submit(download_clip, terms[i], output_dir, orientation, used_links, min_width, main_topic, mood): i for i in range(len(terms))}
        
        # Initialize results list with None
        results = [None] * len(terms)
        
        for future in concurrent.futures.as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                path = future.result()
                if path:
                    results[idx] = path
                else:
                    print(f"⚠️ Warning: No clip found for '{terms[idx]}'")
            except Exception as e:
                print(f"❌ Error downloading '{terms[idx]}': {e}")

    # Remove Nones if we want to filter failures, OR ensure we handle Nones downstream.
    # To keep scene alignment (Index 0 -> Scene 0), we MUST separate failures or handle them.
    # Current generate_turbo_video logic expects a list of paths.
    # If we filter Nones, indices shift.
    # BETTER FIX: If a download fails, we should arguably duplicate a previous clip or allow None and handle fallback there.
    # For now, let's filter Nones but we acknowledge this might shift sync if not handled in editor.
    # Ideally, generate_turbo_video should use the same 'terms' list to iterate.
    
    # Let's filter for now to avoid crashes, but eventually we want 1:1 mapping.
    downloaded_paths = [r for r in results if r is not None]
    
    return downloaded_paths




# --- INTELLIGENT FACE TRACKING (MediaPipe - Free) ---
import mediapipe as mp

import cv2

class SmartCropEngine:
    def __init__(self):
        print("[SmartCropEngine] Initializing MediaPipe FaceTracker...")
        self.is_broken = False
        self.mp_face_detection = None
        self.detector = None
        
        try:
            import mediapipe as mp
            if hasattr(mp, "solutions") and hasattr(mp.solutions, "face_detection"):
                self.mp_face_detection = mp.solutions.face_detection
                # model_selection=1 for full-range (further away), 0 for close-up
                self.detector = self.mp_face_detection.FaceDetection(min_detection_confidence=0.5, model_selection=1)
                print("[SmartCropEngine] MediaPipe initialized successfully.")
            else:
                self.is_broken = True
                print("[SmartCropEngine] MediaPipe face_detection missing.")
        except Exception as e:
            print(f"[SmartCropEngine] MediaPipe initialization failed: {e}")
            self.is_broken = True

        self.cache = {}

    def detect_faces(self, frame_pil):
        """
        Detects faces using MediaPipe.
        Returns list of padded (x, y, w, h) absolute pixels.
        Padding: 150% vertical, 50% horizontal.
        """
        if self.is_broken or self.detector is None:
            return []

        w_img, h_img = frame_pil.size
        import numpy as np
        frame_np = np.array(frame_pil)
        
        try:
            results = self.detector.process(frame_np)
            faces = []
            if results.detections:
                for detection in results.detections:
                    bboxC = detection.location_data.relative_bounding_box
                    # Raw MediaPipe bounds
                    raw_x = bboxC.xmin * w_img
                    raw_y = bboxC.ymin * h_img
                    raw_w = bboxC.width * w_img
                    raw_h = bboxC.height * h_img
                    
                    # Return raw MediaPipe face bounding box. We will handle layout in get_crop
                    x = max(0, int(raw_x))
                    y = max(0, int(raw_y))
                    w = int(raw_w)
                    h = int(raw_h)
                    
                    if x + w > w_img: w = w_img - x
                    if y + h > h_img: h = h_img - y
                    
                    faces.append((x, y, w, h))
            return faces
        except Exception as e:
            print(f"⚠️ MediaPipe Detection Error: {e}")
            return []

    def analyze_clip(self, clip, interval=1.5):
        """
        Analyzes the clip at intervals and builds a trajectory.
        Stores cx, cy, w, h for up to 2 faces and determines layout.
        """
        print(f"Analyzing {clip.duration}s clip for faces (Interval: {interval}s)...")
        current_t = 0
        timestamps = []
        configs = [] 
        from PIL import Image
        import numpy as np
        
        while current_t < clip.duration:
            try:
                frame_np = clip.get_frame(current_t)
                frame_pil = Image.fromarray(np.array(frame_np, dtype=np.uint8))
                faces = self.detect_faces(frame_pil)
                
                # Default Config
                cfg = {'mode': 0, 'layout': 'unknown'}

                if len(faces) == 1:
                    # Single Face Mode (Mode A: Smart Solo)
                    f = faces[0]
                    cfg = {
                        'mode': 1, 
                        'f1': {'cx': f[0]+f[2]/2, 'cy': f[1]+f[3]/2, 'w': f[2], 'h': f[3]},
                        'layout': 'single'
                    }
                elif len(faces) >= 2:
                    # Two Face Mode - Determine Layout
                    faces.sort(key=lambda f: f[2]*f[3], reverse=True)
                    top_two = faces[:2]
                    
                    f_x = sorted(top_two, key=lambda f: f[0])
                    f_y = sorted(top_two, key=lambda f: f[1])
                    
                    dist_x = f_x[1][0] - f_x[0][0]
                    dist_y = f_y[1][1] - f_y[0][1]
                    
                    # Robust Layout Detection
                    if dist_y > dist_x * 1.2: 
                        layout = 'vertical'
                        f1 = f_y[0]  # Top
                        f2 = f_y[1]  # Bottom
                    else:
                        layout = 'horizontal'
                        f1 = f_x[0]  # Left
                        f2 = f_x[1]  # Right

                    cfg = {
                        'mode': 2,
                        'layout': layout,
                        'f1': {'cx': f1[0]+f1[2]/2, 'cy': f1[1]+f1[3]/2, 'w': f1[2], 'h': f1[3]},
                        'f2': {'cx': f2[0]+f2[2]/2, 'cy': f2[1]+f2[3]/2, 'w': f2[2], 'h': f2[3]}
                    }
                
                configs.append(cfg)
                timestamps.append(current_t)
            except Exception as e:
                print(f"Frame analysis failed at {current_t}: {e}")
            
            current_t += interval
            
        self.timestamps = timestamps
        self.configs = configs
        print(f"Face Analysis Complete. {len(configs)} keyframes.")

    def get_params(self, t):
        """Interpolates params for time t with Cinematic Lerp smoothing."""
        if not hasattr(self, 'timestamps') or not self.timestamps:
            return None
            
        times = self.timestamps
        if t <= times[0]: return self.configs[0]
        if t >= times[-1]: return self.configs[-1]
        
        for i in range(len(times)-1):
            if times[i] <= t <= times[i+1]:
                t1, t2 = times[i], times[i+1]
                c1, c2 = self.configs[i], self.configs[i+1]
                
                # Check for Mode Cut (if structure changes, don't interpolate, just cut)
                if c1['mode'] != c2['mode'] or c1.get('layout') != c2.get('layout'):
                     return c1 if (t - t1) < (t2 - t) else c2
                
                # Cinematic Smooth Lerp (Ease In-Out)
                alpha = (t - t1) / (t2 - t1)
                smooth_alpha = alpha * alpha * (3 - 2 * alpha)
                
                def lerp(k, subdict):
                    if subdict not in c1 or subdict not in c2: return 0
                    v1 = c1[subdict].get(k, 0)
                    v2 = c2[subdict].get(k, 0)
                    return v1 + smooth_alpha * (v2 - v1)

                new_cfg = c1.copy()
                if 'f1' in c1:
                    new_cfg['f1'] = {k: lerp(k, 'f1') for k in ['cx', 'cy', 'w', 'h']}
                if 'f2' in c1:
                    new_cfg['f2'] = {k: lerp(k, 'f2') for k in ['cx', 'cy', 'w', 'h']}
                    
                return new_cfg
                
        return self.configs[-1]


def apply_smart_crop(clip, mode="smart_crop", target_width=1080, target_height=1920):
    if mode in ["podcast_stack", "mode_a", "mode_b", "mode_c", "smart_crop"]:
        return process_podcast_stack(clip, target_width, target_height, requested_mode=mode)
    elif mode == "dynamic_cut":
        return process_dynamic_cut(clip, target_width, target_height)
    elif mode == "content_fit":
        return process_content_fit(clip, target_width, target_height)
    elif mode == "viral_split":
        return process_viral_split(clip, target_width, target_height)
    else:
        return process_podcast_stack(clip, target_width, target_height, requested_mode=mode)

def process_podcast_stack(clip, target_width=720, target_height=1280, requested_mode="auto"):

    """

    AI-Powered Stack using Smart Zoom (Face-Relative Cropping).

    """

    mp = get_moviepy()

    VideoClip = mp["VideoClip"] if "VideoClip" in mp else None 

    # Use standard PIL Image from global import

    

    print(f"[LOG] Processing AI Podcast Stack. Input: {clip.w}x{clip.h} (Requested Mode: {requested_mode})")

    

    # 1. Analyze
    tracker = SmartCropEngine()
    tracker.analyze_clip(clip, interval=1.5) 

    

    # 2. Generator

    def frame_generator(t):

        params = tracker.get_params(t)

        frame = clip.get_frame(t)

        h, w, _ = frame.shape

        

        # --- Helper: Smart Zoom Crop ---

        def get_crop(face_data, slot_w, slot_h, restrict_h=False):

            cx, cy = face_data['cx'], face_data['cy']

            fw, fh = face_data.get('w', w/4), face_data.get('h', h/4)

            

            # Target Zoom: Face height should be ~40-50% of the slot height ideally

            # Zoom out slightly more to capture shoulders (3.5x face height)
            ideal_crop_h = fh * 3.5

            # Enforce Aspect Ratio of the Slot
            slot_ratio = slot_w / slot_h 

            # Calculate implied Width from Ideal Height
            crop_w = ideal_crop_h * slot_ratio
            crop_h = ideal_crop_h

            # --- CONSTRAINTS ---

            # 1. Don't exceed Source Dimensions
            if crop_w > w:
                crop_w = w
                crop_h = w / slot_ratio
            if crop_h > h:
                crop_h = h
                crop_w = h * slot_ratio
                
            # 2. Overlap Safety (Vertical Layouts)
            # If Vertical, ensure we don't bleed into the other half too much
            if restrict_h:
                max_safe_h = h / 2.1 # Leave a small gap
                if crop_h > max_safe_h:
                    print(f"⚠️ Clamping Crop Height for Overlap Safety: {crop_h} -> {max_safe_h}")
                    crop_h = max_safe_h
                    crop_w = crop_h * slot_ratio

            # Center on Face horizontally
            x1 = cx - crop_w/2
            # Put face in the upper third vertically (rule of thirds) instead of dead center
            y1 = cy - crop_h * 0.33
            
            # Clamp to Image Bounds
            x1 = max(0, min(w - crop_w, x1))
            y1 = max(0, min(h - crop_h, y1))

            

            # Extract

            region = frame[int(y1):int(y1+crop_h), int(x1):int(x1+crop_w)]

            

            # Resize to Slot

            img = Image.fromarray(region)

            return np.array(img.resize((slot_w, slot_h), Image.LANCZOS))



        # --- Logic ---

        mode = params.get('mode', 0) if params else 0

        layout = params.get('layout', 'unknown') if params else 'unknown'

        if mode == 2:
            # Determine output layout
            if requested_mode in ["podcast_stack", "mode_b", "stack", "vertical"]:
                is_vertical = True
            elif requested_mode in ["side_by_side", "mode_c", "horizontal"]:
                is_vertical = False
            else:
                # If auto, map horizontal input -> vertical output stack, and vertical input -> horizontal output stack
                is_vertical = (layout == 'horizontal')

            if is_vertical:
                # Mode B: PODCAST STACK MODE - Stack vertically (upper/lower)
                slot_w = target_width
                slot_h = target_height // 2 

                top_img = get_crop(params['f1'], slot_w, slot_h, restrict_h=True)
                bottom_img = get_crop(params['f2'], slot_w, slot_h, restrict_h=True)

                def safety_zoom(img_arr, scale=1.05):
                    h_in, w_in = img_arr.shape[:2]
                    new_w, new_h = int(w_in * scale), int(h_in * scale)
                    zoomed = Image.fromarray(img_arr).resize((new_w, new_h), Image.LANCZOS)
                    left = (new_w - w_in) // 2
                    top = (new_h - h_in) // 2
                    return np.array(zoomed.crop((left, top, left + w_in, top + h_in)))

                top_img = safety_zoom(top_img)
                bottom_img = safety_zoom(bottom_img)

                return np.vstack((top_img, bottom_img))
            
            else:
                # Mode C: SIDE-BY-SIDE MODE - Split canvas vertically (left/right)
                slot_w = target_width // 2
                slot_h = target_height 

                # f1 is left face, f2 is right face (sorted in analyze_clip)
                left_img = get_crop(params['f1'], slot_w, slot_h, restrict_h=False)
                right_img = get_crop(params['f2'], slot_w, slot_h, restrict_h=False)

                def safety_zoom(img_arr, scale=1.05):
                    h_in, w_in = img_arr.shape[:2]
                    new_w, new_h = int(w_in * scale), int(h_in * scale)
                    zoomed = Image.fromarray(img_arr).resize((new_w, new_h), Image.LANCZOS)
                    left = (new_w - w_in) // 2
                    top = (new_h - h_in) // 2
                    return np.array(zoomed.crop((left, top, left + w_in, top + h_in)))

                left_img = safety_zoom(left_img)
                right_img = safety_zoom(right_img)

                return np.hstack((left_img, right_img))


        elif mode == 1:
            # Single Face - Smart crop around the detected face
            return get_crop(params['f1'], target_width, target_height)

        else:
            # Fallback: Center Crop (no faces detected)
            center_x = w // 2
            x1 = max(0, center_x - target_width//2)
            crop = frame[:, int(x1):int(x1+target_width)]

            img = Image.fromarray(crop).resize((target_width, target_height), Image.LANCZOS)

            return np.array(img)



    # 3. Create Clip

    # from moviepy.editor import VideoClip # Removed to use lazy map

    # Note: process_podcast_stack takes a 'clip' object. 

    # We assume 'clip' is a MoviePy object. 

    # If we need VideoClip constructor:

    from moviepy.editor import VideoClip

    final_clip = VideoClip(make_frame=frame_generator, duration=clip.duration)

    final_clip = final_clip.set_audio(clip.audio)

    

    if hasattr(clip, 'fps') and clip.fps:

        final_clip.fps = clip.fps

    else:

        final_clip.fps = 24

    

    return final_clip





def process_dynamic_cut(clip, target_width=720, target_height=1280):
    """
    OpusClip Style Dynamic Cut: Auto-punches between Stack, Face 1, and Face 2
    to create a highly engaging, fast-paced edit.
    """
    from moviepy.editor import VideoClip
    from PIL import Image
    
    print(f"[LOG] Processing AI Dynamic Cut (Auto-Puncher). Input: {clip.w}x{clip.h}")
    
    # 1. Analyze
    tracker = SmartCropEngine()
    tracker.analyze_clip(clip, interval=1.0) 

    def frame_generator(t):
        params = tracker.get_params(t)
        frame = clip.get_frame(t)
        h, w, _ = frame.shape
        
        mode = params.get('mode', 0) if params else 0
        
        # --- Helper: Extract Region ---
        def extract_face(face_data, slot_w, slot_h, restrict_h=False):
            cx, cy = face_data['cx'], face_data['cy']
            fw, fh = face_data.get('w', w/4), face_data.get('h', h/4)
            
            ideal_crop_h = fh * 3.5
            slot_ratio = slot_w / slot_h 
            crop_w = ideal_crop_h * slot_ratio
            crop_h = ideal_crop_h

            if crop_w > w:
                crop_w = w
                crop_h = w / slot_ratio
            if crop_h > h:
                crop_h = h
                crop_w = h * slot_ratio
                
            if restrict_h:
                max_safe_h = h / 2.1
                if crop_h > max_safe_h:
                    crop_h = max_safe_h
                    crop_w = crop_h * slot_ratio

            x1 = cx - crop_w/2
            y1 = cy - crop_h * 0.33
            
            x1 = max(0, min(w - crop_w, x1))
            y1 = max(0, min(h - crop_h, y1))

            region = frame[int(y1):int(y1+crop_h), int(x1):int(x1+crop_w)]
            img = Image.fromarray(np.array(region, dtype=np.uint8))
            return np.array(img.resize((slot_w, slot_h), Image.LANCZOS))
            
        # --- Auto Puncher Logic ---
        # Cycle: 0-4s (Stack), 4-7s (Solo 1), 7-10s (Solo 2)
        cycle_duration = 10.0
        cycle_pos = t % cycle_duration
        
        state = "stack"
        if 4.0 <= cycle_pos < 7.0:
            state = "f1"
        elif cycle_pos >= 7.0:
            state = "f2"
            
        if mode == 1:
            state = "f1" # Force solo if only one face
        elif mode == 0:
            # Fallback center crop
            center_x = w // 2
            x1 = max(0, center_x - target_width//2)
            crop = frame[:, int(x1):int(x1+target_width)]
            img = Image.fromarray(np.array(crop, dtype=np.uint8)).resize((target_width, target_height), Image.LANCZOS)
            return np.array(img)

        # Render State
        if state == "stack":
            slot_w = target_width
            slot_h = target_height // 2 
            top_img = extract_face(params['f1'], slot_w, slot_h, restrict_h=True)
            bottom_img = extract_face(params['f2'], slot_w, slot_h, restrict_h=True)
            return np.vstack((top_img, bottom_img))
        elif state == "f1":
            return extract_face(params['f1'], target_width, target_height, restrict_h=False)
        elif state == "f2":
            return extract_face(params['f2'], target_width, target_height, restrict_h=False)
            
    final_clip = VideoClip(make_frame=frame_generator, duration=clip.duration)
    final_clip = final_clip.set_audio(clip.audio)
    
    if hasattr(clip, 'fps') and clip.fps:
        final_clip.fps = clip.fps
    else:
        final_clip.fps = 24
    
    return final_clip



def process_content_fit(clip, target_width=720, target_height=1280):

    """

    Fit Mode: Fits the entire video width into 1080/720p width.

    Fills empty vertical space with a blurred version of the background.

    """

    mp = get_moviepy()

    ImageClip = mp["ImageClip"] if "ImageClip" in mp else None

    

    print(f"[LOG] Processing Content Fit. Input: {clip.w}x{clip.h}")

    

    # 1. Resize Main Clip to Fit Width

    # We want the video to be full width (target_width)

    # The height will scale automatically.

    

    # Scale factor

    scale = target_width / clip.w

    new_h = int(clip.h * scale)

    

    main_clip = clip.resize(width=target_width)

    

    # Center it vertically

    main_clip = main_clip.set_position(("center", "center"))

    

    # 2. Create Blurred Background

    # Crop the center square/aspect of original to fill the vertical frame?

    # Or just resize original to fill height and blur?

    # Resize to fill height normally covers the width too if landscape.

    

    bg_scale = target_height / clip.h

    if (clip.w * bg_scale) < target_width:

        # If scaling to height still leaves width gaps (super tall video?), scale to width

        bg_scale = target_width / clip.w

        

    bg_clip = clip.resize(height=target_height)

    if bg_clip.w < target_width: 

        bg_clip = clip.resize(width=target_width) # Ensure coverage

        

    # Crop center 9:16

    x_center = bg_clip.w / 2

    bg_clip = bg_clip.crop(x1=x_center - target_width/2, width=target_width, height=target_height)

    

    # Blur

    # MoviePy's gaussian_blur might be slow. PIL is faster?

    # Actually, let's just use a darken effect if blur is too heavy? I'll try generic blur.

    # Note: vfx.gaussian_blur is heavy.

    # OPTIMIZATION: Resize strictly to small, blur, resize up? 

    # For now, let's just use a predefined blur or dark overlay if generic blur is missing.

    try:

        bg_clip = bg_clip.fx(mp["vfx"].gaussian_blur, 15)

    except:

        print("⚠️ Blur unavailable, darkening background.")

        bg_clip = bg_clip.fx(mp["vfx"].colorx, 0.3) # Darken



    # 3. Composite

    final = mp["CompositeVideoClip"]([bg_clip, main_clip], size=(target_width, target_height))

    final.duration = clip.duration

    return final



def process_viral_split(clip, target_width=720, target_height=1280):

    """

    Viral Split Mode (Repurpose.io Style):

    Top half = Smart Cropped Speaker (Active Face).

    Bottom half = Gameplay / Satisfying background (or blurred original if gameplay not provided).

    """

    print(f"[LOG] Processing Viral Split (Repurpose Pro). Input: {clip.w}x{clip.h}")

    

    # Get the top half crop (Smart Face Track)

    # We reuse the logic from process_podcast_stack, but we only have 1 face usually (or we just use dynamic cut)

    # A simple way is to use dynamic cut but restrict height to target_height // 2

    # Since process_dynamic_cut uses target bounds, we can just call it for a half-height target!

    top_half = process_dynamic_cut(clip, target_width, target_height // 2)

    

    # For the bottom half, we'll create a heavily blurred and darkened version of the original video.

    # (In a full implementation, you'd download a GTA/Minecraft video here and crop it, but for now, 

    # dynamic heavily blurred background works perfectly for podcasts too).

    

    # Resize clip to fill bottom half

    scale = target_width / clip.w

    bg_clip = clip.resize(width=target_width)

    if bg_clip.h < (target_height // 2):

        bg_clip = clip.resize(height=(target_height // 2))

    

    # Center crop for bottom half

    y_center = bg_clip.h / 2

    x_center = bg_clip.w / 2

    bg_clip = bg_clip.crop(

        y1=y_center - (target_height // 4), 

        x1=x_center - target_width / 2, 

        width=target_width, 

        height=target_height // 2

    )

    

    # Darken and Blur the bottom half

    mp = get_moviepy()

    try:

        # Blur and Darken

        bg_clip = bg_clip.fx(mp["vfx"].gaussian_blur, 25).fx(mp["vfx"].colorx, 0.4)

    except:

        # Fallback if blur fails

        bg_clip = bg_clip.fx(mp["vfx"].colorx, 0.3)

        

    import numpy as np

    

    def frame_generator(t):

        try:

            top_frame = top_half.get_frame(t)

        except:

            top_frame = top_half.get_frame(top_half.duration - 0.1)

            

        try:

            bot_frame = bg_clip.get_frame(t)

        except:

            bot_frame = bg_clip.get_frame(bg_clip.duration - 0.1)

            

        # Stack them exactly

        return np.vstack((top_frame, bot_frame))

        

    from moviepy.editor import VideoClip

    final_clip = VideoClip(make_frame=frame_generator, duration=clip.duration)

    final_clip = final_clip.set_audio(clip.audio)

    final_clip.fps = clip.fps if hasattr(clip, 'fps') and clip.fps else 24

    return final_clip



    """

    Dispatcher for Layout Logic.

    modes: 'podcast_stack', 'content_fit', 'smart_solo', 'viral_split'

    """

    print(f"🎨 Applying Layout Mode: {mode}")

    

    if mode == 'podcast_stack':

        return process_podcast_stack(clip, target_width, target_height)

    elif mode == 'viral_split':

        return process_viral_split(clip, target_width, target_height)

    elif mode == 'content_fit':

        return process_content_fit(clip, target_width, target_height)

    elif mode == 'smart_solo' or mode == 'center_crop':

        # Use Dynamic Active Speaker Cut (Smart Solo)

        # Fallback to simple center crop if detection fails inside process_dynamic_cut?

        # Actually standard center crop is cheaper but dynamic is better.

        # User requested "Face tracking center crop" -> process_dynamic_cut

        return process_dynamic_cut(clip, target_width, target_height)

    else:

        # Default: content_fit is safest if unknown? Or center crop?

        # Let's Default to Content Fit (No data loss)

        return process_content_fit(clip, target_width, target_height)

        

        if mode == 2:

            # --- AI DIRECTOR LOGIC ---

            # Instead of static sticking, we simulate a multi-cam setup.

            # Cycle: Face 1 (4s) -> Face 2 (4s) -> Group (3s) -> Repeat

            

            cycle_duration = 11.0 # Total loop

            loop_t = t % cycle_duration

            

            f1 = params['f1']

            f2 = params['f2']

            

            # Distance check for grouping

            dist = abs(f1['cx'] - f2['cx'])

            can_group = (dist < w * 0.5)

            

            if loop_t < 4.0:

                 # Shot A: Focus Left/Top (Face 1)

                 target_face = f1

            elif loop_t < 8.0:

                 # Shot B: Focus Right/Bottom (Face 2)

                 target_face = f2

            else:

                 # Shot C: Wide/Group (if possible)

                 if can_group:

                     avg_face = {

                         'cx': (f1['cx'] + f2['cx']) / 2,

                         'cy': (f1['cy'] + f2['cy']) / 2,

                         'w': max(f1['w'], f2['w']) * 1.5, # Wider crop

                         'h': max(f1['h'], f2['h']) * 1.5

                     }

                     target_face = avg_face

                 else:

                     # If too far to group, return to F1

                     target_face = f1



        elif mode == 1:

             target_face = params['f1']

        

        if target_face:

            # We must SMOOTH this target transition, otherwise cuts are instant (which is actually good for cuts).

            # But the *camera movement* within the shot handles interpolation.

            # The 'cut' between targets happens here.

            

            x, y, cw, ch = get_crop_params(target_face, w, h)

            

            # Safety Clamp

            x = max(0, min(w - cw, x))

            y = max(0, min(h - ch, y))

            

            region = frame[int(y):int(y+ch), int(x):int(x+cw)]

            img = Image.fromarray(region).resize((target_width, target_height), Image.LANCZOS)

            return np.array(img)

            

        else:

             # Fallback: Center Crop (Corrected)

             ratio = target_height / h

             new_w = int(w * ratio)

             if new_w >= target_width:

                 img = Image.fromarray(frame).resize((new_w, target_height), Image.LANCZOS)

                 start_x = (new_w - target_width)//2

                 img = img.crop((start_x, 0, start_x+target_width, target_height))

                 return np.array(img)

             else:

                 img = Image.fromarray(frame).resize((target_width, int(h * (target_width/w))), Image.LANCZOS)

                 return np.array(img)



    final_clip = VideoClip(make_frame=frame_generator, duration=clip.duration)

    final_clip = final_clip.set_audio(clip.audio)

    if hasattr(clip, 'fps') and clip.fps: final_clip.fps = clip.fps

    else: final_clip.fps = 24

    

    return final_clip









# --- 3. VIRAL SUBTITLES ---



def create_subtitles(audio_path):

    """

    Generates fast viral subtitles using the cached Whisper model.

    FIX: Groups 2-3 words per line for better readability ("Phrase Mode").

    """

    WHISPER_MODEL = get_whisper_model()

    mp = get_moviepy()

    TextClip = mp["TextClip"]

    

    if not WHISPER_MODEL:

        return []

        

    print(f"[LOG] Starting Whisper Transcribe: {time.time()}")

    result = WHISPER_MODEL.transcribe(audio_path, word_timestamps=True, language="hi")

    text_clips = []

    

    # Vibrant Palette (Neon / Cyberpunk)

    colors = ['#FFD700', '#00FFFF', '#00FF00', '#FF00FF', '#FFA500', '#FFFFFF'] 

    

    # Expanded Emoji Map

    emoji_map = {

        "MONEY": "💰", "CASH": "💵", "DOLLAR": "💲", "RICH": "🤑",

        "AI": "🤖", "ROBOT": "🦾", "FUTURE": "🚀", "TECH": "💻",

        "FAST": "⚡", "SPEED": "🏎️", "QUICK": "🏃",

        "LOVE": "❤️", "HEART": "💖", "LIKE": "👍",

        "FIRE": "🔥", "HOT": "🥵", "BURN": "🧨",

        "HAPPY": "😊", "SMILE": "😁", "FUN": "🎉",

        "SAD": "😢", "CRY": "😭", "PAIN": "💔",

        "BRAIN": "🧠", "MIND": "🤯", "THINK": "🤔",

        "TIME": "⏰", "CLOCK": "⏳", "NOW": "👇",

        "STOP": "🛑", "WAIT": "✋", "NO": "❌", "YES": "✅",

        "SECRET": "🤫", "HIDDEN": "🕵️", "LOCK": "🔒",

        "GROWTH": "📈", "UP": "⬆️", "DOWN": "⬇️",

        "WORLD": "🌎", "GLOBAL": "🌐", "EARTH": "🌍",

        "MAGIC": "✨", "WAND": "🪄", "STAR": "⭐"

    }



    all_words = []

    for segment in result['segments']:

        all_words.extend(segment['words'])

    

    # --- PHRASE GROUPING LOGIC ---

    chunks = []

    current_chunk = []

    

    for i, word in enumerate(all_words):

        current_chunk.append(word)

        

        # Decide when to break the chunk

        should_break = False

        

        # 1. Max Words (2-3 words is sweet spot)

        if len(current_chunk) >= 3:

            should_break = True

        

        # 2. Long Pause Check

        elif i < len(all_words) - 1:

            gap = all_words[i+1]['start'] - word['end']

            if gap > 0.3: # If >300ms silence, break natural phrase

                should_break = True

                

        # 3. Last Word

        if i == len(all_words) - 1:

            should_break = True

            

        if should_break:

            # Create Chunk Data

            chunk_text = " ".join([w['word'].strip().upper() for w in current_chunk])

            start_t = current_chunk[0]['start']

            end_t = current_chunk[-1]['end']

            

            # Emoji Injection (Check whole phrase)

            for key, emoji in emoji_map.items():

                if key in chunk_text:

                    chunk_text += f" {emoji}"

                    break # One emoji per chunk is enough

            

            # Check Next Chunk Start for Overlap Safety

            if i < len(all_words) - 1:

                next_start = all_words[i+1]['start']

                if end_t > next_start:

                    end_t = next_start

            

            duration = end_t - start_t

            if duration < 0.2: duration = 0.2

            

            chunks.append({

                "text": chunk_text,

                "start": start_t,

                "duration": duration

            })

            current_chunk = []

            

    # Create Clips

    for i, c in enumerate(chunks):

        color = colors[i % len(colors)]

        try:

            # TRY 1: High Quality Caption (Requires ImageMagick)

            # Use specific font that is likely to exist on Windows to avoid generic errors

            # or allow MoviePy to pick default.

            txt = (TextClip(c['text'], fontsize=70, color=color, font='Arial', 

                           stroke_color='black', stroke_width=3, method='caption', size=(700, None))

                   .set_position(('center', 0.8), relative=True)

                   .set_start(c['start'])

                   .set_duration(c['duration'])) 

            text_clips.append(txt)

        except Exception as e:

            print(f"⚠️ TextClip Method 'caption' failed: {e}. Trying fallback...")

            try:

                # TRY 2: Simple Label (No ImageMagick wrap needed usually, but less pretty)

                # method='label' is safer

                txt = (TextClip(c['text'], fontsize=60, color=color, font='Arial', 

                               stroke_color='black', stroke_width=2, method='label')

                       .set_position(('center', 0.8), relative=True)

                       .set_start(c['start'])

                       .set_duration(c['duration']))

                text_clips.append(txt)

            except Exception as e2:

                 print(f"❌ TextClip Fallback failed too: {e2}")

            

    print(f"[LOG] Subtitles Generated: {len(text_clips)} phrases.")
    return text_clips

from config import QUALITY_TIERS

def map_scenes_to_timestamps(scenes, whisper_result):
    """
    Maps each scene's text to exact start and end timestamps from Whisper words.
    """
    words = whisper_result.get("segments", [])
    all_words = []
    for segment in words:
        if "words" in segment:
            all_words.extend(segment["words"])
            
    if not all_words:
        return scenes
        
    word_idx = 0
    total_words = len(all_words)
    
    for scene in scenes:
        scene_text = scene.get("text", "")
        # Very simple mapping: count words in scene_text
        scene_word_count = len(scene_text.split())
        
        if scene_word_count == 0 or word_idx >= total_words:
            scene["start_time"] = all_words[-1]["end"] if all_words else 0
            scene["end_time"] = all_words[-1]["end"] if all_words else 0
            scene["duration"] = 0
            continue
            
        start_word = all_words[word_idx]
        
        end_idx = min(word_idx + scene_word_count - 1, total_words - 1)
        end_word = all_words[end_idx]
        
        scene["start_time"] = start_word["start"]
        scene["end_time"] = end_word["end"]
        scene["duration"] = scene["end_time"] - scene["start_time"]
        
        word_idx = end_idx + 1
        
    return scenes


def generate_turbo_video(audio_path, visual_terms, output_path, platform="tiktok", 
user_plan="free", main_topic=None, mood="informative", resolution=1080, watermark=False, subtitle_preset="bold_viral", 
hook_boost=False, brand_kit=None, bgm_style=None):
    """
    Generates video with quality based on user plan and enforced resolution/watermark.
    Uses FFmpeg ASS subtitles for viral styling.
    """
    mp = get_moviepy()
    AudioFileClip = mp["AudioFileClip"]
    VideoFileClip = mp["VideoFileClip"]
    concatenate_videoclips = mp["concatenate_videoclips"]
    CompositeVideoClip = mp["CompositeVideoClip"]
    
    # 1. ENFORCE PLAN LIMITS (Double Check)
    limits = get_plan_limits(user_plan)
    allowed_presets = limits.get("allowed_presets", ["bold_viral"])
    
    if "all" not in allowed_presets and subtitle_preset not in allowed_presets:
        print(f"⚠️ Plan '{user_plan}' cannot use '{subtitle_preset}'. Fallback to 'bold_viral'.")
        subtitle_preset = "bold_viral"
        
    if hook_boost and not limits.get("hook_boost", False):
         print(f"⚠️ Plan '{user_plan}' cannot use Hook Boost. Disabling.")
         hook_boost = False

    print(f"[LOG] Starting Turbo Generation Pipeline: {time.time()} (Plan: {user_plan}, Preset: {subtitle_preset}, HookBoost: {hook_boost})")
    t_pipeline_start = time.time()
    
    # --- CONTEXT-AWARE MODE CHECK ---
    # visual_terms can now be a LIST of STRINGS (Legacy) OR a LIST of DICTS (Scene Objects)
    smart_mode = False
    if visual_terms and isinstance(visual_terms, list) and len(visual_terms) > 0 and isinstance(visual_terms[0], dict):
        print(f"[LOG] Smart Context-Aware Mode ACTIVATED with {len(visual_terms)} scenes.")
        smart_mode = True
    else:
        print(f"[LOG] Legacy Random-Clip Mode (Terms: {visual_terms})")


    # QA UPGRADE: Resolve Quality Config

    plan_config = QUALITY_TIERS.get(user_plan.lower(), QUALITY_TIERS['free'])

    

    orientation = "portrait" if platform == "tiktok" else "landscape"

    

    # Resolve Targets

    target_w = plan_config['width']

    target_h = plan_config['height']

    bitrate = plan_config.get('bitrate', '3000k')

    

    if orientation == "landscape":

        target_w, target_h = target_h, target_w # Swap

        

    print(f"   -> Target Resolution: {target_w}x{target_h} @ {bitrate}")

    

    
    w, h = target_w, target_h

    # 1. DOWNLOAD (Parallel)
    # Pass target_w as min_width preference (if logic requires > 720)
    # Note: For Pexels, if we want 4K, min_width=3840. If we want 1080p, min_width=1920.
    # Our target_w logic sets 1080 for HD.
    
    download_terms = []
    if smart_mode:
        # Extract keywords from all scenes
        for scene in visual_terms:
            kws = scene.get('keywords', [])
            if isinstance(kws, str): kws = [kws]
            if kws: download_terms.append(kws[0])
            else: download_terms.append("lifestyle")
            
        # Deduplicate to save bandwidth but keep order? 
        # Actually batch_download usually handles a list.
        print(f"[LOG] Smart Mode: Downloading {len(download_terms)} specific clips...")
    else:
        download_terms = visual_terms

    clip_paths = batch_download_videos(download_terms, orientation=orientation, min_width=target_w)
    if not clip_paths:
        raise ValueError("No clips were downloaded!")
        

    # 2. AUDIO ANALYZE & SYNC
    all_opened_clips = []
    all_opened_audio = []
    video = None
    final_clips = []

    try:
        audio = AudioFileClip(audio_path)
        all_opened_audio.append(audio)
        total_duration = audio.duration
        
        print("[LOG] Transcribing for Cinematic Sync & Subtitles...")
        WHISPER_MODEL = get_whisper_model()
        whisper_result = WHISPER_MODEL.transcribe(audio_path, word_timestamps=True, language="hi")
        
        # Explicit garbage collection after Whisper peak
        gc.collect()

        if smart_mode:
            visual_terms = map_scenes_to_timestamps(visual_terms, whisper_result)

        # 3. EDIT (The "Fast Cuts" Logic)
        print(f"[LOG] Starting Editing: {time.time()}")
        current_time = 0
        clip_idx = 0
        
        # Loop until we fill the audio duration
        while current_time < total_duration:
            # --- HOOK BOOST FLAG ---
            is_hook_zone = current_time < 3.0  # First 3 seconds = HOOK
            
            remaining = total_duration - current_time
            target_duration = 2.5 # Default
            
            # SMART SELECTION LOGIC
            query_term = "lifestyle" # Fallback
            
            if smart_mode:
                 # Find first un-exhausted scene
                 scene_idx = 0
                 while scene_idx < len(visual_terms) and 'duration' in visual_terms[scene_idx] and visual_terms[scene_idx]['duration'] == 0:
                     scene_idx += 1
                 if scene_idx >= len(visual_terms):
                     scene_idx = len(visual_terms) - 1 # Fallback to last scene if all exhausted
                 
                 effective_idx = clip_idx if clip_idx < len(clip_paths) else clip_idx % len(clip_paths)
                 
                 p = clip_paths[effective_idx]
                 scene_data = visual_terms[scene_idx]
                 
                 query_term = scene_data.get('keywords', ["calm person neutral"])[0]
                 
                 # PERFECT SYNC: Calculate exact duration based on Whisper or text length ratio
                 if 'duration' in scene_data and scene_data['duration'] > 0:
                     target_duration = scene_data['duration']
                     
                     # Dynamic Pacing: Sub-cutting (B-Roll Injection)
                     if target_duration > 3.5:
                         target_duration = target_duration / 2.0
                         scene_data['duration'] = target_duration # Leave remainder for next pass
                         # Don't pop the scene, but increment clip_idx to fetch a new visual
                         clip_idx += 1
                         print(f"   -> [Sync] B-ROLL INJECTED! Scene {scene_idx+1}: '{query_term}' | Sub-Duration = {target_duration:.2f}s")
                     else:
                         scene_data['duration'] = 0 # Exhausted
                         print(f"   -> [Sync] Scene {scene_idx+1}: '{query_term}' | Perfect Duration = {target_duration:.2f}s")
                         clip_idx += 1
                         # Pop the exhausted scene so the next iteration uses the next scene
                         visual_terms[scene_idx]['duration'] = 0 
                         
                 else:
                     # LEGACY FALLBACK or Scene Exhausted
                     scene_text = scene_data.get('text', '')
                     total_text = " ".join([s.get('text', '') for s in visual_terms])
                     
                     if len(total_text) > 0 and len(scene_text) > 0:
                         scene_words = len(scene_text.split())
                         total_words = len(total_text.split())
                         target_duration = (scene_words / total_words) * total_duration
                     else:
                         target_duration = total_duration / len(visual_terms)
                         
                     # Dynamic Pacing for legacy too
                     if target_duration > 3.5:
                         target_duration = target_duration / 2.0
                         scene_data['duration'] = target_duration # Track it
                         clip_idx += 1
                     else:
                         print(f"   -> [Sync] Scene {scene_idx+1}: '{query_term}' | Math Duration = {target_duration:.2f}s")
                         clip_idx += 1
                         visual_terms[scene_idx]['duration'] = 0
                 
            else:
                 # LEGACY: Cycle through downloaded clips with dynamic pacing
                 half_point = total_duration / 2
                 if current_time < half_point:
                     target_duration = 2.0  # Fast cuts for engagement
                 else:
                     target_duration = 3.0  # Slightly longer for story progression
                 
                 p = clip_paths[clip_idx % len(clip_paths)]
                 clip_idx += 1
            
            # Determine actual clip length
            duration = min(target_duration, remaining)

            try:
                # Load & IMMEDIATE RESIZE (Crucial for Speed)
                raw_c = VideoFileClip(p)
                all_opened_clips.append(raw_c)
                c = raw_c

                # Force Resize BEFORE any processing (Use Plan Settings)
                if orientation == "portrait":
                    # Portrait Target: target_w x target_h
                    if c.w > target_w:
                        c = c.resize(width=target_w)
                    if c.h < target_h:
                        c = c.resize(height=target_h)
                    crop_x1 = (c.w / 2) - (target_w / 2)
                    c = c.crop(x1=crop_x1, width=target_w, height=target_h)
                else:
                    # Landscape Target: target_w x target_h (swapped logic in setup)
                    if c.h > target_h:
                        c = c.resize(height=target_h)
                    if c.w < target_w:
                        c = c.resize(width=target_w)
                    crop_y1 = (c.h / 2) - (target_h / 2)
                    c = c.crop(y1=crop_y1, width=target_w, height=target_h)

                # Safety: Loop if source is shorter
                if c.duration < duration:
                    c = c.loop(duration=duration)

                # Cut exactly
                c = c.subclip(0, duration)
                c = c.resize((w, h)) # Double check final dimensions

                # --- HOOK ZOOM EFFECT ---
                # Apply 1.05x zoom for first 3 seconds (scroll-stopping punch)
                if is_hook_zone:
                    zoom_factor = 1.05
                    zoomed_w = int(w * zoom_factor)
                    zoomed_h = int(h * zoom_factor)
                    c = c.resize((zoomed_w, zoomed_h))
                    # Center crop back to target size
                    crop_x = (zoomed_w - w) // 2
                    crop_y = (zoomed_h - h) // 2
                    c = c.crop(x1=crop_x, y1=crop_y, width=w, height=h)
                    print(f"   🎯 HOOK BOOST: Applied 1.05x zoom to hook clip")

                final_clips.append(c)
                current_time += duration

            except Exception as e:
                print(f"⚠️ Failed to process clip {p}: {e}")

        # Sequential concatenation with method="chain" avoids multi-layer composite memory inflation
        video = concatenate_videoclips(final_clips, method="chain")

        # Add Background Music Logic
        final_audio = audio
        if bgm_style:
            bgm_path = os.path.join(os.path.dirname(__file__), "assets", "bgm", f"{bgm_style.lower()}.mp3")
            if os.path.exists(bgm_path):
                try:
                    bgm = AudioFileClip(bgm_path)
                    all_opened_audio.append(bgm)
                    bgm = bgm.volumex(0.1)  # 10% volume for background
                    from moviepy.audio.fx.all import audio_loop
                    bgm = audio_loop(bgm, duration=video.duration)
                    final_audio = mp["CompositeAudioClip"]([audio, bgm])
                    all_opened_audio.append(final_audio)
                    print(f"[LOG] Applied BGM style: {bgm_style}")
                except Exception as e:
                    print(f"[LOG] Failed to apply BGM {bgm_style}: {e}")

        video = video.set_audio(final_audio)

        # 4. SUBTITLES (FFmpeg ASS Sidecar)
        ass_path = output_path.replace(".mp4", ".ass")
        preset_config = SUBTITLE_PRESETS.get(subtitle_preset, SUBTITLE_PRESETS["bold_viral"])
        generate_ass(whisper_result['segments'], ass_path, preset_config, platform=platform, hook_boost=hook_boost, brand_kit=brand_kit)
        
        # Escape path for FFmpeg (Windows strictness)
        try:
            rel_ass_path = os.path.relpath(ass_path, start=os.getcwd())
        except ValueError:
            rel_ass_path = ass_path
        
        ffmpeg_ass_path = rel_ass_path.replace("\\", "/").replace(":", "\\\\:")

        # 5. RENDER (ULTRAFAST DRAFT MODE + SUBS)
        print(f"[LOG] Starting Render: {time.time()}")
        
        # Free memory before FFmpeg encoding process
        gc.collect()

        video.write_videofile(
            output_path,
            fps=24,                  
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",      
            bitrate=bitrate,         
            threads=2,               
            logger=None,
            ffmpeg_params=["-vf", f"subtitles='{ffmpeg_ass_path}'"] # BURN SUBS
        )

    finally:
        # Cleanup guaranteed even on error or early return
        print(f"[LOG] Cleaning Up: {time.time()}")
        if video is not None:
            try:
                video.close()
            except Exception:
                pass
        for c in final_clips:
            try:
                c.close()
            except Exception:
                pass
        for raw_c in all_opened_clips:
            try:
                raw_c.close()
            except Exception:
                pass
        for a in all_opened_audio:
            try:
                a.close()
            except Exception:
                pass
        gc.collect()

    print(f"[LOG] Turbo Video Complete: {time.time()} (Total Pipeline: {time.time() - t_pipeline_start:.2f}s)")
    return output_path


def add_viral_captions(video_path, output_path, subtitle_preset="bold_viral", hook_boost=False, platform="shorts", brand_kit=None, custom_hook_text=None, headline_text=None, use_progress_bar=True):
    """
    Takes an existing video, transcribes it, and burns viral ASS subtitles.
    Also applies FFmpeg filters for Progress Bars and Headlines (Repurpose.io style).
    """
    import os
    import shutil
    import subprocess
    
    print(f"[LOG] Adding Viral Captions ({subtitle_preset}) to {video_path}...")
    
    # 1. Transcribe (Fix 3: use shared word-level timestamp function)
    from services.subtitle_generator import get_word_level_timestamps
    word_timings = get_word_level_timestamps(video_path, language="hi")
    # Extract raw Whisper result (last element contains "_raw" key)
    raw_entry = word_timings[-1] if word_timings and "_raw" in word_timings[-1] else {}
    result = raw_entry.get("_raw", {"text": "", "segments": []})
    
    text_content = result.get("text", "").strip()
    has_speech = bool(text_content and len(result.get("segments", [])) > 0)
    
    # 2. Generate ASS
    ass_path = output_path.replace(".mp4", ".ass")
    
    if has_speech:
        preset_config = SUBTITLE_PRESETS.get(subtitle_preset, SUBTITLE_PRESETS["bold_viral"])
        generate_ass(result['segments'], ass_path, preset_config, platform=platform, hook_boost=hook_boost, brand_kit=brand_kit, custom_hook_text=custom_hook_text)
    else:
        print("[LOG] Whisper detected no speech. Bypassing ASS subtitle generation.")
    
    # 3. Calculate FFmpeg Filters
    from moviepy.editor import VideoFileClip
    try:
        temp_c = VideoFileClip(video_path)
        duration = temp_c.duration
        temp_c.close()
    except:
        duration = 60.0
        
    filters = []
    
    # A. Headline Filter
    if headline_text:
        # Sanitize for FFmpeg drawtext
        safe_title = headline_text.replace("'", "").replace(":", "").replace("\\", "").replace("%", "").replace(",", "")
        # Draw box with text at the top (y=150 is good for Shorts to avoid UI)
        font_size = 70
        filters.append(f"drawtext=text='{safe_title}':fontcolor=black:fontsize={font_size}:box=1:boxcolor=yellow@0.9:boxborderw=25:x=(w-text_w)/2:y=180")
        
    # B. Progress Bar Filter
    if use_progress_bar:
        # Drawbox that fills from left to right at the bottom (y=ih-20)
        # Progress bar at bottom:
        filters.append(f"drawbox=x=0:y=ih-20:w=iw*t/{duration}:h=20:color=yellow@0.9:t=fill")

    # C. Subtitle ASS Filter
    if has_speech:
        ffmpeg_ass_path = ass_path.replace("\\", "/").replace(":", "\\:")
        # We downloaded Noto Sans Devanagari to assets/fonts on startup
        fonts_dir = os.path.join(os.path.dirname(__file__), "assets", "fonts").replace("\\", "/").replace(":", "\\:")
        filters.append(f"subtitles='{ffmpeg_ass_path}':fontsdir='{fonts_dir}'")
    
    if not filters:
        # If there are no filters at all (no hook, no progress, no subs), just copy the stream
        shutil.copyfile(video_path, output_path)
        print("[LOG] No visual edits applied. Output copied directly.")
        return output_path

    vf_string = ",".join(filters)
    
    # 4. Burn with FFmpeg (Subprocess for speed)
    # Force system ffmpeg because imageio static binary lacks drawtext/harfbuzz
    ffmpeg_binary = os.environ.get("SYSTEM_FFMPEG_EXE", "ffmpeg")
    cmd = [
        ffmpeg_binary,
        '-i', video_path,
        '-vf', vf_string, 
        '-c:a', 'aac', # Force AAC Audio for Web Compatibility
        '-b:a', '128k',
        '-strict', 'experimental',
        '-c:v', 'libx264',
        '-preset', 'ultrafast', # Draft speed
        '-y',
        output_path
    ]
    
    print(f"[CMD] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    return output_path

def apply_meme_overlays(video_path: str, script_timings: list, output_path: str):
    """
    Overlays meme assets dynamically onto the video based on AI Director's script timings.
    """
    import os
    
    memes_to_apply = [t for t in script_timings if t.get("meme_overlay") and str(t["meme_overlay"]).lower() != "none"]
    if not memes_to_apply:
        print("[Viral Editor] No memes requested by AI Director.")
        return video_path

    print(f"[Viral Editor] AI Director requested {len(memes_to_apply)} meme overlays.")
    
    from moviepy.editor import VideoFileClip, concatenate_videoclips
    from moviepy.audio.AudioClip import AudioClip
    
    base_video = VideoFileClip(video_path)
    
    # Process in reverse order to keep timestamps valid!
    memes_to_apply = sorted(memes_to_apply, key=lambda x: x["start"], reverse=True)
    
    for timing in memes_to_apply:
        meme_name = str(timing["meme_overlay"]).lower().strip()
        meme_path = os.path.join(os.path.dirname(__file__), "assets", "memes", f"{meme_name}.mp4")
        
        if not os.path.exists(meme_path):
            print(f"[Viral Editor WARNING] Meme asset not found: {meme_path}. Please upload it.")
            continue
            
        print(f"[Viral Editor] Slicing video to insert meme '{meme_name}' at {timing['start']}s")
        meme_clip = VideoFileClip(meme_path)
        
        # Fit meme to line duration or its natural duration
        line_duration = timing["end"] - timing["start"]
        meme_duration = min(meme_clip.duration, line_duration)
        if meme_duration <= 0:
            continue
            
        meme_clip = meme_clip.subclip(0, meme_duration)
        
        # Resize meme to exactly match the main video's resolution for a seamless cut
        meme_clip = meme_clip.resize(newsize=base_video.size)
        
        # Ensure meme has audio to prevent concatenate_audioclips from failing
        if meme_clip.audio is None:
            # Create a silent audio clip
            def make_frame(t):
                return [0, 0]
            silence = AudioClip(make_frame, duration=meme_duration)
            meme_clip = meme_clip.set_audio(silence)
            
        # Slice both video and audio symmetrically
        part1 = base_video.subclip(0, timing["start"])
        part2 = base_video.subclip(timing["start"])
        
        # This implicitly calls concatenate_audioclips on the audio tracks, 
        # pausing the ElevenLabs speech while the meme plays.
        base_video = concatenate_videoclips([part1, meme_clip, part2], method="compose")

    print("[Viral Editor] Rendering Final Video with Meme Cut-ins...")
    temp_out = video_path.replace(".mp4", "_memes.mp4")
    
    # Enforce strict 30fps & CRF 23
    base_video.write_videofile(
        temp_out, 
        codec="libx264", 
        audio_codec="aac", 
        fps=30, 
        preset="medium",
        ffmpeg_params=["-crf", "23"]
    )
    
    base_video.close()
    
    import shutil
    shutil.move(temp_out, output_path)
    
    return output_path



