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
    def translate_text(self, text, target_lang, source_lang=None):
        """
        Translate text to target language for dubbing.
        Args:
            text: The text to translate
            target_lang: Target language code (e.g., 'es', 'hi', 'fr')
            source_lang: Optional source language detected by Whisper
        """
        print(f"🌍 Translating to: {target_lang} (from: {source_lang or 'auto'})")
        if not text or not text.strip():
            return ""
            
        try:
            from services.ai_service import generate_text
            
            # ENHANCED PROMPT: Strict single-language output
            source_context = f"The original text is in {source_lang}." if source_lang else ""
            
            prompt = f"""
TASK: Translate the following text to {target_lang} for professional video dubbing.

INPUT TEXT: "{text}"
{source_context}

CRITICAL RULES (MUST FOLLOW):
1. Translate EVERY word to {target_lang}. Do NOT leave ANY word in the original language.
2. Do NOT mix languages. The output must be 100% in {target_lang}.
3. Use natural, conversational phrasing suitable for spoken audio.
4. Match the approximate length and tone of the original.
5. For Hindi: Use natural Hindi in Devanagari script. Avoid "Hinglish" mixing.
6. For any language: Use the standard/formal version, not slang or mixed dialect.

OUTPUT: Return ONLY the translated text in {target_lang}. No explanations, no notes.
"""
            
            response_text = generate_text(prompt)
            translated = response_text.strip()
            
            # Remove any quotes that might wrap the response
            if translated.startswith('"') and translated.endswith('"'):
                translated = translated[1:-1]
            if translated.startswith("'") and translated.endswith("'"):
                translated = translated[1:-1]
                
            return translated

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
        """Transcribe video and return segments with detected language and DIARIZATION (Mocked)."""
        model = get_whisper_model()
        print(f"👂 Transcribing & Diarizing: {video_path}")
        result = model.transcribe(video_path, word_timestamps=False) 
        detected_lang = result.get("language", "en")
        print(f"🗣️ Detected source language: {detected_lang}")
        
        # --- MOCK DIARIZATION ARCHITECTURE ---
        # Simulate PyAnnote speaker diarization
        segments = result["segments"]
        current_speaker = "SPEAKER_00"
        for i, seg in enumerate(segments):
            # Switch speaker randomly (30% chance) or keep same
            import random
            if i > 0 and random.random() > 0.7:
                current_speaker = "SPEAKER_01" if current_speaker == "SPEAKER_00" else "SPEAKER_00"
            seg['speaker'] = current_speaker
            
        print(f"👥 Diarization complete: Found {len(set(s['speaker'] for s in segments))} speakers.")
        return segments, detected_lang

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
            segments, detected_source_lang = self.transcribe_video_segments(video_path) 
            print(f"📋 Detected {len(segments)} segments in '{detected_source_lang}'")
            
            tts = GoogleTTSClient()
            dub_clips = []
            
            if background_clip:
                dub_clips.append(background_clip)

            # --- Step 4: Generate Dub Audio with SYNC & DIARIZATION ---
            # Map detected speakers to voice models
            voice_map = {
                "SPEAKER_00": target_voice_name,
                "SPEAKER_01": "en-US-Journey-F" if target_voice_name == "en-US-Journey-D" else "en-US-Journey-D" 
            }
            
            for i, seg in enumerate(segments):
                start = seg['start']
                end = seg['end']
                target_duration = end - start
                speaker = seg.get('speaker', 'SPEAKER_00')
                assigned_voice = voice_map.get(speaker, target_voice_name)
                
                text = seg['text']
                # Pass source language for better translation context
                translated = self.translate_text(text, target_lang_code, source_lang=detected_source_lang)
                
                if translated:
                    try:
                        # Generate TTS
                        print(f"📝 Segment {i+1} [{speaker}]: Using voice '{assigned_voice}' for text: '{translated[:50]}...'")
                        tts_file = tts.generate_audio(translated, assigned_voice)
                        clip = AudioFileClip(tts_file)
                        
                        # Position clip at segment start time
                        clip = clip.set_start(start)
                        dub_clips.append(clip)
                        print(f"   ✅ Segment {i+1}: TTS duration={clip.duration:.2f}s, Target={target_duration:.2f}s")
                    except Exception as e:
                        print(f"   ❌ TTS/Sync Failed: {e}")

            # --- Step 5: Mix & Merge ---
            print(f"🎚️ Mixing {len(dub_clips)} audio tracks...")
            final_audio = CompositeAudioClip(dub_clips).set_duration(original_duration)
            # MoviePy 1.0.3 fix: Explicitly set fps on CompositeAudioClip
            if not hasattr(final_audio, 'fps') or final_audio.fps is None:
                final_audio.fps = 44100  # Standard audio sample rate
            
            final_video = video.set_audio(final_audio)

            # --- ENFORCEMENT ---
            if resolution and final_video.h > resolution:
                print(f"📉 Downscaling to {resolution}p")
                final_video = final_video.resize(height=resolution)

            if watermark:
                 try:
                    print("💧 Applying ShortcutAI Watermark (Dubbing)")
                    from moviepy.editor import TextClip, CompositeVideoClip
                    wm_txt = (TextClip("ShortcutAI", fontsize=int(final_video.h/30), color='white', font='Arial', method='label')
                              .set_opacity(0.40)
                              .set_position(('right', 'bottom'))
                              .set_duration(final_video.duration)
                              .margin(right=20, bottom=20, opacity=0))
                    final_video = CompositeVideoClip([final_video, wm_txt])
                 except Exception as e:
                     print(f"WM Error: {e}")
            
            # Write Files
            final_audio.write_audiofile(temp_audio_output, codec='mp3', logger=None)
            final_video.write_videofile(temp_output_path, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4, logger=None)

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
