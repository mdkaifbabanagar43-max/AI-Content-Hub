import os
from google import genai
from google.genai import types

def test():
    client = genai.Client(vertexai=True, project="shortcutai-backend", location="us-central1")
    print("Sending Veo 2.0 request...")
    try:
        operation = client.models.generate_videos(
            model="veo-2.0-generate-001",
            prompt="A cinematic wide shot of a red car",
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                person_generation="ALLOW_ADULT",
                aspect_ratio="16:9"
            )
        )
        print("Success!", operation)
    except Exception as e:
        print("Error with veo-2.0-generate-001:", e)
        
    print("\nSending Veo 3.1 request...")
    try:
        operation = client.models.generate_videos(
            model="veo-3.1-generate-001",
            prompt="A cinematic wide shot of a red car",
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                person_generation="ALLOW_ADULT",
                aspect_ratio="16:9"
            )
        )
        print("Success!", operation)
    except Exception as e:
        print("Error with veo-3.1-generate-001:", e)

if __name__ == "__main__":
    test()
