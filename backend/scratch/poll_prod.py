import requests
import time
import json

def poll():
    url = "https://ai-video-backend-835818829937.us-central1.run.app/projects/proj_6e14aead/blueprints/bp_875d0140"
    headers = {"Authorization": "Bearer test_token"}
    
    print("Polling blueprint status...")
    for _ in range(20):
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status")
            print(f"Status: {status}")
            if status in ["COMPLETED", "FAILED"]:
                print("Final Data:")
                # just print the top-level keys and status, and the final video url if present
                print(f"Final Video URL: {data.get('final_video_url')}")
                if status == "FAILED":
                    print("Error message: ", data.get("error_message", "No error message field?"))
                break
        else:
            print(f"Error {resp.status_code}: {resp.text}")
        time.sleep(10)

if __name__ == "__main__":
    poll()
