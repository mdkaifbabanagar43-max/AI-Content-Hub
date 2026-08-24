# UNIVERSAL TRANSFORMATION CONTRACT — CLONEFRAME

**Boundary Module:** `core.services.universal_creative_director.py`  
**Consolidation Target:** Unifies Video Cloner & Trend Cloner creative transformation boundaries.  

---

## 1. Universal Transformation Context

The LLM prompt is assembled dynamically based *strictly* on the user's `PreservationProfile`:

```python
class TransformationContext:
    """Scoped container providing ONLY authorized DNA context to the LLM."""
    
    def compile_prompt(self, intent: CloneIntent, source_dna: SourceDNACluster) -> str:
        prompt_sections = []
        
        # 1. Primary Creative Directive
        prompt_sections.append(
            f"You are the AI Universal Creative Director.\n"
            f"Your mission is to write a BRAND NEW original storyboard driven by the User's Creative Intent.\n"
            f"Story Topic: {intent.creative_intent.topic}\n"
            f"Story Detail: {intent.creative_intent.story_change or 'Invent an original comedic/dramatic narrative'}\n"
            f"Genre / Tone: {intent.creative_intent.genre} ({intent.creative_intent.tone})\n"
            f"Language: {intent.creative_intent.language}\n"
            f"Target Duration: {intent.creative_intent.target_duration_seconds or 15.0}s\n"
        )
        
        # 2. Visual Style Preservation (Conditionally Injected)
        if intent.preservation_profile.preserve_visual_style and source_dna.visual_style:
            prompt_sections.append(
                f"SOURCE VISUAL STYLE (MANDATORY TO PRESERVE):\n"
                f"- Art Style: {source_dna.visual_style.art_style}\n"
                f"- Render Language: {source_dna.visual_style.render_language}\n"
                f"- Lighting & Ambiance: {source_dna.visual_style.lighting_style}\n"
                f"- Color Palette: {source_dna.visual_style.color_palette}\n"
            )
            
        # 3. Character Policy (Conditionally Injected)
        if intent.character_mode == CharacterMode.PRESERVE_SOURCE and source_dna.character_dna:
            prompt_sections.append(
                f"SOURCE CHARACTERS (PRESERVE EXACT APPEARANCE):\n"
                f"{json.dumps(source_dna.character_dna.characters, indent=2)}\n"
            )
        elif intent.character_mode == CharacterMode.CREATE_NEW:
            prompt_sections.append(
                f"CHARACTER POLICY: DO NOT use source characters. INVENT brand new characters "
                f"matching the {intent.creative_intent.topic} story, styled in the authoritative art style.\n"
            )
            
        # 4. Environment Policy (Conditionally Injected)
        if intent.environment_mode == EnvironmentMode.PRESERVE_SOURCE and source_dna.environment_dna:
            prompt_sections.append(
                f"ENVIRONMENT (PRESERVE SOURCE WORLD):\n"
                f"- World Setting: {source_dna.environment_dna.setting_type}\n"
                f"- Architectural Style: {source_dna.environment_dna.architectural_style}\n"
            )
        else:
            prompt_sections.append(
                f"ENVIRONMENT POLICY: Create NEW settings and locations appropriate for {intent.creative_intent.topic}.\n"
            )
            
        # 5. Pacing & Camera Language (Conditionally Injected)
        if intent.preservation_profile.preserve_camera_language and source_dna.camera_dna:
            prompt_sections.append(
                f"CAMERA LANGUAGE: Use shot types {source_dna.camera_dna.dominant_shot_types} "
                f"and motions {source_dna.camera_dna.motion_styles}.\n"
            )
        if intent.preservation_profile.preserve_pacing_editing and source_dna.pacing_dna:
            prompt_sections.append(
                f"PACING: Aim for average shot duration ~{source_dna.pacing_dna.average_shot_duration:.1f}s "
                f"with {source_dna.pacing_dna.cut_frequency} rhythm intensity.\n"
            )
            
        # 6. Negative Constraints (Zero Tolerances)
        prompt_sections.append(
            f"STRICT RULES:\n"
            f"1. DO NOT reproduce the original source video's dialogue, actions, gags, or punchlines.\n"
            f"2. Output strictly valid JSON conforming to ProductionBlueprint schema.\n"
            f"3. Divide story into 3-5 cohesive scenes (3-8s each) matching target duration.\n"
        )
        
        return "\n".join(prompt_sections)
```

---

## 2. Multi-Dimensional Validation Pipeline

Before returning the `ProductionBlueprint`, `UniversalCreativeDirector` executes 4 deterministic validation layers:

```
[Generated Production Blueprint]
               │
               ▼
   1. Schema & Pydantic Validation
      (Verifies all fields, shot durations, timestamps)
               │
               ▼
   2. Preservation Compliance Validation
      (If characters=false, assert no source character IDs appear)
      (If environment=false, assert no source scene locations copied)
               │
               ▼
   3. Narrative Originality Validation
      (Asserts narrative token/concept similarity < 0.40 against source beats)
               │
               ▼
   4. Entity & Project Bible Validation
      (Validates style IDs, voice IDs, and character IDs against project context)
               │
               ▼
   [Approved & Validated ProductionBlueprint]
```

---

## 3. Preservation Presets in UI

| Preset Name | Visual Style | Characters | Environment | Camera | Pacing | Trend |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Style Clone** | ✅ | ❌ (New) | ❌ (New) | ✅ | ✅ | ❌ |
| **2. Character Clone** | ✅ | ✅ (Preserved) | ❌ (New) | ❌ | ❌ | ❌ |
| **3. Style + Characters** | ✅ | ✅ (Preserved) | ❌ (New) | ✅ | ✅ | ❌ |
| **4. Full Visual Clone** | ✅ | ✅ (Preserved) | ✅ (Preserved)| ✅ | ✅ | ❌ |
| **5. Trend Inspired** | ❌ (New) | ❌ (New) | ❌ (New) | ✅ | ✅ | ✅ |

*Presets configure defaults; users may toggle any combination of checkboxes.*
