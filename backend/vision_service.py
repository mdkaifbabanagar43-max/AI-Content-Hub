import os
import uuid
from google.genai import types
from services.ai_service import get_gemini_client, GEMINI_MODEL_NAME, GEMINI_FALLBACK_MODEL

class VideoAnalyzer:
    def __init__(self):
        self.client = get_gemini_client()

    def generate_script(self, video_path, video_format="TikTok", duration="30 seconds", mood="Viral"):
        print(f"👁️ Analyzing video: {video_path} [Format={video_format}, Duration={duration}, Mood={mood}]")
        
        temp_files = []
        try:
            # Step 1: Extract Frames
            import moviepy.editor as mp # Lazy
            clip = mp.VideoFileClip(video_path)
            clip_duration = clip.duration
            
            # Capture frames at 20% and 80%
            times = [clip_duration * 0.2, clip_duration * 0.8]
            frames = []
            
            for i, t in enumerate(times):
                frame_path = f"temp_frame_{uuid.uuid4()}_{i}.jpg"
                clip.save_frame(frame_path, t=t)
                frames.append(frame_path)
                temp_files.append(frame_path)
                print(f"📸 Captured frame at {t:.2f}s: {frame_path}")
                
            clip.close()

            # Step 2: Prepare Prompt (Customized)
            prompt = f"""
            You are a professional video scriptwriter.
            Topic: Analyze the accompanying images to determine the video topic.
            Platform: {video_format} (Strictly adhere to this style)
            Target Duration: {duration}
            Tone/Mood: {mood}
            Instructions:
            - If Platform is TikTok/Shorts: Use fast pacing, slang, and a strong hook in the first 3 seconds.
            - If Platform is YouTube: Use a structured intro, body, and conclusion.
            - Keep the word count appropriate for {duration} (approx 150 words per minute).
            - Focus on the visual details in these images.
            - Return ONLY the raw text script, no headings or 'Here is the script'.
            """
            
            # Step 3: Call Gemini
            parts = [prompt]
            for frame_path in frames:
                with open(frame_path, "rb") as f:
                    image_data = f.read()
                    parts.append(types.Part.from_bytes(data=image_data, mime_type="image/jpeg"))
            
            print("🤖 Sending images to Gemini...")
            try:
                response = self.client.models.generate_content(
                    model=GEMINI_MODEL_NAME,
                    contents=parts
                )
            except Exception as e:
                print(f"Gemini 3.6 Flash failed, falling back: {e}")
                response = self.client.models.generate_content(
                    model=GEMINI_FALLBACK_MODEL,
                    contents=parts
                )
                
            generated_text = response.text
            print("✅ Script Generated!")
            
            return generated_text

        except Exception as e:
            print(f"❌ Vision Analysis Error: {e}")
            import traceback
            traceback.print_exc()
            return "Error analyzing video."
            
        finally:
            # Step 4: Cleanup
            for path in temp_files:
                if os.path.exists(path):
                    os.remove(path)
                    print(f"🧹 Cleaned up: {path}")
