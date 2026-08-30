import os
import sys
import json
import re

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath("."))
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.source_analyzer import run_source_analysis
from core.services.clone_blueprint_builder import CloneBlueprintBuilder
from services.trend_remixer import _sanitize_veo_prompt

def generate_google_flow_prompt_pack(video_path: str, output_md_path: str, output_json_path: str):
    print("=" * 70)
    print(f"🎬 VIDEO CLONER -> GOOGLE FLOW PROMPT COMPILER")
    print(f"📁 Source Video: {video_path}")
    print("=" * 70)

    # 1. Source Analysis
    print("\n[1/4] Probing media and running multimodal analysis...")
    source_analysis = run_source_analysis(video_path, "src_flow_export")
    
    # 2. Build Clone Blueprint
    print("\n[2/4] Constructing Clone Blueprint...")
    builder = CloneBlueprintBuilder()
    clone_bp = builder.build_from_source(
        source_analysis,
        project_id="proj_flow_001",
        user_id="user_flow",
        title="Google Flow Production Clone"
    )

    art_style = source_analysis.visual_style.art_style or "3D Pixar-style digital animation, stylized CGI cartoon"
    char_design = source_analysis.visual_style.character_design or "Expressive 3D stylized character"
    
    # 3. Compile Master Prompts for each Scene
    print("\n[3/4] Compiling Scene-by-Scene Prompts for Google Flow...")
    
    # Master Character Sheet Prompt
    master_character_prompt = (
        f"Character turnaround model sheet of {char_design}, in {art_style}. "
        f"Front view, three-quarter view, side profile, and full body view. "
        f"Neutral solid studio background, volumetric cinematic lighting, high-end 3D render, 8k resolution."
    )

    scenes_data = []
    
    # Combine cuts and semantic scenes
    semantic_map = {s.scene_number: s for s in source_analysis.semantic_scenes}
    
    for i, seg in enumerate(source_analysis.scenes):
        sc_num = seg.scene_number
        sem = semantic_map.get(sc_num)
        
        narrative_purpose = sem.narrative_purpose if sem else f"Beat {sc_num}"
        visual_action = sem.visual_action if sem else "Character performing action in scene"
        emotion = sem.emotion if sem else "neutral"
        shot_type = sem.shot_type if sem and sem.shot_type != "UNKNOWN" else "MEDIUM SHOT"
        camera_motion = sem.camera_motion if sem and sem.camera_motion != "UNKNOWN" else "STATIC"
        lighting = sem.lighting_summary if sem and sem.lighting_summary else "Cinematic volumetric lighting"
        location = sem.location_summary if sem and sem.location_summary else "Detailed 3D background environment"
        
        # Dialogue line matching time window if any
        matching_dialogue = []
        for d in source_analysis.dialogue_beats:
            if d.start_seconds is not None and d.end_seconds is not None:
                # Check if dialogue beat overlaps with this scene segment
                if not (d.end_seconds <= seg.start_seconds or d.start_seconds >= seg.end_seconds):
                    matching_dialogue.append(d)
            elif i < len(source_analysis.dialogue_beats) and d == source_analysis.dialogue_beats[i]:
                matching_dialogue.append(d)
        
        dialogue_text = " ".join([d.text for d in matching_dialogue]).strip() if matching_dialogue else ""
        speaker_role = matching_dialogue[0].speaker_role if matching_dialogue else "PROTAGONIST"

        # Build raw visual description
        action_core = (
            f"{shot_type}, {camera_motion} camera motion. {visual_action}. "
            f"Location: {location}. Lighting: {lighting}. Emotion: {emotion} expression."
        )

        # Run through official sanitization engine
        compiled_veo_prompt = _sanitize_veo_prompt(
            prompt=action_core,
            art_style=art_style,
            character_design=char_design,
            is_animated=True
        )

        scene_entry = {
            "scene_number": sc_num,
            "duration_seconds": seg.duration_seconds,
            "start_time": seg.start_seconds,
            "end_time": seg.end_seconds,
            "narrative_purpose": narrative_purpose,
            "shot_type": shot_type,
            "camera_motion": camera_motion,
            "emotion": emotion,
            "veo_prompt": compiled_veo_prompt,
            "dialogue": {
                "speaker": speaker_role,
                "text": dialogue_text,
                "emotion": emotion,
                "duration_seconds": round(min(seg.duration_seconds, max(1.5, len(dialogue_text.split()) * 0.4)), 1) if dialogue_text else 0.0
            }
        }
        scenes_data.append(scene_entry)

    # 4. Generate Output Files
    print(f"\n[4/4] Writing output documents...")
    
    # Save JSON
    json_payload = {
        "source_metadata": {
            "duration_seconds": source_analysis.media_metadata.duration_seconds,
            "aspect_ratio": source_analysis.media_metadata.aspect_ratio,
            "fps": source_analysis.media_metadata.fps,
            "scene_count": len(source_analysis.scenes)
        },
        "visual_identity": {
            "art_style": art_style,
            "character_design": char_design,
            "master_character_sheet_prompt": master_character_prompt
        },
        "hook_analysis": {
            "type": source_analysis.hook.hook_type,
            "description": source_analysis.hook.hook_description,
            "duration": f"{source_analysis.hook.hook_start_seconds}s - {source_analysis.hook.hook_end_seconds}s"
        },
        "transcript_raw": source_analysis.transcript_text,
        "scenes": scenes_data
    }
    
    with open(output_json_path, "w", encoding="utf-8") as jf:
        json.dump(json_payload, jf, indent=2)
    print(f"✅ Saved JSON: {output_json_path}")

    # Save Markdown for Google Flow
    md_content = f"""# 🎬 Google Flow Production Prompt Pack

**Source Video:** `{os.path.basename(video_path)}`  
**Total Duration:** `{source_analysis.media_metadata.duration_seconds}s`  
**Total Scenes:** `{len(scenes_data)}`  
**Aspect Ratio:** `9:16 (Vertical)`  
**Art Style:** `{art_style}`  
**Character Design:** `{char_design}`  

---

## 🎨 Master Character Consistency Prompt (Step 1: Anchor Reference)
> **Instructions for Google Flow / Midjourney / Imagen:**
> Generate this character sheet first. Download the resulting image and upload it as the **Reference Image (First Frame)** in Google Flow for each scene to maintain 100% visual consistency.

```text
{master_character_prompt}
```

---

## 📋 Complete Scene-by-Scene Prompt Suite (Google Flow / Veo)

"""
    for sc in scenes_data:
        md_content += f"""### 🎥 Shot {sc['scene_number']:02d} — {sc['narrative_purpose']}
- **Timing:** `{sc['start_time']}s` $\\rightarrow$ `{sc['end_time']}s` (`{sc['duration_seconds']}s` total)
- **Cinematography:** `{sc['shot_type']}` | `{sc['camera_motion']}`
- **Emotion / Mood:** `{sc['emotion']}`

#### 🎬 Google Flow / Veo Video Prompt:
```text
{sc['veo_prompt']}
```

"""
        if sc['dialogue']['text']:
            md_content += f"""#### 🎙️ Spoken Dialogue / Voiceover (ElevenLabs / Audio Studio):
- **Speaker:** `{sc['dialogue']['speaker']}`
- **Emotion:** `{sc['dialogue']['emotion']}`
- **Estimated Duration:** `{sc['dialogue']['duration_seconds']}s`
```text
{sc['dialogue']['text']}
```
"""
        else:
            md_content += """#### 🎙️ Audio / Dialogue:
*(Ambient music / sound effect only — no dialogue spoken)*
"""
        md_content += "\n---\n\n"

    md_content += f"""## 📊 Full Video Transcript & Script
```text
{source_analysis.transcript_text}
```

## 🚀 How to Assemble in Google Flow:
1. **Generate Anchor Character:** Paste the *Master Character Consistency Prompt* into your image generator (or Google Flow reference slot) and select the best look.
2. **Generate Scenes (1 to {len(scenes_data)}):** For each scene, copy the corresponding **Google Flow / Veo Video Prompt** and set the scene duration to match the timeline.
3. **Generate Voiceover:** If using dialogue, paste the dialogue lines into ElevenLabs or your TTS model with the specified emotion.
4. **Assembly:** Drop the generated video clips in sequential order onto your video editing timeline (CapCut, Premiere, DaVinci).
"""

    with open(output_md_path, "w", encoding="utf-8") as mf:
        mf.write(md_content)
    print(f"✅ Saved Markdown: {output_md_path}")
    print("\n🎉 ALL PROMPTS COMPILED SUCCESSFULLY!")

if __name__ == "__main__":
    vid = os.path.abspath(os.path.join("..", "videos", "WhatsApp Video 2026-08-17 at 11.36.14 PM.mp4"))
    out_md = os.path.abspath(os.path.join("..", "videos", "google_flow_prompts.md"))
    out_json = os.path.abspath(os.path.join("..", "videos", "google_flow_prompts.json"))
    generate_google_flow_prompt_pack(vid, out_md, out_json)
