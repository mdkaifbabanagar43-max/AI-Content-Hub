import asyncio
import os
import sys
import uuid
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from main import app
from core.auth import get_current_user
from core.models.blueprint import ProductionBlueprint, SceneBlueprint, DialogueLine, QualityStrategy, GenerationStrategy
from routers.video_cloner import production_blueprint_repo
from config import ModelRoutingConfig

def override_get_current_user():
    return "test_user_prod_tester"

app.dependency_overrides[get_current_user] = override_get_current_user

def run_test():
    print(f"VIDEO_DEFAULT: {ModelRoutingConfig.VIDEO_DEFAULT}")
    print(f"VOICE_DEFAULT: {ModelRoutingConfig.VOICE_DEFAULT}")
    print(f"QUALITY_REVIEW: {ModelRoutingConfig.QUALITY_REVIEW}")
    
    project_id = "proj_" + str(uuid.uuid4())[:8]
    bp_id = "bp_" + str(uuid.uuid4())[:8]
    
    bp = ProductionBlueprint(
        project_id=project_id,
        blueprint_id=bp_id,
        title="Astronaut Journey Test",
        concept="A brave astronaut exploring alien worlds",
        genre="Sci-Fi",
        target_duration_seconds=30.0,
        status="APPROVED",
        quality_strategy=QualityStrategy(max_retries=1),
        generation_strategy=GenerationStrategy(),
        source_clone_blueprint_id="cb_test",
        source_clone_blueprint_version=1
    )
    
    s1 = SceneBlueprint(
        scene_id="scn_test_1",
        scene_number=1,
        narrative_purpose="Hook",
        estimated_duration_seconds=5.0,
        visual_prompt="A cinematic wide shot of an astronaut walking on a red sandy alien planet",
        dialogue=[DialogueLine(
            text="The surface is unlike anything we've seen before.", 
            character_id="char_padlock", 
            voice_id="11_flash",
            emotion="Awed", 
            delivery_style="Calm", 
            estimated_duration_seconds=3.0
        )]
    )
    
    s2 = SceneBlueprint(
        scene_id="scn_test_2",
        scene_number=2,
        narrative_purpose="Discovery",
        estimated_duration_seconds=5.0,
        visual_prompt="Medium shot of the astronaut examining a glowing blue crystal on the ground",
        dialogue=[DialogueLine(
            text="This energy reading is off the charts.", 
            character_id="char_padlock", 
            voice_id="11_flash",
            emotion="Excited", 
            delivery_style="Urgent", 
            estimated_duration_seconds=3.0
        )]
    )
    
    s3 = SceneBlueprint(
        scene_id="scn_test_3",
        scene_number=3,
        narrative_purpose="Climax",
        estimated_duration_seconds=5.0,
        visual_prompt="Close up of the astronaut reaching out to touch the crystal, the glow reflecting on the visor",
        dialogue=[DialogueLine(
            text="It's reacting to my presence.", 
            character_id="char_padlock", 
            voice_id="11_flash",
            emotion="Awed", 
            delivery_style="Whisper", 
            estimated_duration_seconds=3.0
        )]
    )
    
    s4 = SceneBlueprint(
        scene_id="scn_test_4",
        scene_number=4,
        narrative_purpose="Resolution",
        estimated_duration_seconds=5.0,
        visual_prompt="A wide cinematic shot of the alien landscape, the astronaut standing triumphant",
        dialogue=[DialogueLine(
            text="This changes everything.", 
            character_id="char_padlock", 
            voice_id="11_flash",
            emotion="Confident", 
            delivery_style="Epic", 
            estimated_duration_seconds=3.0
        )]
    )
    
    bp.scenes.append(s1)
    bp.scenes.append(s2)
    bp.scenes.append(s3)
    bp.scenes.append(s4)
    
    production_blueprint_repo.save("test_user_prod_tester", bp)
    print(f"Saved Blueprint {bp_id} to DB.")
    
    print("Calling /generate endpoint...")
    
    with TestClient(app) as client:
        response = client.post(
            f"/projects/{project_id}/production-blueprints/{bp_id}/generate",
            headers={"Authorization": "Bearer fake"}
        )
        
        print(f"Response Status: {response.status_code}")
        print("Response Body:", json.dumps(response.json(), indent=2))
    
if __name__ == "__main__":
    run_test()
