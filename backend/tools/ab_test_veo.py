import os
import sys
import json
import time
import argparse
from typing import Dict, Any

# Ensure backend path is in sys.path so we can import services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import ModelRoutingConfig, TEMP_DIR
from services.veo_service import generate_video_with_veo
from core.services.quality_reviewer import QualityReviewer
from core.telemetry import log_model_telemetry

def run_ab_test(prompt: str, reference_image_uri: str, target_duration: int) -> Dict[str, Any]:
    print("========================================")
    print("   VEO 2.0 vs VEO 3.1 FAST A/B TEST")
    print("========================================")
    
    models = {
        "A": ModelRoutingConfig.VIDEO_DEFAULT,  # veo-2.0-generate-001
        "B": ModelRoutingConfig.VIDEO_FAST      # veo-3.1-fast-generate-001
    }
    
    results = {}
    reviewer = QualityReviewer()
    
    for variant, model_id in models.items():
        print(f"\n--- Running Variant {variant}: {model_id} ---")
        
        start_time = time.time()
        retries = 0
        max_retries = 1
        video_path = None
        
        while retries <= max_retries:
            try:
                print(f"Generating with {model_id} (Attempt {retries + 1})...")
                log_model_telemetry(
                    task="AB_TEST_GENERATION",
                    provider="Google Vertex AI",
                    model=model_id,
                    reason=f"A/B Test Variant {variant}",
                    retry_count=retries
                )
                
                raw_bytes = generate_video_with_veo(
                    prompt=prompt,
                    model_id=model_id,
                    target_duration=target_duration,
                    reference_image_uri=reference_image_uri
                )
                
                if not raw_bytes:
                    raise Exception("Generated video bytes were empty.")
                
                video_path = os.path.join(TEMP_DIR, f"ab_test_variant_{variant}_{model_id}.mp4")
                if isinstance(raw_bytes, bytes):
                    with open(video_path, "wb") as f:
                        f.write(raw_bytes)
                else:
                    video_path = raw_bytes
                
                break # Success
            except Exception as e:
                print(f"Error during generation: {e}")
                retries += 1
                if retries > max_retries:
                    print("Max retries exceeded.")
                    break
        
        latency = time.time() - start_time
        
        if not video_path:
            results[variant] = {
                "model": model_id,
                "status": "FAILED",
                "latency": latency,
                "retries": retries
            }
            continue
            
        print(f"Video saved to {video_path}")
        print("Running QualityReviewer...")
        review = reviewer.review_video(video_path, prompt, "BALANCED")
        
        # Estimate cost (Dummy calculation for now, adjust based on actual limits)
        cost_per_chunk_2_0 = 0.20
        cost_per_chunk_3_1_fast = 0.25 # Assume slightly more expensive or cheaper
        
        chunks = max(1, (target_duration + 7) // 8)
        cost = chunks * (cost_per_chunk_2_0 if "2.0" in model_id else cost_per_chunk_3_1_fast)
        
        results[variant] = {
            "model": model_id,
            "status": "COMPLETED",
            "video_path": video_path,
            "latency": latency,
            "retries": retries,
            "estimated_cost": cost,
            "review": review.model_dump() if hasattr(review, "model_dump") else review
        }
        
        log_model_telemetry(
            task="AB_TEST_REVIEW",
            provider="Google Gemini",
            model=ModelRoutingConfig.QUALITY_REVIEWER_DEFAULT,
            reason=f"Scoring variant {variant}",
            cost=cost,
            latency=latency,
            quality_score=getattr(review, "overall", 0.0),
            retry_count=retries
        )

    print("\n========================================")
    print("               RESULTS")
    print("========================================")
    print(json.dumps(results, indent=2))
    
    output_json = os.path.join(TEMP_DIR, "ab_test_results.json")
    with open(output_json, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_json}")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run A/B test between Veo 2.0 and Veo 3.1 Fast")
    parser.add_argument("--prompt", type=str, required=True, help="Text prompt for the video")
    parser.add_argument("--reference", type=str, required=True, help="URI/Path for the character reference image")
    parser.add_argument("--duration", type=int, default=8, help="Target duration in seconds")
    
    args = parser.parse_args()
    
    run_ab_test(args.prompt, args.reference, args.duration)
