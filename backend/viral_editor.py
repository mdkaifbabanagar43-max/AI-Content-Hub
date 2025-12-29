import os

import random

import requests

import concurrent.futures

import time

import re

import numpy as np

import os

import random

import requests

import concurrent.futures

import time

import re

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

        # 1. Context Anchoring: If the term is vague (e.g. "wallet"), force main topic (e.g. "bitcoin wallet")

        final_query = term

        if main_topic and len(main_topic) > 2:

             # Heuristic: If main_topic words are not in term, prepend them

             # Simple check:

             if main_topic.lower() not in term.lower():

                 final_query = f"{main_topic} {term}"

        

        # 2. Mood/Style Enforcement

        style_suffix = "cinematic realistic 4k"

        if mood:

             m = mood.lower()

             if 'scary' in m or 'horror' in m: style_suffix = "dark gloomy horror cinematic"

             elif 'fast' in m or 'action' in m: style_suffix = "fast action motion blur cinematic"

             elif 'sad' in m: style_suffix = "sad slow rain cinematic"

             elif 'happy' in m or 'fun' in m: style_suffix = "bright colorful happy"

             elif 'tech' in m or 'future' in m: style_suffix = "futuristic cyberpunk neon tech"

        

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



def batch_download_videos(terms, output_dir="/tmp/temp_clips", orientation="portrait", main_topic=None, mood="informative", min_width=720, min_height=1280):

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

from PIL import Image

import numpy as np



class FaceTracker:

    def __init__(self):
        print("🧠 Initializing FaceTracker (MediaPipe)...")
        self.is_broken = False
        self.mp_face_detection = None
        self.detector = None
        
        try:
            # Standard Import 
            import mediapipe as mp
            self.mp_face_detection = mp.solutions.face_detection
            # Force short range (0) or full range (1). 1 is better for shots.
            self.detector = self.mp_face_detection.FaceDetection(min_detection_confidence=0.5, model_selection=1)
        except Exception as e:
            print(f"❌ MediaPipe Init Failed (Headless/GL Error): {e}")
            print("⚠️ Falling back to CENTER CROP mode.")
            self.is_broken = True

        self.cache = {}



    def detect_faces(self, frame_pil):

        """

        Detects faces in a PIL Image using MediaPipe.

        Returns list of (x, y, w, h) absolute pixels.

        """

        w_img, h_img = frame_pil.size
        
        # SAFETY CHECK
        if self.is_broken or self.detector is None:
             return []

        # Convert PIL to Numpy/OpenCV (RGB)

        frame_np = np.array(frame_pil)

        

        # MediaPipe expects RGB (which PIL provides), but ensures contiguous array

        if len(frame_np.shape) == 3:

             # Just in case PIL opened as RGBA or something else, force RGB

             # But typically PIL Image open is RGB.

             pass



        try:

            results = self.detector.process(frame_np)

            faces = []

            

            if results.detections:

                for detection in results.detections:

                    bboxC = detection.location_data.relative_bounding_box

                    

                    x = int(bboxC.xmin * w_img)

                    y = int(bboxC.ymin * h_img)

                    w = int(bboxC.width * w_img)

                    h = int(bboxC.height * h_img)

                    

                    faces.append((x, y, w, h))

                

            return faces

        except Exception as e:

            print(f"❌ MediaPipe Detection Error: {e}")

            return []



    def analyze_clip(self, clip, interval=2.0):

        """

        Analyzes the clip at intervals and builds a trajectory.

        Stores cx, cy, w, h for up to 2 faces and determines layout.

        """

        print(f"Analyzing {clip.duration}s clip for faces (Interval: {interval}s)...")

        current_t = 0

        timestamps = []

        configs = [] 

        

        while current_t < clip.duration:

            try:

                frame_np = clip.get_frame(current_t)

                frame_pil = Image.fromarray(frame_np)

                faces = self.detect_faces(frame_pil)

                

                # Default Config

                cfg = {'mode': 0, 'layout': 'unknown'}



                if len(faces) == 1:

                    # Single Face Mode

                    f = faces[0]

                    cfg = {

                        'mode': 1, 

                        'f1': {'cx': f[0]+f[2]/2, 'cy': f[1]+f[3]/2, 'w': f[2], 'h': f[3]},

                        'layout': 'single'

                    }

                elif len(faces) >= 2:

                    # Two Face Mode - Determine Layout

                    f_x = sorted(faces, key=lambda f: f[0])

                    f_y = sorted(faces, key=lambda f: f[1])

                    

                    dist_x = f_x[-1][0] - f_x[0][0]

                    dist_y = f_y[-1][1] - f_y[0][1]

                    

                    # Robust Layout Detection

                    if dist_y > dist_x * 1.2: 

                        layout = 'vertical'

                        f1 = f_y[0]  # Top

                        f2 = f_y[-1] # Bottom

                    else:

                        layout = 'horizontal'

                        f1 = f_x[0]  # Left

                        f2 = f_x[-1] # Right



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

        """Interpolates params for time t to smooth camera movement."""

        if not hasattr(self, 'timestamps') or not self.timestamps:

            return None

            

        # Find surrounding keyframes

        times = self.timestamps

        if t <= times[0]: return self.configs[0]

        if t >= times[-1]: return self.configs[-1]

        

        # Binary search or simple linear scan (list is short)

        for i in range(len(times)-1):

            if times[i] <= t <= times[i+1]:

                t1, t2 = times[i], times[i+1]

                c1, c2 = self.configs[i], self.configs[i+1]

                

                # Check for Mode Cut (if structure changes, don't interpolate, just cut)

                if c1['mode'] != c2['mode'] or c1.get('layout') != c2.get('layout'):

                     return c1 if (t - t1) < (t2 - t) else c2

                

                # Interpolate Scalar Params (cx, cy, w, h)

                alpha = (t - t1) / (t2 - t1)

                

                def lerp(k, subdict):

                    if subdict not in c1 or subdict not in c2: return 0

                    v1 = c1[subdict].get(k, 0)

                    v2 = c2[subdict].get(k, 0)

                    return v1 + alpha * (v2 - v1)



                new_cfg = c1.copy()

                if 'f1' in c1:

                    new_cfg['f1'] = {k: lerp(k, 'f1') for k in ['cx', 'cy', 'w', 'h']}

                if 'f2' in c1:

                    new_cfg['f2'] = {k: lerp(k, 'f2') for k in ['cx', 'cy', 'w', 'h']}

                    

                return new_cfg

                

        return self.configs[-1]



def process_podcast_stack(clip, target_width=720, target_height=1280):

    """

    AI-Powered Stack using Smart Zoom (Face-Relative Cropping).

    """

    mp = get_moviepy()

    VideoClip = mp["VideoClip"] if "VideoClip" in mp else None 

    # Use standard PIL Image from global import

    

    print(f"[LOG] Processing AI Podcast Stack. Input: {clip.w}x{clip.h}")

    

    # 1. Analyze

    tracker = FaceTracker()

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

            # or tighter: 60%.

            # Let's say we want the CROP Height to be approx 2.0x the Face Height (Head + Shoulders)

            # Reduced from 2.5 to 2.0 to prevent neighboring character bleed.

            

            ideal_crop_h = fh * 2.0

            

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



            # Center on Face

            x1 = cx - crop_w/2

            y1 = cy - crop_h/2

            

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



        if mode == 1:

            # Single Face

            return get_crop(params['f1'], target_width, target_height)

            

            # Stack Mode

            is_vertical = (layout == 'vertical')

            slot_w, slot_h = target_width, int(target_height/2)

            

            top_img = get_crop(params['f1'], slot_w, slot_h, restrict_h=is_vertical)

            bottom_img = get_crop(params['f2'], slot_w, slot_h, restrict_h=is_vertical)

            

            # --- SAFETY ZOOM (Fix Seam Bleeding) ---

            # Scale up by 5% and center crop back to slot size

            # This pushes the edge pixels out of the frame

            def safety_zoom(img_arr, scale=1.05):

                h_in, w_in = img_arr.shape[:2]

                new_w, new_h = int(w_in * scale), int(h_in * scale)

                

                # Resize

                zoomed = Image.fromarray(img_arr).resize((new_w, new_h), Image.LANCZOS)

                

                # Center Crop

                left = (new_w - w_in) // 2

                top = (new_h - h_in) // 2

                right = left + w_in

                bottom = top + h_in

                

                return np.array(zoomed.crop((left, top, right, bottom)))

            

            top_img = safety_zoom(top_img)

            bottom_img = safety_zoom(bottom_img)

            

            return np.vstack((top_img, bottom_img))

            

        else:

            # Fallback

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

    Standard Mode: Dynamically tracks the 'Active' face (or primary face) 

    instead of a static center crop.

    """

    mp = get_moviepy()

    from moviepy.editor import VideoClip

    

    print(f"[LOG] Processing AI Dynamic Cut (Active Speaker). Input: {clip.w}x{clip.h}")

    

    # 1. Reuse Tracker

    tracker = FaceTracker()

    tracker.analyze_clip(clip, interval=1.0) # slightly faster interval

    

    # helper

    def get_crop_params(face_data, w, h):

         cx, cy = face_data['cx'], face_data['cy']

         fw, fh = face_data.get('w', w/4), face_data.get('h', h/4)

         

         # Zoom: 2.5x Face Height

         ideal_crop_h = fh * 2.5

         slot_ratio = target_width / target_height

         crop_w = ideal_crop_h * slot_ratio

         crop_h = ideal_crop_h

         

         # Bounds

         if crop_w > w: crop_w = w; crop_h = w / slot_ratio

         if crop_h > h: crop_h = h; crop_w = h * slot_ratio

         

         x1 = cx - crop_w/2

         y1 = cy - crop_h/2

         x1 = max(0, min(w - crop_w, x1))

         y1 = max(0, min(h - crop_h, y1))

         

         return int(x1), int(y1), int(crop_w), int(crop_h)



    def frame_generator(t):

        params = tracker.get_params(t)

        frame = clip.get_frame(t)

        h, w, _ = frame.shape

        

        mode = params.get('mode', 0) if params else 0

        

        target_face = None

        

        # Logic: If 2 faces, who is active? 

        # Without audio diarization, we just center on the GROUP if close, 

        # or pick the LARGEST face (closest to camera).

        # OR: Just alternate?

        # Simpler: If 2 faces, pick the one that moved most recently? No.



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



def apply_smart_crop(clip, mode="smart_solo", target_width=720, target_height=1280):

    """

    Dispatcher for Layout Logic.

    modes: 'podcast_stack', 'content_fit', 'smart_solo'

    """

    print(f"🎨 Applying Layout Mode: {mode}")

    

    if mode == 'podcast_stack':

        return process_podcast_stack(clip, target_width, target_height)

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

    result = WHISPER_MODEL.transcribe(audio_path, word_timestamps=True, language="en")

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


def generate_turbo_video(audio_path, visual_terms, output_path, platform="tiktok", user_plan="free", main_topic=None, mood="informative", resolution=1080, watermark=False, subtitle_preset="bold_viral", hook_boost=False):
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
        

    # 2. AUDIO ANALYZE

    audio = AudioFileClip(audio_path)

    total_duration = audio.duration

    

    # 3. EDIT (The "Fast Cuts" Logic)

    print(f"[LOG] Starting Editing: {time.time()}")

    final_clips = []

    current_time = 0

    clip_idx = 0

    

    # Loop until we fill the audio duration
    while current_time < total_duration:
        # Determine Clip Length (Target 2.5s for fast cuts, but respects Scene logic if smart)
        remaining = total_duration - current_time
        target_duration = 2.5 # Default fast cut
        
        # SMART SELECTION LOGIC
        query_term = "lifestyle" # Fallback
        
        if smart_mode:
             # Find which scene covers the current time
             # We assume visual_terms is a list of scenes.
             # We need to map time -> scene.
             # Simple logic: If we have N scenes, and we downloaded N clips (hopefully),
             # we just use the clip corresponding to the scene index.
             
             # Problem: clip_paths might differ in length if some downloads failed.
             # Robust mapping:
             # scene_idx -> attempts to map to clip_paths[scene_idx]
             
             scene_idx = min(clip_idx, len(visual_terms) - 1)
             # If downloads failed, we might have fewer clips.
             # Fallback to modulo if indices don't match
             effective_idx = scene_idx if scene_idx < len(clip_paths) else scene_idx % len(clip_paths)
             
             p = clip_paths[effective_idx]
             
             scene_data = visual_terms[scene_idx]
             query_term = scene_data.get('keywords', ["lifestyle"])[0] 
             print(f"   -> [Smart] Scene {scene_idx+1}: '{query_term}' (Clip: {p})")
             
             clip_idx += 1
             
        else:
             # LEGACY: Cycle through downloaded clips
             p = clip_paths[clip_idx % len(clip_paths)]
             clip_idx += 1
        
        # Determine Clip Length (Target 2.5s for fast cuts)
        remaining = total_duration - current_time

        duration = min(2.5, remaining)

        

        try:

            # Load & IMMEDIATE RESIZE (Crucial for Speed)

            c = VideoFileClip(p)

            

            # Force Resize BEFORE any processing (Use Plan Settings)
            if orientation == "portrait":
                # Portrait Target: target_w x target_h
                
                # Resize if larger than target to save RAM
                if c.w > target_w:
                    c = c.resize(width=target_w)

                # Ensure height coverage
                if c.h < target_h:
                    c = c.resize(height=target_h)

                # Center Crop (Use variable targets)
                crop_x1 = (c.w / 2) - (target_w / 2)
                c = c.crop(x1=crop_x1, width=target_w, height=target_h)

            else:
                 # Landscape Target: target_w x target_h (swapped logic in setup)
                 # Safety Net: If height > target_h, resize down
                 if c.h > target_h:
                     c = c.resize(height=target_h)
                 
                 # Check width sufficient?
                 if c.w < target_w:
                     c = c.resize(width=target_w)

                 # Center Crop
                 crop_y1 = (c.h / 2) - (target_h / 2)
                 c = c.crop(y1=crop_y1, width=target_w, height=target_h)



            # Safety: Loop if source is shorter

            if c.duration < duration:

                c = c.loop(duration=duration)

                

            # Cut exactly

            c = c.subclip(0, duration)

            c = c.resize((w, h)) # Double check final dimensions

            

            final_clips.append(c)

            current_time += duration

            

        except Exception as e:

            print(f"⚠️ Failed to process clip {p}: {e}")

            

    # STITCH

    video = concatenate_videoclips(final_clips, method="compose")

    video = video.set_audio(audio)

    

    # 4. SUBTITLES (FFmpeg ASS Sidecar)
    # Generate ASS file
    ass_path = output_path.replace(".mp4", ".ass")
    
    # Transcribe
    print("[LOG] Transcribing for Subtitles...")
    WHISPER_MODEL = get_whisper_model()
    result = WHISPER_MODEL.transcribe(audio_path, word_timestamps=True, language="en")
    
    # Get Preset Config
    preset_config = SUBTITLE_PRESETS.get(subtitle_preset, SUBTITLE_PRESETS["bold_viral"])
    
    # Generate .ass
    generate_ass(result['segments'], ass_path, preset_config, platform=platform, hook_boost=hook_boost)
    
    # Escape path for FFmpeg (Windows strictness)
    # Forward slashes work best in FFmpeg usually
    ffmpeg_ass_path = ass_path.replace("\\", "/").replace(":", "\\:") 
    # Actually on Windows with MoviePy, simple forward slashes usually work if drive letter is handled.
    # Safe bet: relative path if possible, or forward slashes.
    ffmpeg_ass_path = ass_path.replace("\\", "/")

    # 5. RENDER (ULTRAFAST DRAFT MODE + SUBS)
    print(f"[LOG] Starting Render: {time.time()}")
    
    video.write_videofile(
        output_path,
        fps=24,                  
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",      
        bitrate=bitrate,         
        threads=4,               
        logger=None,
        ffmpeg_params=["-vf", f"subtitles='{ffmpeg_ass_path}'"] # BURN SUBS
    )

    

    # Cleanup

    print(f"[LOG] Cleaning Up: {time.time()}")

    for c in final_clips: c.close()

    video.close()

    audio.close()

    

    print(f"[LOG] Turbo Video Complete: {time.time()} (Total Pipeline: {time.time() - t_pipeline_start:.2f}s)")

    return output_path


def add_viral_captions(video_path, output_path, subtitle_preset="bold_viral", hook_boost=False, platform="shorts"):
    """
    Takes an existing video, transcribes it, and burns viral ASS subtitles.
    Used by the Repurposer (Cut logic).
    """
    print(f"[LOG] Adding Viral Captions ({subtitle_preset}) to {video_path}...")
    
    # 1. Transcribe
    WHISPER_MODEL = get_whisper_model()
    # Whisper accepts video files directly too
    result = WHISPER_MODEL.transcribe(video_path, word_timestamps=True, language="en")
    
    # 2. Generate ASS
    ass_path = output_path.replace(".mp4", ".ass")
    
    # Avoid circular import if possible, but we are inside viral_editor
    # logic already imported SUBTITLE_PRESETS at top
    preset_config = SUBTITLE_PRESETS.get(subtitle_preset, SUBTITLE_PRESETS["bold_viral"])
    
    generate_ass(result['segments'], ass_path, preset_config, platform=platform, hook_boost=hook_boost)
    
    # 3. Burn with FFmpeg (Subprocess for speed)
    from moviepy.config import get_setting
    try:
        ffmpeg_binary = get_setting("FFMPEG_BINARY")
    except:
        ffmpeg_binary = "ffmpeg"
        
    # Escape path
    ffmpeg_ass_path = ass_path.replace("\\", "/").replace(":", "\\:")
    
    cmd = [
        ffmpeg_binary,
        '-i', video_path,
        '-vf', f"subtitles='{ffmpeg_ass_path}'", 
        '-c:a', 'aac', # Force AAC Audio for Web Compatibility
        '-b:a', '128k',
        '-strict', 'experimental',
        '-c:v', 'libx264',
        '-preset', 'ultrafast', # Draft speed
        '-y',
        output_path
    ]
    
    import subprocess
    print(f"[CMD] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    return output_path




