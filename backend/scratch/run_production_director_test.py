import os
import sys
import uuid
import json
import asyncio

# Ensure correct encodings for logging
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from core.repositories.blueprint_repo import BlueprintRepository
from core.models.blueprint import ProductionBlueprint
from routers.video_cloner import run_production_job

async def test_run():
    project_id = "proj_" + str(uuid.uuid4())[:8]
    bp_id = "bp_" + str(uuid.uuid4())[:8]
    user_id = "test_user_prod_tester"
    
    bp_data = {
        "project_id": project_id,
        "blueprint_id": bp_id,
        "blueprint_version": 1,
        "title": "Astronaut Journey Prod Test",
        "concept": "A brave astronaut exploring alien worlds",
        "genre": "Sci-Fi",
        "target_duration_seconds": 30.0,
        "status": "APPROVED",
        "quality_strategy": {"max_retries": 1},
        "generation_strategy": {"use_voiceover": True},
        "source_clone_blueprint_id": "cb_test",
        "source_clone_blueprint_version": 1,
        "scenes": [
            {
                "scene_id": "scn_test_1",
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
    print(f"✅ Saved Blueprint {bp_id} to DB.")
    
    print("🚀 Calling run_production_job synchronously...")
    await run_production_job(user_id, project_id, bp_id)
    print("✅ Job Complete!")

if __name__ == "__main__":
    asyncio.run(test_run())
