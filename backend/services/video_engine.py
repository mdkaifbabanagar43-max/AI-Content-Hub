import os
import asyncio
import random
import time
import subprocess
import tempfile
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

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
    from config import TEMP_DIR
    if not unique_id: unique_id = "temp"
    output_filename = f"repurpose_{unique_id}.mp4"
    output_path = os.path.join(TEMP_DIR, output_filename)
    
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
                 # Add "ShortcutAI" text in bottom right, semi-transparent
                 wm_txt = (TextClip("ShortcutAI", fontsize=int(target_h/30), color='white', font='Arial', method='label')
                           .set_opacity(0.40)
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


# ─────────────────────────────────────────────────────────────
# TREND CLONER — SCENE STITCHING  (Fix 1b, 4, 5)
# ─────────────────────────────────────────────────────────────

def concat_scenes(clip_paths: list, output_path: str, fps: int = 30, crf: int = 23, crossfade_frames: int = 0, outro_text: str = None) -> str:
    """
    Concatenates multiple scene clip paths into a single output video.

    Strategy:
    1. First attempts FFmpeg concat demuxer (-c copy) — fastest, no quality loss.
       Requires all clips to share identical codec/resolution/fps.
    2. Falls back to MoviePy concatenate_videoclips() re-encode if streams differ.

    Args:
        clip_paths:       Ordered list of absolute file paths to scene clips.
        output_path:      Destination for the stitched output file.
        fps:              Target frame rate (30 for Shorts/Reels/TikTok standard).
        crf:              x264 CRF value for quality (23 = good quality, smaller file).
        crossfade_frames: Number of frames to blend between scenes (0 = hard cut).
        outro_text:       Optional text for a 2-second punchline card at the end.

    Returns:
        output_path on success.
    """
    if not clip_paths:
        raise ValueError("[concat_scenes] No clip paths provided.")

    print(f"[Video Engine] Stitching {len(clip_paths)} scenes → {output_path} (fps={fps}, crf={crf})")
    
    # --- Fix 3b: Handle Outro Text Card ---
    if outro_text:
        try:
            from moviepy.editor import TextClip, VideoFileClip, ColorClip, CompositeVideoClip
            
            first_clip = VideoFileClip(clip_paths[0])
            w, h = first_clip.size
            first_clip.close()
            
            font_path = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "NotoSansDevanagari-Bold.ttf")
            
            bg = ColorClip(size=(w, h), color=(0,0,0), duration=2)
            txt_clip = TextClip(
                outro_text, 
                fontsize=70, 
                color='white', 
                font=font_path,
                method='caption',
                size=(w*0.8, h*0.8)
            ).set_position('center').set_duration(2)
            
            outro_clip = CompositeVideoClip([bg, txt_clip]).set_duration(2)
            outro_path = output_path.replace(".mp4", "_outro.mp4")
            
            # Enforce 30fps and CRF 23
            outro_clip.write_videofile(
                outro_path,
                fps=fps,
                codec="libx264",
                audio_codec="aac",
                ffmpeg_params=["-crf", str(crf), "-preset", "medium"],
                logger=None
            )
            
            outro_clip.close()
            txt_clip.close()
            bg.close()
            
            clip_paths.append(outro_path)
            print(f"[Video Engine] Appended outro text card to clips list.")
        except Exception as e:
            print(f"[Video Engine WARNING] Failed to generate outro text card: {e}")

    # --- Attempt 1: FFmpeg concat demuxer (zero-loss copy) ---
    try:
        concat_list_path = output_path.replace(".mp4", "_concat_list.txt")
        with open(concat_list_path, "w") as f:
            for path in clip_paths:
                # Escape single quotes in path for ffmpeg concat format
                safe_path = path.replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        ffmpeg_bin = os.environ.get("SYSTEM_FFMPEG_EXE", "ffmpeg")
        cmd = [
            ffmpeg_bin,
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c:v", "libx264",
            "-crf", str(crf),
            "-preset", "medium",
            "-r", str(fps),
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-y",
            output_path
        ]
        print(f"[Video Engine] FFmpeg concat: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, capture_output=True)

        # Cleanup concat list
        if os.path.exists(concat_list_path):
            os.remove(concat_list_path)

        print(f"[Video Engine] ✅ Scene concat complete: {output_path}")
        return output_path

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
        print(f"[Video Engine] FFmpeg concat failed (will re-encode): {stderr[:300]}")
        if os.path.exists(concat_list_path):
            os.remove(concat_list_path)

    # --- Fallback: MoviePy re-encode ---
    print("[Video Engine] Falling back to MoviePy concatenation (re-encode)...")
    from moviepy.editor import VideoFileClip, concatenate_videoclips

    clips = [VideoFileClip(p) for p in clip_paths]
    try:
        stitched = concatenate_videoclips(clips, method="compose")
        stitched.write_videofile(
            output_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            ffmpeg_params=["-crf", str(crf), "-preset", "medium"],
            logger=None
        )
    finally:
        for c in clips:
            c.close()
        if 'stitched' in dir():
            stitched.close()

    print(f"[Video Engine] ✅ Scene concat (MoviePy fallback) complete: {output_path}")
    return output_path


# ─────────────────────────────────────────────────────────────
# WATERMARK HELPER  (Fix 6)
# ─────────────────────────────────────────────────────────────

def apply_watermark_if_needed(input_path: str, output_path: str, plan_tier: str = "free") -> str:
    """
    Overlays a semi-transparent "ShortcutAI" watermark on free/starter tier exports.
    Pro and Agency tiers get a clean, watermark-free output.

    Args:
        input_path:  Path to the video to watermark.
        output_path: Destination path.
        plan_tier:   User plan tier from Firestore ("free", "starter", "creator", "agency").

    Returns:
        output_path (whether watermarked or just copied).
    """
    import shutil

    WATERMARKED_TIERS = {"free", "starter"}
    if plan_tier.lower() not in WATERMARKED_TIERS:
        # Pro/Agency: no watermark — just copy if paths differ
        if input_path != output_path:
            shutil.copyfile(input_path, output_path)
        return output_path

    print(f"[Video Engine] Applying ShortcutAI watermark (plan={plan_tier})...")
    ffmpeg_bin = os.environ.get("SYSTEM_FFMPEG_EXE", "ffmpeg")

    # drawtext: bottom-right, 40% opacity, small font
    import subprocess
    cmd = [
        ffmpeg_bin,
        "-i", input_path,
        "-vf", "drawtext=text='ShortcutAI':fontcolor=white@0.40:fontsize=28:x=w-text_w-20:y=h-text_h-20",
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "medium",
        "-c:a", "copy",
        "-y",
        output_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"[Video Engine] ✅ Watermark applied: {output_path}")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
        print(f"[Video Engine] ⚠️ Watermark failed (returning unwatermarked): {stderr[:200]}")
        if input_path != output_path:
            shutil.copyfile(input_path, output_path)

    return output_path
