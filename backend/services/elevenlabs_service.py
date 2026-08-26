import os
import requests
import tempfile
import uuid

from typing import Union, List, Dict, Any

from config import ModelRoutingConfig

VOICE_MAP = {
    "Male": "pNInz6obpgDQGcFmaJgB",   # Indian Male placeholder
    "Female": "EXAVITQu4vr4xnSDxMaL"  # Indian Female placeholder
}

def _generate_single_tts(text: str, voice_id: str, is_premium: bool = False) -> str:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY is not set.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }

    model_id = ModelRoutingConfig.VOICE_PREMIUM if is_premium else ModelRoutingConfig.VOICE_DEFAULT

    data = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.35,
            "similarity_boost": 0.75,
            "style": 0.20
        }
    }

    response = requests.post(url, json=data, headers=headers)
    if not response.ok:
        raise Exception(f"ElevenLabs API Error: {response.text}")

    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, f"elevenlabs_{uuid.uuid4().hex}.mp3")

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path

def generate_voiceover(script: Union[str, List[Dict[str, Any]]], voice_id: str = "IKne3meq5aSn9XLyUdCD", is_premium: bool = False) -> str:
    """
    Generate voiceover using ElevenLabs Multilingual v2 API.
    Handles single string or array of DialogueLines for multi-character conversations.
    Returns the path to the master MP3 file.
    """
    if isinstance(script, str):
        # Single string fallback
        try:
            # Check if it's a JSON string of a list
            import json
            parsed = json.loads(script)
            if isinstance(parsed, list):
                script = parsed
        except:
            pass

    if isinstance(script, str):
        return _generate_single_tts(script, voice_id, is_premium)
        
    # It's a list of DialogueLines
    from moviepy.editor import AudioFileClip, concatenate_audioclips
    
    audio_clips = []
    temp_files = []
    timings = []
    current_time = 0.0
    
    for line in script:
        voice_label = line.get("voice_label", "Male")
        text = line.get("text", "")
        meme = line.get("meme_overlay", "none")
        # Only generate TTS if there is text
        if not text.strip():
            continue
            
        vid = VOICE_MAP.get(voice_label, voice_id)
        print(f"[ElevenLabs] Generating TTS for {voice_label}: {text[:30]}...")
        
        mp3_path = _generate_single_tts(text, vid, is_premium)
        temp_files.append(mp3_path)
        clip = AudioFileClip(mp3_path)
        audio_clips.append(clip)
        
        # Track timing for meme overlays
        duration = clip.duration
        timings.append({
            "start": current_time,
            "end": current_time + duration,
            "meme_overlay": meme
        })
        current_time += duration
        
    if not audio_clips:
        raise ValueError("Script array was empty or contained no text.")
        
    print(f"[ElevenLabs] Concatenating {len(audio_clips)} voiceover tracks...")
    master_audio = concatenate_audioclips(audio_clips)
    
    master_path = os.path.join(tempfile.gettempdir(), f"master_voice_{uuid.uuid4().hex}.mp3")
    master_audio.write_audiofile(master_path, logger=None)
    
    # Cleanup memory and individual clips
    for clip in audio_clips:
        clip.close()
    master_audio.close()
    
    # Optional: Delete intermediate mp3s to save tmpfs memory
    for f in temp_files:
        if os.path.exists(f):
            os.remove(f)
            
    return master_path, timings
