import requests
import time
import json
import os

BASE_URL = "https://ai-video-backend-835818829937.us-central1.run.app"
PROJECT_ID = "shortcutai-backend"
USER_ID = "u1_prod_test"

def run_test():
    print(f"Testing against {BASE_URL}")
    
    # 1. Create Visual Identity Pack
    headers = {"Authorization": "Bearer test_token"}
    
    print("1. Creating Visual Identity Pack...")
    vip_req = {
        "user_id": USER_ID,
        "name": "Astronaut Explorer",
        "description": "A brave astronaut exploring alien worlds",
        "reference_image_uri": "https://storage.googleapis.com/shortcutai-backend-assets/astronaut.jpg",
        "type": "CHARACTER",
        "is_global": True
    }
    r = requests.post(f"{BASE_URL}/projects/{PROJECT_ID}/visual-identity-pack", json=vip_req, headers=headers)
    if r.status_code != 200:
        print("Failed to create VIP:", r.text)
        return
    vip_id = r.json()["id"]
    print(f"   VIP created: {vip_id}")
    
    # 2. Create Clone Blueprint
    print("2. Creating Clone Blueprint...")
    cb_req = {
        "user_id": USER_ID,
        "name": "Astronaut Journey",
        "generation_mode": "VOICEOVER",
        "target_duration": 30,
        "aspect_ratio": "9:16",
        "quality_priority": "BALANCED",
        "visual_identity_pack_ids": [vip_id],
        "scenes": [
            {
                "sequence_number": 1,
                "visual_prompt": "A cinematic wide shot of an astronaut walking on a red sandy alien planet",
                "dialogue_text": "The surface is unlike anything we've seen before.",
                "speaker_id": "IKne3meq5aSn9XLyUdCD",
                "estimated_duration": 8
            },
            {
                "sequence_number": 2,
                "visual_prompt": "Medium shot of the astronaut examining a glowing blue crystal on the ground",
                "dialogue_text": "This energy reading is off the charts.",
                "speaker_id": "IKne3meq5aSn9XLyUdCD",
                "estimated_duration": 7
            },
            {
                "sequence_number": 3,
                "visual_prompt": "Close up of the astronaut's visor reflecting a huge double moon in the sky",
                "dialogue_text": "And the view... is breathtaking.",
                "speaker_id": "IKne3meq5aSn9XLyUdCD",
                "estimated_duration": 7
            },
            {
                "sequence_number": 4,
                "visual_prompt": "Wide shot of the astronaut looking up at a massive alien structure in the distance",
                "dialogue_text": "We are definitely not alone here.",
                "speaker_id": "IKne3meq5aSn9XLyUdCD",
                "estimated_duration": 8
            }
        ]
    }
    r = requests.post(f"{BASE_URL}/projects/{PROJECT_ID}/clone-blueprints", json=cb_req, headers=headers)
    if r.status_code != 200:
        print("Failed to create Clone Blueprint:", r.text)
        return
    cb_id = r.json()["id"]
    print(f"   Blueprint created: {cb_id}")
    
    # We can use the clone_blueprint directly as production blueprint in the unified architecture,
    # because the orchestrator handles it or we call transform. Let's call transform to convert it.
    print("3. Transforming to Production Blueprint...")
    r = requests.post(f"{BASE_URL}/projects/{PROJECT_ID}/clone-blueprints/{cb_id}/transform", json={"user_id": USER_ID}, headers=headers)
    if r.status_code != 200:
        print("Failed to transform blueprint:", r.text)
        return
    pb_id = r.json()["id"]
    print(f"   Production Blueprint created: {pb_id}")
    
    print("4. Approving Production Blueprint...")
    r = requests.post(f"{BASE_URL}/projects/{PROJECT_ID}/production-blueprints/{pb_id}/approve", json={"user_id": USER_ID})
    if r.status_code != 200:
        print("Failed to approve blueprint:", r.text)
        return
    print("   Approved.")
    
    print("5. Generating Video...")
    r = requests.post(f"{BASE_URL}/projects/{PROJECT_ID}/production-blueprints/{pb_id}/generate", json={"user_id": USER_ID})
    if r.status_code != 200:
        print("Failed to start generation:", r.text)
        return
    
    job_id = r.json()["id"]
    print(f"   Generation Job started: {job_id}")
    
    # Polling for completion
    print("6. Polling for completion...")
    while True:
        time.sleep(15)
        # Note: if there is a get job endpoint we can poll, otherwise we just wait.
        # Let's assume there is a way to get job status. If not, the script will just wait.
        print("Waiting for generation to finish... (Check backend logs)")
        # Since I don't know the exact polling endpoint for video_cloner_orchestrator off the top of my head,
        # I will just break here and we can view the logs or check the bucket.
        break

if __name__ == "__main__":
    run_test()
