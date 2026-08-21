import asyncio
import os
import sys

from core.services.video_cloner_orchestrator import VideoClonerOrchestrator
from core.repositories.video_cloner_repository import VideoClonerRepository
from models.video_cloner_models import CloneBlueprint, SceneBlueprint, VisualIdentityPack
from config import ModelRoutingConfig

async def run_production_test():
    print("Starting Unified Video Cloner Production Test")
    print(f"VIDEO_DEFAULT: {ModelRoutingConfig.VIDEO_DEFAULT}")
    print(f"VOICE_DEFAULT: {ModelRoutingConfig.VOICE_DEFAULT}")
    print(f"QUALITY_REVIEW: {ModelRoutingConfig.QUALITY_REVIEW}")
    
    repo = VideoClonerRepository("test-project-123")
    orchestrator = VideoClonerOrchestrator(repo)
    
    vip = VisualIdentityPack(
        id="vip-prod-test-01",
        user_id="user_prod_tester",
        name="Astronaut Explorer",
        description="A brave astronaut exploring alien worlds",
        reference_image_uri="https://storage.googleapis.com/shortcutai-backend-assets/astronaut.jpg",
        type="CHARACTER"
    )
    
    blueprint = CloneBlueprint(
        id="cb-prod-test-01",
        user_id="user_prod_tester",
        name="Astronaut Journey",
        generation_mode="VOICEOVER",
        target_duration=30,
        aspect_ratio="9:16",
        quality_priority="BALANCED",
        visual_identity_pack_ids=["vip-prod-test-01"],
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
    
    # Normally we convert CloneBlueprint to ProductionBlueprint, but VideoClonerOrchestrator takes ProductionBlueprint
    # Let's mock a ProductionBlueprint by extending CloneBlueprint properties:
    from models.video_cloner_models import ProductionBlueprint
    prod_bp = ProductionBlueprint(
        **blueprint.model_dump(),
        version=1,
        status="APPROVED"
    )
    
    # We must provide the VIP context since the Orchestrator expects VIPs to be fetched or provided
    # The Orchestrator normally fetches VIPs from DB if they exist. We need to save the VIP first.
    repo.save_visual_identity_pack(vip)
    
    print("Executing Unified Generation...")
    job = await orchestrator.execute_unified_generation(prod_bp)
    
    print("\n================ JOB COMPLETED ==================")
    print(f"Status: {job.status}")
    print(f"Final Video URI: {job.final_video_uri}")
    print(f"Total Duration: {job.final_duration_seconds}s")
    if job.error_message:
        print(f"Error: {job.error_message}")
        
    print("\nVisual Identity Packs used:")
    for vip_id in prod_bp.visual_identity_pack_ids:
        print(f" - {vip_id}")
        
    print("\nDownloading result for inspection...")
    if job.final_video_uri:
        import requests
        r = requests.get(job.final_video_uri)
        with open("unified_prod_test_result.mp4", "wb") as f:
            f.write(r.content)
        print("Saved to unified_prod_test_result.mp4")

if __name__ == "__main__":
    asyncio.run(run_production_test())
