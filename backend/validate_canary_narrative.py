"""
Canary Narrative Transformation Real Validation Script
Targets the newly deployed Canary Revision: ai-video-backend-00163-maz
Canary URL: https://canary-remediation---ai-video-backend-sfxkkeql7q-uc.a.run.app

Strictly runs:
Source -> Analysis -> DNA -> Visual Identity -> Creative Transformation -> ProductionBlueprint
DOES NOT:
- approve for generation
- enqueue Cloud Tasks
- call Veo
- call ElevenLabs
- call SyncLabs
"""
import os
import sys
import time
import uuid
import json
import requests

from config import ModelRoutingConfig
from core.services.originality_validator import (
    compute_narrative_similarity,
    validate_blueprint_originality,
    OriginalityValidationException
)
from core.models.blueprint import ProductionBlueprint
from core.models.clone_blueprint import CloneBlueprint

CANARY_URL = "https://canary-remediation---ai-video-backend-sfxkkeql7q-uc.a.run.app"
TEST_VIDEO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "videos", "WhatsApp Video 2026-08-17 at 11.36.14 PM.mp4"))
FIREBASE_API_KEY = "AIzaSyDL4FHsHBa1XE9aUt1h5VyL4iogNOLvvUg"

def get_auth_token():
    email = f"canary_narrative_{uuid.uuid4().hex[:8]}@example.com"
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
        except Exception as e:
            if attempt == 4:
                raise
            time.sleep(2)
    raise RuntimeError(f"Auth signup failed: {resp.text}")

def safe_post(url, **kwargs):
    for attempt in range(4):
        try:
            return requests.post(url, **kwargs)
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            if attempt == 3:
                raise
            print(f"Network retry on {url} ({attempt+1}/4): {e}", flush=True)
            time.sleep(3)

def run_real_canary_test():
    print("=" * 80, flush=True)
    print("CLONEFRAME REAL CANARY NARRATIVE TRANSFORMATION VALIDATION", flush=True)
    print(f"Canary URL: {CANARY_URL}", flush=True)
    print(f"Fixture: {TEST_VIDEO_PATH}", flush=True)
    print("=" * 80, flush=True)

    assert os.path.exists(TEST_VIDEO_PATH), f"Fixture video missing: {TEST_VIDEO_PATH}"

    token, user_id = get_auth_token()
    project_id = f"canary_narrative_proj_{uuid.uuid4().hex[:8]}"
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Authenticated Canary User: {user_id}", flush=True)
    print(f"Project ID: {project_id}", flush=True)

    # 1. Source Video Upload
    print("\n--- [1] Uploading Canonical Source Video ---", flush=True)
    with open(TEST_VIDEO_PATH, "rb") as f:
        up_resp = safe_post(
            f"{CANARY_URL}/projects/{project_id}/source-videos",
            headers=headers,
            files={"file": ("whatsapp_padlock.mp4", f, "video/mp4")}
        )
    if not up_resp.ok:
        raise RuntimeError(f"Upload failed ({up_resp.status_code}): {up_resp.text}")
    src_rec = up_resp.json()
    source_video_id = src_rec["source_video_id"]
    print(f"Uploaded source video ID: {source_video_id}", flush=True)

    # 2. Source Analysis
    print("\n--- [2] Running Source Analysis ---", flush=True)
    t0 = time.time()
    ana_resp = safe_post(
        f"{CANARY_URL}/projects/{project_id}/source-videos/{source_video_id}/analyze",
        headers=headers,
        timeout=180
    )
    if not ana_resp.ok:
        raise RuntimeError(f"Analysis failed ({ana_resp.status_code}): {ana_resp.text}")
    ana_data = ana_resp.json()
    ana_latency = round(time.time() - t0, 2)
    print(f"Source Analysis succeeded in {ana_latency}s.", flush=True)
    print(f"  Art Style Detected: {ana_data.get('visual_style', {}).get('art_style')}", flush=True)
    print(f"  Character Design: {ana_data.get('visual_style', {}).get('character_design')}", flush=True)
    print(f"  Scenes count: {len(ana_data.get('scenes', []))}", flush=True)

    # 3. Visual Identity Pack
    print("\n--- [3] Generating Visual Identity Pack ---", flush=True)
    t0 = time.time()
    vip_resp = safe_post(
        f"{CANARY_URL}/projects/{project_id}/visual-identity-pack",
        headers=headers,
        json={
            "art_style": ana_data.get("visual_style", {}).get("art_style") or "3D Pixar animated character style",
            "character_design": ana_data.get("visual_style", {}).get("character_design") or "Brass padlock character with expressive eyes",
            "characters": [
                {
                    "character_id": "char_padlock_1",
                    "name": "Padlock Lead",
                    "description": "Anthropomorphic brass padlock character"
                }
            ]
        },
        timeout=120
    )
    if not vip_resp.ok:
        raise RuntimeError(f"VIP generation failed ({vip_resp.status_code}): {vip_resp.text}")
    vip_data = vip_resp.json()
    vip_latency = round(time.time() - t0, 2)
    print(f"Visual Identity Pack succeeded in {vip_latency}s.", flush=True)

    # 4. Clone Blueprint
    print("\n--- [4] Creating Clone Blueprint ---", flush=True)
    cb_resp = safe_post(
        f"{CANARY_URL}/projects/{project_id}/source-videos/{source_video_id}/clone-blueprint",
        headers=headers,
        timeout=60
    )
    if not cb_resp.ok:
        raise RuntimeError(f"Clone Blueprint failed ({cb_resp.status_code}): {cb_resp.text}")
    clone_bp = cb_resp.json()
    clone_blueprint_id = clone_bp["clone_blueprint_id"]
    print(f"Clone Blueprint ID: {clone_blueprint_id}", flush=True)

    # 5. Creative Transformation with User Intent
    print("\n--- [5] Executing Creative Transformation (Bank Heist Intent) ---", flush=True)
    transform_payload = {
        "topic": "Turn this into a funny bank-heist story",
        "story_change": "The padlock characters attempt a high-stakes bank vault robbery",
        "niche": "Heist Comedy",
        "tone": "Suspenseful & Hilarious",
        "language": "English",
        "target_duration_seconds": 14.0,
        "requested_character_ids": ["char_padlock_1"]
    }
    print(f"Transformation Request Payload sent to Canary:", flush=True)
    print(json.dumps(transform_payload, indent=2), flush=True)

    t0 = time.time()
    tr_resp = safe_post(
        f"{CANARY_URL}/projects/{project_id}/clone-blueprints/{clone_blueprint_id}/transform",
        headers=headers,
        json=transform_payload,
        timeout=180
    )
    if not tr_resp.ok:
        raise RuntimeError(f"Transformation failed ({tr_resp.status_code}): {tr_resp.text}")
    prod_bp = tr_resp.json()
    tr_latency = round(time.time() - t0, 2)
    print(f"\nCreative Transformation completed in {tr_latency}s.", flush=True)
    print(f"Production Blueprint ID: {prod_bp.get('blueprint_id')}", flush=True)
    print(f"Title: {prod_bp.get('title')}", flush=True)
    print(f"Concept: {prod_bp.get('concept')}", flush=True)
    print(f"Genre: {prod_bp.get('genre')}", flush=True)
    print(f"Status: {prod_bp.get('status')}", flush=True)

    # 6. Verification & Structural Checks
    print("\n" + "=" * 80, flush=True)
    print("VERIFICATION OF TRANSFORMATION OUTPUT", flush=True)
    print("=" * 80, flush=True)

    # Check Visual DNA Preserved
    art_style = prod_bp.get("authoritative_art_style", "")
    print(f"\n[Visual DNA Preserved]")
    print(f"  Art Style: {art_style}")
    print(f"  Character IDs: {prod_bp.get('required_character_ids')}")

    # Check Narrative Separation
    scenes = prod_bp.get("scenes", [])
    print(f"\n[Generated Scenes Breakdown (Count: {len(scenes)})]")
    
    all_generated_text = f"{prod_bp.get('title', '')} {prod_bp.get('concept', '')} "
    for scn in scenes:
        print(f"  Scene #{scn.get('scene_number')} [{scn.get('narrative_purpose')}]:")
        print(f"    Action: {scn.get('action')}")
        for dlg in scn.get("dialogue", []):
            print(f"    Dialogue ({dlg.get('character_id')}): \"{dlg.get('text')}\"")
        all_generated_text += f"{scn.get('action', '')} " + " ".join([d.get('text', '') for d in scn.get('dialogue', [])]) + " "

    all_generated_lower = all_generated_text.lower()

    # Verify forbidden source tropes are NOT copied
    forbidden_tropes = ["grocery", "groceries", "front porch", "house door", "lock out", "locked out", "forgot keys", "wrong key"]
    found_forbidden = [t for t in forbidden_tropes if t in all_generated_lower]
    print(f"\n[Original Tropes Excluded]")
    print(f"  Forbidden tropes detected: {found_forbidden} (Must be empty)")
    assert len(found_forbidden) == 0, f"Transformation copied original tropes: {found_forbidden}"

    # Verify new heist tropes are created
    heist_indicators = ["bank", "vault", "heist", "robbery", "safe", "laser", "security", "loot", "alarm", "code", "guard", "crack", "sneak"]
    matched_heist = [h for h in heist_indicators if h in all_generated_lower]
    print(f"\n[New Heist Narrative Created]")
    print(f"  Heist elements present: {matched_heist}")
    assert len(matched_heist) > 0, "No bank-heist elements detected in generated narrative!"

    # 7. Originality Validation Score
    clone_bp_obj = CloneBlueprint(**clone_bp)
    prod_bp_obj = ProductionBlueprint(**prod_bp)
    
    sim_score, matched_keywords = compute_narrative_similarity(clone_bp_obj, prod_bp_obj)
    print(f"\n[Originality Validation]")
    print(f"  Narrative Similarity Score: {sim_score:.4f} (Max Allowed: 0.4000)")
    print(f"  Overlapping Narrative Keywords: {matched_keywords}")
    assert sim_score < 0.40, f"Narrative similarity {sim_score:.4f} exceeds 0.40 threshold!"

    # Verify validator unit behaviors
    print(f"\n[Originality Validator Unit Constraints]")
    # Test that exact clone fails
    try:
        # Mock a copied production blueprint
        copied_scenes = []
        for s in clone_bp_obj.scenes:
            from core.models.blueprint import SceneBlueprint
            copied_scenes.append(SceneBlueprint(
                scene_id=s.scene_id,
                scene_number=s.scene_number,
                narrative_purpose=s.narrative_purpose,
                estimated_duration_seconds=s.source_duration_seconds,
                character_ids=["char_padlock_1"],
                action=s.visual_action,
                dialogue=[]
            ))
        copied_prod_bp = prod_bp_obj.model_copy(update={
            "scenes": copied_scenes,
            "concept": clone_bp_obj.hook.hook_description if clone_bp_obj.hook else "Original locked out"
        })
        validate_blueprint_originality(clone_bp_obj, copied_prod_bp, max_allowed_similarity=0.40)
        raise AssertionError("Exact copy unexpectedly PASSED originality validation!")
    except OriginalityValidationException as e:
        print(f"  [OK] Exact-copy rejection: SUCCESS ({e})")

    print("\n" + "=" * 80)
    print("[SUCCESS] CANARY TRANSFORMATION VALIDATION COMPLETED SUCCESSFULLY")
    print("=" * 80)

    return {
        "canary_revision": "ai-video-backend-00163-maz",
        "canary_url": CANARY_URL,
        "project_id": project_id,
        "blueprint_id": prod_bp.get("blueprint_id"),
        "title": prod_bp.get("title"),
        "concept": prod_bp.get("concept"),
        "genre": prod_bp.get("genre"),
        "scenes_count": len(scenes),
        "forbidden_tropes_found": found_forbidden,
        "heist_elements_matched": matched_heist,
        "similarity_score": sim_score,
        "analysis_latency": ana_latency,
        "vip_latency": vip_latency,
        "transformation_latency": tr_latency
    }

if __name__ == "__main__":
    results = run_real_canary_test()
    print("\nFINAL SUMMARY DICT:")
    print(json.dumps(results, indent=2))
