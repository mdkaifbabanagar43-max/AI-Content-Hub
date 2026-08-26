import os
import sys
import time
import uuid
import requests

from config import ModelRoutingConfig

CANARY_URL = "https://canary-model-remediation---ai-video-backend-sfxkkeql7q-uc.a.run.app"
TEST_VIDEO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "videos", "WhatsApp Video 2026-08-17 at 11.36.14 PM.mp4"))
FIREBASE_API_KEY = "AIzaSyDL4FHsHBa1XE9aUt1h5VyL4iogNOLvvUg"

def get_auth_token_for_test_user():
    """Generates a temporary test user and returns an ID token."""
    email = f"canary_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    
    for attempt in range(5):
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.ok:
                data = resp.json()
                return data["idToken"], data["localId"]
            time.sleep(2)
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2)
            
    raise RuntimeError(f"Auth signup failed: {resp.text}")

def safe_post(url, **kwargs):
    """Robust POST request with network glitch retries."""
    for attempt in range(4):
        try:
            return requests.post(url, **kwargs)
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            if attempt == 3:
                raise
            print(f"Network glitch on {url} (attempt {attempt+1}/4): {e}. Retrying in 3s...", flush=True)
            time.sleep(3)

def run_canary_validation():
    print("=" * 70, flush=True)
    print("STARTING CANARY VALIDATION AGAINST REVISION ai-video-backend-00157-paf", flush=True)
    print(f"Canary URL: {CANARY_URL}", flush=True)
    print(f"Test Video: {TEST_VIDEO_PATH}", flush=True)
    print("=" * 70, flush=True)

    assert os.path.exists(TEST_VIDEO_PATH), f"Fixture video not found: {TEST_VIDEO_PATH}"
    
    token, user_id = get_auth_token_for_test_user()
    project_id = f"canary_proj_{uuid.uuid4().hex[:8]}"
    print(f"Authenticated as Test User: {user_id}", flush=True)
    print(f"Project ID: {project_id}", flush=True)
    headers = {"Authorization": f"Bearer {token}"}

    telemetry = []

    # -------------------------------------------------------------
    # STEP 1: Upload Source Video & Run Source Analysis
    # -------------------------------------------------------------
    print("\n[STEP 1] Testing Source Analysis...", flush=True)
    with open(TEST_VIDEO_PATH, "rb") as f:
        upload_resp = safe_post(
            f"{CANARY_URL}/projects/{project_id}/source-videos",
            headers=headers,
            files={"file": ("test_video.mp4", f, "video/mp4")}
        )
    if not upload_resp.ok:
        raise RuntimeError(f"Upload failed ({upload_resp.status_code}): {upload_resp.text}")
    source_record = upload_resp.json()
    source_video_id = source_record["source_video_id"]
    print(f"Source video uploaded successfully. ID: {source_video_id}", flush=True)
    print(f"GCS URI: {source_record.get('gcs_uri')}", flush=True)

    # Analyze source video
    t_start = time.time()
    analyze_resp = safe_post(
        f"{CANARY_URL}/projects/{project_id}/source-videos/{source_video_id}/analyze",
        headers=headers,
        timeout=180
    )
    latency_analysis = round(time.time() - t_start, 2)
    if not analyze_resp.ok:
        raise RuntimeError(f"Source analysis failed ({analyze_resp.status_code}): {analyze_resp.text}")
    analysis_data = analyze_resp.json()
    print(f"Source Analysis succeeded in {latency_analysis}s.", flush=True)
    print(f"  Scenes Detected: {len(analysis_data.get('scenes', []))}", flush=True)
    print(f"  Art Style: {analysis_data.get('visual_style', {}).get('art_style')}", flush=True)
    print(f"  Hook Type: {analysis_data.get('hook', {}).get('hook_type')}", flush=True)
    print(f"  Analysis ID: {analysis_data.get('analysis_id')}", flush=True)

    telemetry.append({
        "task": "Source Analysis",
        "provider": "Google Vertex AI (GenAI SDK)",
        "model_id": ModelRoutingConfig.SOURCE_ANALYSIS,
        "status": "SUCCESS",
        "latency_sec": latency_analysis,
        "estimated_cost_usd": 0.0005
    })

    # -------------------------------------------------------------
    # STEP 2: Visual Identity Pack & Canonical Reference Image Generation
    # -------------------------------------------------------------
    print("\n[STEP 2] Testing Visual Identity Pack Generation (Gemini Image Modality)...", flush=True)
    t_start = time.time()
    vip_resp = safe_post(
        f"{CANARY_URL}/projects/{project_id}/visual-identity-pack",
        headers=headers,
        json={
            "art_style": "3D Pixar animated character style",
            "character_design": "Golden padlock anthropomorphic character with large expressive eyes",
            "characters": [
                {
                    "character_id": "char_padlock_lead",
                    "name": "Padlock Lead",
                    "description": "Anthropomorphic brass padlock character with arms and big cartoon eyes"
                }
            ]
        },
        timeout=120
    )
    latency_vip = round(time.time() - t_start, 2)
    if not vip_resp.ok:
        raise RuntimeError(f"Visual Identity generation failed ({vip_resp.status_code}): {vip_resp.text}")
    vip_data = vip_resp.json()
    print(f"Visual Identity Pack succeeded in {latency_vip}s.", flush=True)
    characters = vip_data.get("characters", {})
    padlock_char = characters.get("char_padlock_lead", {})
    front_ref = padlock_char.get("front_ref_uri") or padlock_char.get("canonical_ref_uri") or vip_data.get("master_sheet_uri")
    print(f"  Generated Character Reference URI: {front_ref}", flush=True)
    assert front_ref and front_ref.startswith("gs://"), f"Invalid reference URI generated: {front_ref}"

    telemetry.append({
        "task": "Visual Identity / Reference Image",
        "provider": "Google Vertex AI (Gemini Multimodal generate_content)",
        "model_id": ModelRoutingConfig.REFERENCE_IMAGE,
        "status": "SUCCESS",
        "latency_sec": latency_vip,
        "estimated_cost_usd": 0.0300
    })

    # -------------------------------------------------------------
    # STEP 3: Clone Blueprint Creation
    # -------------------------------------------------------------
    print("\n[STEP 3] Generating Clone Blueprint...", flush=True)
    cb_resp = safe_post(
        f"{CANARY_URL}/projects/{project_id}/source-videos/{source_video_id}/clone-blueprint",
        headers=headers,
        timeout=60
    )
    if not cb_resp.ok:
        raise RuntimeError(f"Clone Blueprint creation failed ({cb_resp.status_code}): {cb_resp.text}")
    clone_bp = cb_resp.json()
    clone_blueprint_id = clone_bp["clone_blueprint_id"]
    print(f"Clone Blueprint created. ID: {clone_blueprint_id}, Scenes: {len(clone_bp.get('scenes', []))}", flush=True)

    # -------------------------------------------------------------
    # STEP 4: Creative Transformation (NORMAL Story Complexity)
    # -------------------------------------------------------------
    print("\n[STEP 4A] Testing Creative Transformation - NORMAL Complexity...", flush=True)
    t_start = time.time()
    transform_normal_resp = safe_post(
        f"{CANARY_URL}/projects/{project_id}/clone-blueprints/{clone_blueprint_id}/transform",
        headers=headers,
        json={
            "topic": "Smart Home Lock Troubleshooting Humor",
            "story_change": "The padlock character forgets the combination to its own front door",
            "target_duration_seconds": 13.0,
            "tone": "Humorous viral reel",
            "language": "English",
            "requested_character_ids": ["char_padlock_lead"],
            "preserve_structure": True,
            "preserve_pacing": True,
            "preserve_camera_language": True,
            "preserve_emotional_arc": True
        },
        timeout=180
    )
    latency_normal = round(time.time() - t_start, 2)
    if not transform_normal_resp.ok:
        raise RuntimeError(f"Transformation (NORMAL) failed ({transform_normal_resp.status_code}): {transform_normal_resp.text}")
    prod_bp_normal = transform_normal_resp.json()
    print(f"NORMAL Creative Transformation succeeded in {latency_normal}s.", flush=True)
    print(f"  Production Blueprint ID: {prod_bp_normal.get('blueprint_id')}", flush=True)
    print(f"  Status: {prod_bp_normal.get('status')}", flush=True)
    print(f"  Scenes Count: {len(prod_bp_normal.get('scenes', []))}", flush=True)

    telemetry.append({
        "task": "Creative Transformation (NORMAL)",
        "provider": "Google Vertex AI (GenAI SDK Structured JSON)",
        "model_id": ModelRoutingConfig.NORMAL_STORY,
        "status": "SUCCESS",
        "latency_sec": latency_normal,
        "estimated_cost_usd": 0.0010
    })

    # -------------------------------------------------------------
    # STEP 5: Creative Transformation (COMPLEX Story Complexity)
    # -------------------------------------------------------------
    print("\n[STEP 4B] Testing Creative Transformation - COMPLEX Complexity (>30s duration)...", flush=True)
    t_start = time.time()
    transform_complex_resp = safe_post(
        f"{CANARY_URL}/projects/{project_id}/clone-blueprints/{clone_blueprint_id}/transform",
        headers=headers,
        json={
            "topic": "Epic Locksmith Adventure",
            "story_change": "The padlock character embarks on an epic quest through a stormy city to find the master key",
            "target_duration_seconds": 45.0,
            "tone": "Cinematic comedic narrative",
            "language": "English",
            "requested_character_ids": ["char_padlock_lead"],
            "preserve_structure": False,
            "preserve_pacing": True,
            "preserve_camera_language": True,
            "preserve_emotional_arc": True
        },
        timeout=300
    )
    latency_complex = round(time.time() - t_start, 2)
    if not transform_complex_resp.ok:
        raise RuntimeError(f"Transformation (COMPLEX) failed ({transform_complex_resp.status_code}): {transform_complex_resp.text}")
    prod_bp_complex = transform_complex_resp.json()
    print(f"COMPLEX Creative Transformation succeeded in {latency_complex}s.", flush=True)
    print(f"  Production Blueprint ID: {prod_bp_complex.get('blueprint_id')}", flush=True)
    print(f"  Status: {prod_bp_complex.get('status')}", flush=True)
    print(f"  Scenes Count: {len(prod_bp_complex.get('scenes', []))}", flush=True)

    telemetry.append({
        "task": "Creative Transformation (COMPLEX)",
        "provider": "AWS Bedrock Claude 3.5 Sonnet / Claude Sonnet 4.6",
        "model_id": ModelRoutingConfig.COMPLEX_STORY,
        "status": "SUCCESS",
        "latency_sec": latency_complex,
        "estimated_cost_usd": 0.0050
    })

    # -------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------
    print("\n" + "=" * 70, flush=True)
    print("CANARY VALIDATION TELEMETRY SUMMARY", flush=True)
    print("=" * 70, flush=True)
    total_cost = sum(t["estimated_cost_usd"] for t in telemetry)
    for t in telemetry:
        print(f"* [{t['status']}] {t['task']}: Model={t['model_id']} | Latency={t['latency_sec']}s | Est. Cost=${t['estimated_cost_usd']:.4f}", flush=True)
    print(f"Total Validation Cost: ${total_cost:.4f}", flush=True)
    print("=" * 70, flush=True)
    
    return telemetry

if __name__ == "__main__":
    try:
        run_canary_validation()
    except Exception as e:
        print(f"\n[ERROR] Canary Validation Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
