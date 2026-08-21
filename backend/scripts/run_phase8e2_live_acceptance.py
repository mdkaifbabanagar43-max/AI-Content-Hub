import os
import sys
import time
import json
import uuid
import datetime
import requests
import subprocess
from google.cloud import firestore

CLOUD_RUN_URL = "https://ai-video-backend-835818829937.us-central1.run.app"
USER_ID = "test_user_id"
PROJECT_ID = "proj_lock_acceptance_8e2"
BLUEPRINT_ID = "bp_lock_acceptance_8e2_001"
CLONE_BP_ID = "cl_fff273eac45c"

def setup_firestore_test_data():
    print(f"[Acceptance Runner] Setting up test data in Firestore for {USER_ID}/{PROJECT_ID}...")
    db = firestore.Client(project="shortcutai-backend")
    
    # 1. Fetch original CloneBlueprint data
    orig_clone_doc = db.collection("users").document("user_acceptance_8e1") \
                       .collection("projects").document("proj_lock_acceptance") \
                       .collection("clone_blueprints").document(f"{CLONE_BP_ID}_v1").get()
                       
    if not orig_clone_doc.exists:
        raise Exception(f"Original clone blueprint {CLONE_BP_ID}_v1 not found in Firestore!")
        
    clone_data = orig_clone_doc.to_dict()
    clone_data["project_id"] = PROJECT_ID
    clone_data["user_id"] = USER_ID
    
    # Save CloneBlueprint under test_user_id
    db.collection("users").document(USER_ID) \
      .collection("projects").document(PROJECT_ID) \
      .collection("clone_blueprints").document(f"{CLONE_BP_ID}_v1").set(clone_data)
      
    print(f"[Acceptance Runner] Saved CloneBlueprint {CLONE_BP_ID}_v1 for {USER_ID}")
    
    # 2. Fetch original ProductionBlueprint data
    orig_prod_doc = db.collection("users").document("user_acceptance_8e1") \
                      .collection("projects").document("proj_lock_acceptance") \
                      .collection("blueprints").document("bp_lock_acceptance_001_v1").get()
                      
    if not orig_prod_doc.exists:
        raise Exception("Original blueprint bp_lock_acceptance_001_v1 not found!")
        
    prod_data = orig_prod_doc.to_dict()
    prod_data["blueprint_id"] = BLUEPRINT_ID
    prod_data["blueprint_version"] = 1
    prod_data["project_id"] = PROJECT_ID
    prod_data["status"] = "APPROVED"
    prod_data["source_clone_blueprint_id"] = CLONE_BP_ID
    prod_data["source_clone_blueprint_version"] = 1
    prod_data["authoritative_art_style"] = "3D Pixar-style animation"
    prod_data["authoritative_character_design"] = "3D anthropomorphic couple with brass padlock heads wearing modern and traditional Indian clothing"
    prod_data["visual_style_profile"] = clone_data.get("visual_style_profile")
    
    # Save ProductionBlueprint under test_user_id
    db.collection("users").document(USER_ID) \
      .collection("projects").document(PROJECT_ID) \
      .collection("blueprints").document(f"{BLUEPRINT_ID}_v1").set(prod_data)
      
    print(f"[Acceptance Runner] Saved ProductionBlueprint {BLUEPRINT_ID}_v1 with status APPROVED for {USER_ID}")

def trigger_cloud_run_job():
    print(f"[Acceptance Runner] Triggering Cloud Run endpoint: {CLOUD_RUN_URL}/projects/{PROJECT_ID}/production-blueprints/{BLUEPRINT_ID}/generate")
    headers = {
        "Authorization": "Bearer dev_token",
        "Content-Type": "application/json"
    }
    url = f"{CLOUD_RUN_URL}/projects/{PROJECT_ID}/production-blueprints/{BLUEPRINT_ID}/generate"
    resp = requests.post(url, headers=headers, timeout=30)
    print(f"[Acceptance Runner] Trigger Response: HTTP {resp.status_code} -> {resp.text}")
    if resp.status_code != 200:
        raise Exception(f"Cloud Run trigger failed: {resp.status_code} - {resp.text}")
    return resp.json()

def monitor_job_execution(start_time):
    print("[Acceptance Runner] Monitoring job execution in Cloud Logging & Firestore...")
    db = firestore.Client(project="shortcutai-backend")
    
    poll_interval = 15
    max_wait = 1800 # 30 minutes max for full 5 scenes
    elapsed = 0
    
    seen_log_timestamps = set()
    
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed = int(time.time() - start_time)
        
        # 1. Check blueprint status in Firestore
        bp_doc = db.collection("users").document(USER_ID) \
                   .collection("projects").document(PROJECT_ID) \
                   .collection("blueprints").document(f"{BLUEPRINT_ID}_v1").get()
                   
        status = "UNKNOWN"
        if bp_doc.exists:
            status = bp_doc.to_dict().get("status", "UNKNOWN")
            
        # 2. Fetch latest logs from Cloud Run
        iso_start = datetime.datetime.fromtimestamp(start_time - 10, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        log_cmd = [
            "gcloud.cmd", "logging", "read",
            f'resource.type=cloud_run_revision AND resource.labels.service_name=ai-video-backend AND timestamp>="{iso_start}"',
            "--project=shortcutai-backend", "--limit=40", "--format=json"
        ]
        
        try:
            p = subprocess.run(log_cmd, capture_output=True, text=True, timeout=20)
            if p.stdout.strip():
                logs = json.loads(p.stdout)
                # Logs are returned newest first; reverse for chronological printing
                for log in reversed(logs):
                    log_ts = log.get("timestamp", "")
                    if log_ts and log_ts not in seen_log_timestamps:
                        seen_log_timestamps.add(log_ts)
                        msg = log.get("textPayload") or log.get("jsonPayload", {}).get("message") or ""
                        if msg:
                            print(f"[CloudRun {log_ts[-13:-1]}] {msg}")
        except Exception as log_err:
            pass
            
        # 3. Check attempts count
        attempts = list(db.collection("users").document(USER_ID)
                          .collection("projects").document(PROJECT_ID)
                          .collection("generation_attempts").stream())
        
        print(f"[Acceptance Runner] Elapsed: {elapsed}s | Blueprint Status: {status} | Generation Attempts Logged: {len(attempts)}")
        
        if status in ["COMPLETED", "FAILED"]:
            print(f"[Acceptance Runner] Job reached terminal status: {status}")
            break
            
    return status

def collect_forensic_metrics():
    print("\n" + "="*80)
    print("PHASE 8E.2 FORENSIC TELEMETRY AUDIT")
    print("="*80)
    
    db = firestore.Client(project="shortcutai-backend")
    
    # 1. Blueprint details
    bp_doc = db.collection("users").document(USER_ID) \
               .collection("projects").document(PROJECT_ID) \
               .collection("blueprints").document(f"{BLUEPRINT_ID}_v1").get()
               
    bp_data = bp_doc.to_dict() if bp_doc.exists else {}
    
    # 2. Final Video Record
    final_videos = list(db.collection("users").document(USER_ID)
                          .collection("projects").document(PROJECT_ID)
                          .collection("final_videos").stream())
    
    final_video_data = final_videos[0].to_dict() if final_videos else {}
    
    # 3. Generation Attempts
    attempt_docs = list(db.collection("users").document(USER_ID)
                          .collection("projects").document(PROJECT_ID)
                          .collection("generation_attempts").stream())
    
    attempts = [doc.to_dict() for doc in attempt_docs]
    attempts.sort(key=lambda x: (x.get("scene_id", ""), x.get("attempt_number", 1)))
    
    return bp_data, final_video_data, attempts

if __name__ == "__main__":
    start_time = time.time()
    setup_firestore_test_data()
    trigger_cloud_run_job()
    final_status = monitor_job_execution(start_time)
    bp_data, final_video_data, attempts = collect_forensic_metrics()
    
    # Output raw JSON summary for programmatic verification
    output_summary = {
        "final_status": final_status,
        "blueprint": bp_data,
        "final_video": final_video_data,
        "attempts": attempts,
        "total_elapsed_seconds": time.time() - start_time
    }
    
    with open("phase8e2_acceptance_result.json", "w", encoding="utf-8") as f:
        json.dump(output_summary, f, indent=2, default=str)
        
    print(f"\n[Acceptance Runner] Completed in {time.time() - start_time:.2f}s. Results saved to phase8e2_acceptance_result.json")
