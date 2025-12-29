# from google.cloud import translate_v2 as translate
# from google.cloud import texttospeech
# import moviepy.editor as mp 
import os
import uuid
import subprocess
import shutil
from tts_service import GoogleTTSClient
import torchaudio

# FORCE Torchaudio to use 'soundfile'
# Note: set_audio_backend is deprecated/removed in newer torchaudio.
# Soundfile is usually the default if installed.
try:
    if hasattr(torchaudio, 'set_audio_backend'):
        torchaudio.set_audio_backend("soundfile")
        print("✅ set_audio_backend('soundfile') successful")
    else:
        print("ℹ️ torchaudio.set_audio_backend not found (Newer Version). Assuming soundfile backend.")
except Exception as e:
    print(f"⚠️ Could not set audio backend: {e}")

# Lazy Globals
WHISPER_MODEL = None
TRANSLATE_CLIENT = None

def get_whisper_model():
    global WHISPER_MODEL
    import whisper
    if WHISPER_MODEL is None:
        print("⏳ Loading Whisper Model (Dubbing Service)...")
        WHISPER_MODEL = whisper.load_model("base")
        print("✅ Whisper Loaded.")
    return WHISPER_MODEL

def get_moviepy():
    print("⏳ Importing MoviePy (Lazy)...")
    import moviepy.editor as mp
    return mp

def get_translate_client():
    global TRANSLATE_CLIENT
    from google.cloud import translate_v2 as translate
    if TRANSLATE_CLIENT is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(base_dir, "service-account.json")
        if os.path.exists(key_path):
            TRANSLATE_CLIENT = translate.Client.from_service_account_json(key_path)
        else:
            TRANSLATE_CLIENT = translate.Client()
    return TRANSLATE_CLIENT

class VideoDubber:
    def translate_text(self, text, target_lang):
        print(f"🌍 Translating to: {target_lang}")
        if not text or not text.strip():
            return ""
            
        try:
            # Use Vertex AI/Gemini for Context-Aware Translation
            import vertexai
            from vertexai.generative_models import GenerativeModel
            from google.oauth2 import service_account
            
            base_dir = os.path.dirname(os.path.abspath(__file__))
            key_path = os.path.join(base_dir, "service-account.json")
            if os.path.exists(key_path):
                credentials = service_account.Credentials.from_service_account_file(key_path)
                vertexai.init(project="leafy-oxide-480614-m4", location="us-central1", credentials=credentials)
            else:
                vertexai.init(project="leafy-oxide-480614-m4", location="us-central1")

            model = GenerativeModel("gemini-2.0-flash-001")
            
            # Enhanced Prompting for Dubbing
            tone_instruction = "Translate this for a video dub. Match the approximate length of the original sentence if possible. Use natural, spoken phrasing suitable for a viral video."
            
            if target_lang and 'hindi' in target_lang.lower():
                tone_instruction += " For Hindi, use 'Hinglish' (conversational Hindi with English terms) and write in Devanagari/English mix as appropriate for TTS."

            prompt = f"""
            TASK: Translate the following subtitle text to {target_lang} for audio dubbing.
            
            INPUT: "{text}"
            
            GUIDELINES:
            1. {tone_instruction}
            2. Do NOT add explanation or notes.
            3. Return ONLY the translated text.
            """
            
            response = model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            print(f"⚠️ LLM Translation Failed ({e}). Using Standard API.")
            try:
                translate_client = get_translate_client()
                result = translate_client.translate(text, target_language=target_lang)
                return result['translatedText']
            except Exception as e2:
                 print(f"❌ Standard Translate Failed: {e2}")
                 return text 

    def transcribe_video_segments(self, video_path):
        model = get_whisper_model()
        print(f"👂 Transcribing: {video_path}")
        result = model.transcribe(video_path, word_timestamps=False) 
        return result["segments"]

    def separate_audio(self, audio_path, output_dir):
        """
        Uses Demucs to separate audio into 'vocals' and 'no_vocals' (background).
        Returns path to the background track (no_vocals).
        """
        print(f"🎸 Separating Audio: {audio_path}")
        try:
            # We use "htdemucs" model and specific output structure
            # demucs -n htdemucs --two-stems=vocals [file] -o [dir]
            cmd = [
                "demucs", 
                "-n", "htdemucs", 
                "--two-stems=vocals", # Only split vocals vs everything else
                audio_path,
                "-o", output_dir
            ]
            print(f"🚀 Running Demucs: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            
            # Path logic: Demucs outputs to output_dir/htdemucs/{filename_no_ext}/no_vocals.wav
            filename = os.path.splitext(os.path.basename(audio_path))[0]
            bg_path = os.path.join(output_dir, "htdemucs", filename, "no_vocals.wav")
            
            if os.path.exists(bg_path):
                print(f"✅ Background Track Isolated: {bg_path}")
                return bg_path
            else:
                print(f"⚠️ Background track not found at: {bg_path}")
                return None

        except Exception as e:
            print(f"❌ Demucs Separation Failed: {e}")
            return None

    def dub_video(self, video_path, target_lang_code, target_voice_name, sync_mode="audio", resolution=None, watermark=False):
        print(f"🎬 Starting Advanced Dubbing: {video_path} -> {target_lang_code} [Res: {resolution}, WM: {watermark}]")
        
        job_id = str(uuid.uuid4())
        temp_dir = f"temp_dub_{job_id}"
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_output_path = f"dubbed_{job_id}.mp4"
        temp_audio_output = f"dubbed_audio_{job_id}.mp3"

        try:
            mp = get_moviepy()
            from moviepy.editor import AudioFileClip, CompositeAudioClip
            
            # --- Step 1: Analyze Video & Extract Audio ---
            video = mp.VideoFileClip(video_path)
            original_duration = video.duration
            
            if video.audio is None:
                print("⚠️ No audio in video.")
                return None, None
            
            # Export original audio for separation
            original_audio_path = os.path.join(temp_dir, "original.wav")
            video.audio.write_audiofile(original_audio_path, logger=None)

            # --- Step 2: Source Separation (Background Preservation) ---
            print("🔍 Attempting Background Preservation...")
            background_audio_path = self.separate_audio(original_audio_path, temp_dir)
            
            background_clip = None
            if background_audio_path:
                try:
                    # Keep background at decent volume (e.g. 60-70% of original)
                    background_clip = AudioFileClip(background_audio_path).volumex(0.7) 
                    print("🎹 Background track loaded (Demucs)")
                except:
                    print("⚠️ Failed to load background track.")
            else:
                # Fallback: Use original audio at very low volume (Dirty Dub)
                print("⚠️ Demucs failed/missing. Using 'Dirty Dub' (Original @ 10%)")
                background_clip = AudioFileClip(original_audio_path).volumex(0.1)

            # --- Step 3: Transcribe & Translate ---
            segments = self.transcribe_video_segments(video_path) 
            
            tts = GoogleTTSClient()
            dub_clips = []
            
            if background_clip:
                dub_clips.append(background_clip)

            # --- Step 4: Generate Dub Audio with SYNC (Time-Stretching) ---
            import moviepy.audio.fx.all as afx

            for i, seg in enumerate(segments):
                start = seg['start']
                end = seg['end']
                target_duration = end - start
                
                text = seg['text']
                translated = self.translate_text(text, target_lang_code)
                
                if translated:
                    try:
                        # Generate TTS
                        tts_file = tts.generate_audio(translated, target_voice_name)
                        clip = AudioFileClip(tts_file)
                        
                        # CALC SPEED FACTOR
                        current_dur = clip.duration
                        if current_dur > 0:
                            speed_factor = current_dur / target_duration
                            
                            # Clamp speed (0.8x to 1.5x) to avoid 'Chipmunk' or 'Slow-mo'
                            speed_factor = max(0.8, min(speed_factor, 1.5))
                            
                            # Apply speed effect
                            if abs(speed_factor - 1.0) > 0.05: 
                                clip = clip.fx(afx.speedx, speed_factor)
                        
                        # Position
                        clip = clip.set_start(start)
                        dub_clips.append(clip)
                    except Exception as e:
                        print(f"   ❌ TTS/Sync Failed: {e}")

            # --- Step 5: Mix & Merge ---
            print(f"🎚️ Mixing {len(dub_clips)} audio tracks...")
            final_audio = CompositeAudioClip(dub_clips).set_duration(original_duration)
            
            final_video = video.set_audio(final_audio)

            # --- ENFORCEMENT ---
            if resolution and final_video.h > resolution:
                print(f"📉 Downscaling to {resolution}p")
                final_video = final_video.resize(height=resolution)

            if watermark:
                 try:
                     print("💧 Applying Watermark...")
                     from moviepy.editor import TextClip, CompositeVideoClip
                     wm_txt = (TextClip("AI VIDEO SAAS", fontsize=int(final_video.h/30), color='white', font='Arial', method='label')
                               .set_opacity(0.5)
                               .set_position(('right', 'bottom'))
                               .set_duration(final_video.duration)
                               .margin(right=20, bottom=20, opacity=0))
                     final_video = CompositeVideoClip([final_video, wm_txt])
                 except Exception as e:
                     print(f"WM Error: {e}")
            
            # Write Files
            final_audio.write_audiofile(temp_audio_output, codec='mp3', logger=None)
            final_video.write_videofile(temp_output_path, codec="libx264", audio_codec="aac", logger=None)

            # Final Cleanup
            video.close()
            final_audio.close()
            for c in dub_clips:
                c.close()
            
            # Remove temp dir 
            try:
                shutil.rmtree(temp_dir)
            except: pass

            # --- Step 6: Handle Lip Sync (If Requested) ---
            if sync_mode == "lipsync":
                 print("👄 Lip-Sync Mode Detected in Service. Returning paths for upstream processing.")
                 # In a monolithic service we might call lipsync here, 
                 # but since main.py handles GCS uploads and Replicate calls, 
                 # we just return the paths and let main.py orchestrate the specialized sync.
                 return temp_output_path, temp_audio_output

            return temp_output_path, temp_audio_output

        except Exception as e:
            print(f"❌ Dubbing Critical Error: {e}")
            import traceback
            traceback.print_exc()
            return None, None
