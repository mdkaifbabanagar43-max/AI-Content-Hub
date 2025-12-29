from google.cloud import texttospeech
from google.oauth2 import service_account
import uuid
import os

class TTSClient:
    def __init__(self):
        # Flexible Credential Loading
        base_dir = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(base_dir, "service-account.json")
        
        if os.path.exists(key_path):
            self.credentials = service_account.Credentials.from_service_account_file(key_path)
            print(f"TTS: Loaded credentials from {key_path}")
        else:
            print(f"TTS: {key_path} not found. Using Default Credentials (Cloud Run)...")
            self.credentials = None 

    def generate_audio(self, text, voice_name="en-US-Journey-D"):
        """
        Generates audio using Google Cloud TTS (Journey Models).
        Returns the path to the temporary MP3 file.
        """
        try:
            # 1. Initialize Client
            if self.credentials:
                client = texttospeech.TextToSpeechClient(credentials=self.credentials)
            else:
                client = texttospeech.TextToSpeechClient()

            # 2. Configure Input
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # 3. Configure Voice
            # FIX: Dynamically extract language code from the voice ID (e.g. "hi-IN-Neural2-B" -> "hi-IN")
            computed_lang = "-".join(voice_name.split("-")[:2]) # "en-US", "hi-IN", "es-ES"
            
            voice = texttospeech.VoiceSelectionParams(
                language_code=computed_lang,
                name=voice_name 
            )

            # 4. Configure Audio (MP3)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            # 5. Execute Request
            print(f"TTS: Generating Journey Audio ({voice_name})...")
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            # 6. Save File
            unique_id = uuid.uuid4()
            output_filename = f"temp_journey_{unique_id}.mp3"
            output_path = os.path.join(os.getcwd(), output_filename)

            with open(output_path, "wb") as out:
                out.write(response.audio_content)
                print(f"TTS Success: {output_path}")

            return output_path

        except Exception as e:
            print(f"Google TTS Error: {e}")
            raise e

# Backward Compatibility
GoogleTTSClient = TTSClient
