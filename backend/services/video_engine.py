import os
import asyncio
import random
import time
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from vertexai.generative_models import Part

# STRICT LIMIT: Only 1 request to Gemini at a time.
# This prevents hitting the 'Requests Per Minute' quota.
gemini_lock = asyncio.Semaphore(1)

async def generate_with_retry(model, prompt_parts, max_retries=3):
    """ Wraps model.generate_content_async with 'Nuclear Backoff' (65s+) and Global Lock. """
    
    # Global Serial Lock
    async with gemini_lock:
        # print("🚦 Acquired Gemini Lock.") 
        
        for attempt in range(max_retries):
            try:
                print(f"🚀 Sending Request (Attempt {attempt+1})...")
                return await model.generate_content_async(prompt_parts)
            except (ResourceExhausted, ServiceUnavailable) as e:
                if attempt == max_retries - 1:
                    print(f"❌ Giving up. Quota is truly dead.")
                    raise e
                
                # NUCLEAR BACKOFF: 65s+ to reset RPM
                wait_time = 65 + (attempt * 5)
                print(f"🛑 Quota Penalty Box. Sleeping for {wait_time}s to clear RPM counter...")
                await asyncio.sleep(wait_time) 
        return None
try:
    from moviepy.editor import VideoFileClip, clips_array, TextClip, CompositeVideoClip
except ImportError:
    print("Warning: MoviePy not found. Video processing will fail.")

# Lazy loaded
mp_face = None
face_detector = None

def get_face_center(frame):
    """
    Returns the relative X center (0.0 to 1.0) of the largest face.
    Defaults to 0.5 (center) if no face is found.
    """
    global mp_face, face_detector, mp
    import mediapipe as mp # Lazy import

    if not face_detector:
        mp_face = mp.solutions.face_detection
        face_detector = mp_face.FaceDetection(min_detection_confidence=0.6)
    try:
        # Convert Frame to RGB (MoviePy uses RGB, but MediaPipe expects RGB too. 
        # However, checking if valid numpy array is good practice)
        if frame is None: return 0.5
        
        results = face_detector.process(frame)
        
        if results.detections:
            # Get the largest face (assuming main speaker is largest)
            # Detections are not sorted by size by default, but usually first is prominent.
            # Let's find max width just in case.
            largest_face = max(results.detections, key=lambda d: d.location_data.relative_bounding_box.width)
            
            bbox = largest_face.location_data.relative_bounding_box
            center_x = bbox.xmin + (bbox.width / 2)
            return center_x
    except Exception as e:
        print(f"Face Warning: {e}")
        
    return 0.5 # Default to center if no face found

async def repurpose_video(video_path, mode='center_crop', unique_id=None, resolution=1080, watermark=False):
    """
    Repurposes a video based on the selected mode.
    Run largely in a thread to prevent blocking the async event loop.
    """
    if not unique_id: unique_id = "temp"
    output_filename = f"repurpose_{unique_id}.mp4"
    output_path = f"/tmp/{output_filename}"
    
    print(f"🎬 Repurposing Video: {video_path} (Mode: {mode}, Res: {resolution}, WM: {watermark})")
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Use run_in_executor for CPU-bound MoviePy work
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _process_video_sync, video_path, output_path, mode, resolution, watermark)
    
    return output_path

def _process_video_sync(video_path, output_path, mode, resolution, watermark):
    """ Synchronous worker for MoviePy """
    # Helper to enforce even dimensions
    def make_even(x):
        return int(x) if int(x) % 2 == 0 else int(x) - 1

    target_w = make_even(resolution)
    target_h = make_even(resolution * 16 / 9) # 9:16 aspect
    
    clip = VideoFileClip(video_path)

    if mode == 'podcast_stack':
        # 🎙️ MODE A: PODCAST STACK
        print("Processing Mode: Podcast Stack (Split Left/Right -> Stack Top/Bottom)")

        # Split Left/Right
        half_width = make_even(clip.w / 2)
        left_clip = clip.crop(x1=0, y1=0, width=half_width, height=clip.h)
        right_clip = clip.crop(x1=half_width, y1=0, width=half_width, height=clip.h)

        # Calculate stack height
        stack_h = make_even(target_h / 2)
        
        # Resize Logic: Resize to Target Width, then Crop Vertical Center to Stack Height
        # This prevents "Squashing" the faces.
        
        # Top (Left Source)
        top_stack = left_clip.resize(width=target_w) 
        if top_stack.h > stack_h:
            # Crop center vertical
            y_center = top_stack.h / 2
            y1 = y_center - (stack_h / 2)
            top_stack = top_stack.crop(y1=y1, height=stack_h)
        else:
            # Pad or stretch? Stretching slightly is safer than black bars for MVP
            top_stack = top_stack.resize(newsize=(target_w, stack_h))

        # Bottom (Right Source)
        bot_stack = right_clip.resize(width=target_w)
        if bot_stack.h > stack_h:
            y_center = bot_stack.h / 2
            y1 = y_center - (stack_h / 2)
            bot_stack = bot_stack.crop(y1=y1, height=stack_h)
        else:
            bot_stack = bot_stack.resize(newsize=(target_w, stack_h))

        final_clip = clips_array([[top_stack], [bot_stack]])

    else:
        # 🎯 MODE B: SMART CENTER CROP
        print("Processing Mode: Smart Center Crop")
        
        sample_t = min(2.0, clip.duration / 2)
        sample_frame = clip.get_frame(sample_t)
        rel_center_x = get_face_center(sample_frame)
        
        # Crop logic
        target_ratio = 9 / 16
        new_width = make_even(clip.h * target_ratio)
        if new_width > clip.w: new_width = make_even(clip.w)
        
        pixel_center_x = rel_center_x * clip.w
        x1 = int(pixel_center_x - (new_width / 2))
        if x1 < 0: x1 = 0
        if x1 + new_width > clip.w: x1 = clip.w - new_width
        
        final_clip = clip.crop(x1=x1, y1=0, width=new_width, height=clip.h)
        final_clip = final_clip.resize(newsize=(target_w, target_h))

    # Watermark Logic
    if watermark:
        try:
             wm_txt = (TextClip("AI VIDEO SAAS", fontsize=int(target_h/30), color='white', font='Arial', method='label')
                       .set_opacity(0.5)
                       .set_position(('right', 'bottom'))
                       .set_duration(final_clip.duration)
                       .margin(right=20, bottom=20, opacity=0))
             final_clip = CompositeVideoClip([final_clip, wm_txt], size=(target_w, target_h))
        except Exception as e:
             print(f"WM Error: {e}")

    # Render
    final_clip.write_videofile(
        output_path, 
        codec='libx264', 
        audio_codec='aac', 
        fps=24, 
        preset='ultrafast',
        logger=None # Silence progress bar in logs to avoid spam
    )
    
    clip.close()
    final_clip.close()
    print(f"✅ Repurpose Complete: {output_path}")
