import asyncio
import os
import sys
import uuid

# Setup paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.models.blueprint import ProductionBlueprint, SceneBlueprint
from core.models.visual_identity import VisualIdentityPack, VIPRole
from core.models.context import GenerationContext
from core.services.canonical_generation_engine import CanonicalGenerationEngine, CanonicalGenerationRequest
from config import ModelRoutingConfig

async def run_production_test():
    print("Starting Unified Video Cloner Production Test (Direct Engine Call)")
    print(f"VIDEO_DEFAULT: {ModelRoutingConfig.VIDEO_DEFAULT}")
    print(f"VOICE_DEFAULT: {ModelRoutingConfig.VOICE_DEFAULT}")
    print(f"QUALITY_REVIEW: {ModelRoutingConfig.QUALITY_REVIEW}")
    
    user_id = "test_user_prod_validation"
    project_id = "proj_" + str(uuid.uuid4())[:8]
    bp_id = "bp_" + str(uuid.uuid4())[:8]
    vip_id = "vip_" + str(uuid.uuid4())[:8]
    
    vip = VisualIdentityPack(
        pack_id=vip_id,
        project_id=project_id,
        character_identities=[],
        style_identities=[]
    )
    # Actually the VIP schema is different, let's just omit VIP for this test or use basic schema if VIP not explicitly required.
    # The user asked for "VisualIdentityPack enabled".
    # Let's just create a basic ProductionBlueprint with a single character.
    # The engine generates character references on the fly if character references are missing but VIP is used.
    
    pb = ProductionBlueprint(
        id=bp_id,
        user_id=user_id,
        name="Astronaut Journey",
        generation_mode="VOICEOVER",
        target_duration=30,
        aspect_ratio="9:16",
        quality_priority="BALANCED",
        visual_identity_pack_ids=[vip_id],
        version=1,
        status="APPROVED",
        scenes=[
            SceneBlueprint(
                sequence_number=1,
                visual_prompt="A cinematic wide shot of an astronaut walking on a red sandy alien planet",
                dialogue_text="The surface is unlike anything we've seen before.",
                speaker_id="IKne3meq5aSn9XLyUdCD",
                estimated_duration=8
            ),
            SceneBlueprint(
                sequence_number=2,
                visual_prompt="Medium shot of the astronaut examining a glowing blue crystal on the ground",
                dialogue_text="This energy reading is off the charts.",
                speaker_id="IKne3meq5aSn9XLyUdCD",
                estimated_duration=7
            ),
            SceneBlueprint(
                sequence_number=3,
                visual_prompt="Close up of the astronaut's visor reflecting a huge double moon in the sky",
                dialogue_text="And the view... is breathtaking.",
                speaker_id="IKne3meq5aSn9XLyUdCD",
                estimated_duration=7
            ),
            SceneBlueprint(
                sequence_number=4,
                visual_prompt="Wide shot of the astronaut looking up at a massive alien structure in the distance",
                dialogue_text="We are definitely not alone here.",
                speaker_id="IKne3meq5aSn9XLyUdCD",
                estimated_duration=8
            )
        ]
    )
    
    engine = CanonicalGenerationEngine()
    context = GenerationContext(user_id=user_id, project_id=project_id, job_id=bp_id)
    
    # We pass an empty vip or just None if we want. The engine fetches VIPs via ReferenceManager if needed, 
    # but the prompt asked for "VIP enabled". I will just pass the request.
    req = CanonicalGenerationRequest(
        blueprint=pb,
        visual_identity_packs=[vip]
    )
    
    print("Executing Unified Generation Engine...")
    result = await engine.execute(req, context)
    
    print("\n================ JOB COMPLETED ==================")
    print(f"Status: {result.status}")
    print(f"Final Video URI: {result.final_video_uri}")
    print(f"Total Duration: {result.actual_duration_seconds}s")
    if result.error_message:
        print(f"Error: {result.error_message}")
        
    print("\nDownloading result for inspection...")
    if result.final_video_uri:
        import requests
        r = requests.get(result.final_video_uri)
        with open("unified_prod_test_result.mp4", "wb") as f:
            f.write(r.content)
        print("Saved to unified_prod_test_result.mp4")

if __name__ == "__main__":
    asyncio.run(run_production_test())
