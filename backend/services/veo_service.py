import os
import time
import subprocess
import tempfile
import uuid
from typing import Optional
from google import genai
from google.genai import types
import cv2


def extract_last_frame(video_path: str, output_image_path: str):
    """Extracts the very last frame of a video using OpenCV."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception("Failed to open video to extract last frame.")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, total_frames - 1))

    ret, frame = cap.read()
    if not ret:
        # Fallback to reading frame by frame if setting pos fails
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        while True:
            ret, next_frame = cap.read()
            if not ret:
                break
            frame = next_frame

    if frame is None:
        cap.release()
        raise Exception("Failed to read any frame from video.")

    cv2.imwrite(output_image_path, frame)
    cap.release()
    print(f"[Veo] Extracted last frame -> {output_image_path}")


def generate_video_with_veo(
    prompt: str,
    model_id: str = "veo-3.1-fast-generate-001",
    region: str = "us-central1",
    target_duration: int = 16,
    reference_image_uri: Optional[str] = None
) -> Optional[bytes]:
    """
    Generate a video using Google Veo API via google-genai SDK.
    Supports chaining multiple 8s videos if target_duration > 8.

    Frame-Continuity Chaining:
      - Chunk 1: Text-to-video from prompt.
      - Chunk 2+: Extract the last frame of the previous chunk via OpenCV,
        encode to JPEG bytes, and pass as `image` kwarg for image-to-video
        continuation so Veo picks up seamlessly from the final frame.

    Returns the concatenated video bytes if successful.
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "shortcutai-backend")
    client = genai.Client(vertexai=True, project=project_id, location=region)

    chunks_needed = max(1, (target_duration + 7) // 8)  # e.g. 14s -> 2, 16s -> 2, 24s -> 3
    temp_dir = os.path.join(tempfile.gettempdir(), f"veo_chain_{uuid.uuid4().hex}")
    os.makedirs(temp_dir, exist_ok=True)

    video_chunks = []

    try:
        for i in range(chunks_needed):
            print(f"[Veo] Submitting generation job (Chunk {i+1}/{chunks_needed}) prompt: '{prompt[:60]}...'")

            kwargs = {
                "model": model_id,
                "prompt": prompt,
                "config": types.GenerateVideosConfig(
                    aspect_ratio="9:16",
                    person_generation="allow_adult"
                )
            }
            
            # --- INITIAL IMAGE CONDITIONING for Chunk 0 ---
            if i == 0 and reference_image_uri:
                try:
                    if reference_image_uri.startswith("gs://"):
                        kwargs["image"] = types.Image(gcs_uri=reference_image_uri, mime_type="image/jpeg")
                        print(f"[Veo] Chunk 1: Using character reference GCS URI: {reference_image_uri}")
                    elif reference_image_uri.startswith("http://") or reference_image_uri.startswith("https://"):
                        import urllib.request
                        with urllib.request.urlopen(reference_image_uri) as resp:
                            ref_bytes = resp.read()
                        kwargs["image"] = types.Image(image_bytes=ref_bytes, mime_type="image/jpeg")
                        print(f"[Veo] Chunk 1: Using character reference from HTTP URL ({len(ref_bytes)} bytes)")
                except Exception as img_err:
                    print(f"[Veo] WARNING: Failed to load reference image '{reference_image_uri}': {img_err}")

            # --- FRAME-CONTINUITY CHAINING for Chunk 2+ ---
            if i > 0 and len(video_chunks) > 0:
                last_chunk_path = video_chunks[-1]
                frame_path = os.path.join(temp_dir, f"frame_{i}.jpg")
                extract_last_frame(last_chunk_path, frame_path)

                # Read JPEG bytes and pass as image seed
                with open(frame_path, "rb") as f:
                    frame_bytes = f.read()
                kwargs["image"] = types.Image(image_bytes=frame_bytes, mime_type="image/jpeg")
                print(f"[Veo] Chunk {i+1}: Using last-frame seed from chunk {i} ({len(frame_bytes)} bytes)")

            operation = client.models.generate_videos(**kwargs)

            print(f"[Veo] Waiting for chunk {i+1} to complete...")
            while not operation.done:
                time.sleep(15)
                try:
                    if hasattr(client, 'operations'):
                        operation = client.operations.get(operation=operation)
                    else:
                        print("[Veo] Cannot poll operation, waiting 120s as fallback.")
                        time.sleep(120)
                        break
                except Exception as e:
                    print(f"[Veo] Polling warning: {e}")

            print(f"[Veo] Chunk {i+1}/{chunks_needed} complete!")

            chunk_bytes = None
            result = getattr(operation, 'result', None)
            generated_videos = getattr(result, 'generated_videos', None) if result else None
            
            if generated_videos and len(generated_videos) > 0:
                generated_video = generated_videos[0]
                if hasattr(generated_video, 'video') and hasattr(generated_video.video, 'video_bytes'):
                    chunk_bytes = generated_video.video.video_bytes

            if not chunk_bytes:
                error_msg = getattr(operation, 'error', None)
                print(f"[Veo] WARNING: No video bytes returned for chunk {i+1}. Safety filter or error: {error_msg}")
                break

            chunk_path = os.path.join(temp_dir, f"chunk_{i}.mp4")
            with open(chunk_path, "wb") as f:
                f.write(chunk_bytes)
            video_chunks.append(chunk_path)
            print(f"[Veo] Saved chunk {i+1} -> {chunk_path} ({len(chunk_bytes)} bytes)")

        if not video_chunks:
            return None

        if len(video_chunks) == 1:
            with open(video_chunks[0], "rb") as f:
                return f.read()

        # --- Concatenate all chunks using FFmpeg concat demuxer ---
        print(f"[Veo] Concatenating {len(video_chunks)} video chunks...")
        list_path = os.path.join(temp_dir, "list.txt")
        with open(list_path, "w") as f:
            for chunk_path in video_chunks:
                safe_path = chunk_path.replace('\\', '/')
                f.write(f"file '{safe_path}'\n")

        output_path = os.path.join(temp_dir, "final_output.mp4")

        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_exe = "ffmpeg"

        cmd = [ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", output_path]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        with open(output_path, "rb") as f:
            final_bytes = f.read()

        print(f"[Veo] Final concatenated video: {len(final_bytes)} bytes")
        return final_bytes

    except Exception as e:
        print(f"[Veo] Generation Error: {e}")
        return None
    finally:
        # Cleanup temp directory
        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except Exception:
                    pass
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except Exception:
                    pass
        try:
            os.rmdir(temp_dir)
        except Exception:
            pass
