import replicate
import os

# The Wav2Lip Model (Standard Version)
MODEL_VERSION = "cjwbw/wav2lip:d15582f187a55c2f88301138a0f9687c71e220a214e6727271448b2611842065"

# USER PROVIDED KEY (Injected for Immediate Use)
DEFAULT_TOKEN = "r8_EjxpQxefnA1w4o2McWeaE0mRWgw2E9Z4D6B8Y"

def sync_lips(face_video_url: str, audio_url: str) -> str:
    """
    Sends video and audio to Replicate GPU to sync lips.
    Returns: URL of the synced video.
    """
    # Try env first, fall back to injected key
    api_token = os.getenv("REPLICATE_API_TOKEN", DEFAULT_TOKEN)
    
    if not api_token:
        print("⚠️ Missing REPLICATE_API_TOKEN. Skipping Lip Sync.")
        return face_video_url  # Return original video if no key
        
    # Ensure env var is set for the library
    os.environ["REPLICATE_API_TOKEN"] = api_token
    
    print("🚀 Sending to Replicate for Lip Syncing...")
    try:
        output = replicate.run(
            MODEL_VERSION,
            input={
                "face": face_video_url,
                "audio": audio_url,
                "pads": "0 10 0 0",  # Padding to prevent chin clipping
                "smooth": True
            }
        )
        print(f"✅ Lip Sync Complete: {output}")
        # Output is usually a URI or list. Handle generic return type.
        if isinstance(output, str):
            return output
        return str(output)
        
    except Exception as e:
        print(f"🔥 Lip Sync Failed: {e}")
        return face_video_url  # Fallback to original on failure
