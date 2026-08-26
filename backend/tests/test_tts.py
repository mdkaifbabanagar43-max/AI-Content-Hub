
import requests
import time

url = "http://127.0.0.1:8000/generate-voiceover"
payload = {
    "text": "Hello! This is a test of the Google Journey voice integration. If you can hear this, the system is working perfectly.",
    "voice_name": "en-US-Journey-D"
}

print(f"🎤 Testing TTS Endpoint: {url}")
print(f"Standard Journey Voice: en-US-Journey-D")

try:
    start = time.time()
    response = requests.post(url, json=payload)
    end = time.time()
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! ({end-start:.2f}s)")
        print(f"🔗 Audio URL: {data.get('audio_url')}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"❌ Error: {e}")
