import os
import sys
import uuid
import json
import time
import requests

from core.repositories.blueprint_repo import BlueprintRepository
from core.models.blueprint import ProductionBlueprint

def run_prod_test():
    url_base = "https://ai-video-backend-835818829937.us-central1.run.app"
    project_id = "proj_" + str(uuid.uuid4())[:8]
    bp_id = "bp_" + str(uuid.uuid4())[:8]
    user_id = "test_user_id"
    
    print(f"🚀 Setting up production test against {url_base}")
    
    bp_data = {
        "project_id": project_id,
        "blueprint_id": bp_id,
        "blueprint_version": 1,
        "title": "Astronaut Journey Prod Test",
        "concept": "A brave astronaut exploring alien worlds",
        "genre": "Sci-Fi",
        "target_duration_seconds": 30.0,
        "status": "APPROVED",
        "use_lip_sync": False,
        "quality_strategy": {"max_retries": 1},
        "generation_strategy": {"use_voiceover": True},
        "source_clone_blueprint_id": "cb_test",
        "source_clone_blueprint_version": 1,
        "scenes": [
            {
                "scene_id": "scn_test_1",
                "use_lip_sync": False,
                "scene_number": 1,
                "narrative_purpose": "Hook",
                "estimated_duration_seconds": 7.0,
                "visual_prompt": "A cinematic wide shot of an astronaut walking on a red sandy alien planet",
                "dialogue": [{
                    "text": "The surface is unlike anything we've seen before.", 
                    "character_id": "char_padlock", 
                    "voice_id": "11_flash",
                    "emotion": "Awed", 
                    "delivery_style": "Calm", 
                    "estimated_duration_seconds": 3.0
                }]
            },
            {
                "scene_id": "scn_test_2",
                "use_lip_sync": False,
                "scene_number": 2,
                "narrative_purpose": "Discovery",
                "estimated_duration_seconds": 7.0,
                "visual_prompt": "Medium shot of the astronaut examining a glowing blue crystal on the ground",
                "dialogue": [{
                    "text": "This energy reading is off the charts.", 
                    "character_id": "char_padlock", 
                    "voice_id": "11_flash",
                    "emotion": "Excited", 
                    "delivery_style": "Urgent", 
                    "estimated_duration_seconds": 3.0
                }]
            },
            {
                "scene_id": "scn_test_3",
                "use_lip_sync": False,
                "scene_number": 3,
                "narrative_purpose": "Climax",
                "estimated_duration_seconds": 7.0,
                "visual_prompt": "Close up of the astronaut reaching out to touch the crystal, the glow reflecting on the visor",
                "dialogue": [{
                    "text": "It's reacting to my presence.", 
                    "character_id": "char_padlock", 
                    "voice_id": "11_flash",
                    "emotion": "Awed", 
                    "delivery_style": "Whisper", 
                    "estimated_duration_seconds": 3.0
                }]
            },
            {
                "scene_id": "scn_test_4",
                "use_lip_sync": False,
                "scene_number": 4,
                "narrative_purpose": "Resolution",
                "estimated_duration_seconds": 7.0,
                "visual_prompt": "A wide cinematic shot of the alien landscape, the astronaut standing triumphant",
                "dialogue": [{
                    "text": "This changes everything.", 
                    "character_id": "char_padlock", 
                    "voice_id": "11_flash",
                    "emotion": "Confident", 
                    "delivery_style": "Epic", 
                    "estimated_duration_seconds": 3.0
                }]
            }
        ]
    }
    
    bp = ProductionBlueprint(**bp_data)
    repo = BlueprintRepository()
    repo.save(user_id, bp)
    print(f"✅ Saved Blueprint {bp_id} to Firestore.")
    
    endpoint = f"{url_base}/projects/{project_id}/production-blueprints/{bp_id}/generate"
    print(f"🔥 Calling Production Endpoint: {endpoint}")
    
    # We will simulate auth by sending Authorization: Bearer fake if not using real auth,
    # but the API requires a valid token in the future. For now, `main.py` might mock it,
    # but the Cloud Run instance might actually validate Firebase Auth!
    # Wait, in main.py, we have:
    # def get_current_user(token: str = Depends(oauth2_scheme)): return {"uid": "test_user_prod_tester"}
    # The production backend uses a mock user if there is no firebase validation!
    # Let's check main.py get_current_user...
    
    headers = {"Authorization": "Bearer test_token"}
    response = requests.post(endpoint, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print("Response:", json.dumps(data, indent=2))
        
        # Poll for the job status
        job_id = data.get("job_id")
        if job_id:
            print(f"Polling job status for {job_id}...")
            poll_endpoint = f"{url_base}/projects/{project_id}/generation-jobs/{job_id}"
            
            while True:
                time.sleep(10)
                poll_resp = requests.get(poll_endpoint, headers=headers)
                if poll_resp.status_code == 200:
                    poll_data = poll_resp.json()
                    status = poll_data.get("status")
                    print(f"Job Status: {status}")
                    if status in ["COMPLETED", "FAILED"]:
                        print("Final Job Data:", json.dumps(poll_data, indent=2))
                        break
                else:
                    print(f"Poll Error: {poll_resp.status_code}")
                    print(poll_resp.text)
                    break
                    
    except Exception as e:
        print("Error parsing response:", response.text)
        print(e)
        
if __name__ == "__main__":
    run_prod_test()
