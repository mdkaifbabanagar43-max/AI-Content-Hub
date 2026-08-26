
import requests

url = "http://127.0.0.1:8000/produce-video-assets"
payload = {
    "title": "Debug AI",
    "hook": "Is this working?"
}

try:
    print(f"Sending request to {url}...")
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
