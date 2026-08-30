import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath("."))

from services.source_analyzer import run_source_analysis
from core.services.clone_blueprint_builder import CloneBlueprintBuilder

video_path = os.path.abspath(os.path.join("..", "videos", "WhatsApp Video 2026-08-17 at 11.36.14 PM.mp4"))
print(f"Checking video path: {video_path}")
print(f"Exists: {os.path.exists(video_path)}, Size: {os.path.getsize(video_path) if os.path.exists(video_path) else 'N/A'}")

try:
    print("\n--- STEP 1: Running Source Analysis ---")
    source_analysis = run_source_analysis(video_path, "src_golden_uploaded")
    print("\n[SUCCESS] Source Analysis Completed!")
    print(f"Duration: {source_analysis.media_metadata.duration_seconds}s")
    print(f"Detected Scenes: {len(source_analysis.scenes)}")
    print(f"Art Style: {source_analysis.visual_style.art_style}")
    print(f"Character Design: {source_analysis.visual_style.character_design}")
    print(f"Hook: {source_analysis.hook.visual_hook_description}")
    print(f"Transcript: {source_analysis.transcript_text[:150]}...")
except Exception as e:
    import traceback
    print(f"Error during analysis: {e}")
    traceback.print_exc()
