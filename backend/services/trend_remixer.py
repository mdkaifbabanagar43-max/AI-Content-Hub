import json
import re
from pydantic import BaseModel, Field, conlist
from typing import List, Optional
from google.genai import types

from services.ai_service import get_gemini_client, GEMINI_MODEL_NAME, GEMINI_FALLBACK_MODEL


# ─────────────────────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────────────────────

class DialogueLine(BaseModel):
    voice_label: str = Field(description="The character speaking, e.g., 'Male', 'Female', or character name")
    text: str = Field(description="The Hinglish/Hindi dialogue text")
    meme_overlay: str = Field(description="Optional meme to overlay during this line, e.g., 'laugh', 'crying', or 'none'", default="none")


class SceneBeat(BaseModel):
    """A single shot/beat in the multi-scene video."""
    scene_id: int = Field(description="Sequential scene number starting from 1")
    shot_type: str = Field(description="Shot type: 'wide_establish', 'medium_interaction', or 'punchline_closeup'")
    veo_prompt: str = Field(description="Veo generation prompt for this specific scene/shot")
    duration_s: float = Field(description="Target duration for this scene in seconds (3.0 – 5.0)", default=5.0)
    dialogue_lines: List[DialogueLine] = Field(description="Dialogue lines spoken during this scene", default_factory=list)


class TrendConcept(BaseModel):
    title: str = Field(description="Short, punchy title of the concept")
    description: str = Field(description="How this clones the trend for the target niche")
    # Multi-scene: primary output (2-5 scenes)
    scenes: conlist(SceneBeat, min_length=2, max_length=5) = Field(description="Array of 2 to 5 scene beats based on the comedic structure of the content (default 3)")
    # Backward compatibility: flat script array (populated from scenes)
    script: List[DialogueLine] = Field(description="Flattened array of all dialogue lines across all scenes", default_factory=list)
    # Backward compatibility: single veo_prompt (first scene's prompt)
    veo_prompt: str = Field(description="Primary Veo prompt (equals first scene's veo_prompt)", default="")
    outro_text_card: Optional[str] = Field(description="Short punchline sentence for the outro text card. e.g., 'Ulti Duniya mein...'", default=None)


class ConceptList(BaseModel):
    concepts: List[TrendConcept] = Field(description="List of 3 distinct trend clone concepts")


# ─────────────────────────────────────────────────────────────
# STYLE DETECTION HELPERS
# ─────────────────────────────────────────────────────────────

# Keywords that indicate an animated / non-photorealistic source style
_ANIMATED_INDICATORS = ["3d", "animation", "animated", "cartoon", "pixar", "anime",
                        "claymation", "stop-motion", "cel-shaded", "digital art",
                        "render", "cgi", "vfx", "motion graphics"]

# Contradictory photorealistic tokens that must be stripped when source is animated
_PHOTOREALISTIC_TOKENS = [
    r"\blive[\s-]?action\s*(meme\s*clips?)?\b",
    r"\breal[\s-]?human[s]?\b",
    r"\bphotorealistic\s*(human[s]?|actors?)?\b",
    r"\bphoto[\s-]?realistic\s*(human[s]?|actors?)?\b",
    r"\breal[\s-]?person\b",
    r"\breal[\s-]?people\b",
    r"\breal[\s-]?life\b",
    r"\bhyper[\s-]?realistic\b",
    r"\brealistic[\s-]?actor[s]?\b",
    r"\breal[\s-]?actor[s]?\b",
    r"\bhuman[\s-]?actor[s]?\b",
    r"\bordinary[\s-]?human[s]?\b",
]


def _is_animated_style(art_style: str) -> bool:
    """Return True if the extracted art_style indicates a non-photorealistic render."""
    lower = art_style.lower()
    return any(kw in lower for kw in _ANIMATED_INDICATORS)


def _sanitize_veo_prompt(
    prompt: str,
    art_style: str = "",
    character_design: str = "",
    is_animated: Optional[bool] = None
) -> str:
    """
    Post-process a veo_prompt to:
    1. Strip contradictory photorealistic keywords when source is animated (or is_animated=True).
    2. Clean both art_style and character_design of contradictory live-action keywords.
    3. Ensure the prompt starts with the canonical art_style + character_design prefix.
    4. Preserve all legitimate cinematic camera language.
    """
    sanitized_prompt = prompt
    clean_art_style = art_style or ""
    clean_char_design = character_design or ""

    should_strip = is_animated if is_animated is not None else _is_animated_style(clean_art_style)

    if should_strip:
        # Strip contradictory tokens from prompt
        for token_pattern in _PHOTOREALISTIC_TOKENS:
            sanitized_prompt = re.sub(token_pattern, "", sanitized_prompt, flags=re.IGNORECASE)
            if clean_art_style:
                clean_art_style = re.sub(token_pattern, "", clean_art_style, flags=re.IGNORECASE)
            if clean_char_design:
                clean_char_design = re.sub(token_pattern, "", clean_char_design, flags=re.IGNORECASE)
            
        if clean_art_style:
            clean_art_style = re.sub(r"(mixed|combined)?\s*(with|and)?\s*live[\s-]?action\s*(meme\s*clips?)?", "", clean_art_style, flags=re.IGNORECASE)
            clean_art_style = re.sub(r"  +", " ", clean_art_style).strip(" ,.-")
        if clean_char_design:
            clean_char_design = re.sub(r"  +", " ", clean_char_design).strip(" ,.-")
        sanitized_prompt = re.sub(r"  +", " ", sanitized_prompt).strip(" ,.-")

    # Enforce the canonical prefix if art_style/character_design provided and not already present
    prefix_parts = [p for p in [clean_art_style, clean_char_design] if p]
    if prefix_parts:
        prefix = ", ".join(prefix_parts).strip(" ,")
        check_prefix = clean_art_style[:15].lower() if clean_art_style else prefix[:15].lower()
        if not sanitized_prompt.lower().startswith(check_prefix):
            sanitized_prompt = f"{prefix}, {sanitized_prompt}".strip(" ,")

    # Ensure 9:16 orientation tag is present
    if "9:16" not in sanitized_prompt:
        sanitized_prompt += ", 9:16 vertical orientation, high quality render"

    return sanitized_prompt



# ─────────────────────────────────────────────────────────────
# MAIN REMIX FUNCTION
# ─────────────────────────────────────────────────────────────

def remix_trend(analysis: dict, niche: str) -> dict:
    """
    Takes the parsed TrendAnalysis dictionary and the target niche,
    and returns 3 concepts by prompting Gemini to output multi-scene
    shot arrays (2 to 5 distinct shots, like a real edited video).

    Each concept includes:
    - scenes[]: 2-5 SceneBeat objects with individual veo_prompts per shot
    - script[]: flattened dialogue lines (backward compat)
    - veo_prompt: the first scene's prompt (backward compat)
    """
    print(f"[Trend Remixer] Remixing trend for niche: {niche} (multi-scene mode)")

    art_style = analysis.get("art_style", "")
    character_design = analysis.get("character_design", "")
    humor = analysis.get("humor_mechanism", "")
    language = analysis.get("source_language", "Hindi")
    transcript = analysis.get("transcript_text", "")

    prompt = f"""
    You are a Master Viral Video Director and Content Strategist.
    We have analyzed a trending video. Your job is to CLONE this trend for the '{niche}' niche
    as a MULTI-SCENE production (2 to 5 distinct shots, like a real edited video).

    ORIGINAL VIDEO ANALYSIS:
    - Art Style: {art_style}
    - Character Design: {character_design}
    - Humor/Mechanics: {humor}
    - Language: {language}
    - Original Transcript: {transcript}

    Generate 3 distinct creative concepts adapted for '{niche}'.

    CRITICAL CONSTRAINTS:

    1. SCENES (3 to 5 per concept):
       Generate 3 to 5 scenes based on the comedic structure of the content. Typical order:
       - Scene 1: "wide_establish" — wide shot establishing the setting and characters (~5s)
       - Scene 2: "medium_interaction" — medium shot of the key comedic moment/interaction (~5s)
       - Scene 3: "punchline_closeup" — tight closeup on the punchline reaction (~5s)

       CRITICAL SHOT RULE: Every scene beat in `scenes` MUST feature ONLY the single character who is speaking that specific line. Do NOT use wide group shots during dialogue. If the Monkey is speaking, the `shot_type` MUST be 'close_up_monkey' and the `veo_prompt` MUST explicitly describe ONLY the Monkey talking.

       For EACH scene's veo_prompt:
       - MUST start with EXACT prefix: "{art_style}, {character_design},"
       - Describe the specific visual action for THAT SHOT ONLY (one camera angle, one moment)
       - Do NOT describe the full story in one scene — each scene is one cut
       - NEVER add "live-action", "real human", or "photorealistic" if art style is animated/3D/cartoon
       - End with ", 9:16 vertical orientation, high quality render"

    2. DIALOGUE (dialogue_lines per scene):
       CRITICAL LANGUAGE: MUST be conversational Hinglish (Roman script Hindi).
       - Assign each spoken line to the correct scene where it would be heard
       - Target Audience: Indian social media (Instagram Reels / TikTok)
       - Tone: Funny, expressive, regional Indian dialogue
       - No dialogue: leave list empty.
       - Multi-character: use "Male" and "Female" as voice labels
       - DO NOT invent literal names unless they matter to the plot.
       - Decide meme_overlay per line: 'laugh', 'crying', 'vine_boom', or 'none'
       - Expressive Delivery: Include heavy expressive punctuation (!, ?, ..., ,) so the TTS voice engine generates natural breath pauses and conversational cadence.
       - TOTAL dialogue across all scenes: MINIMUM 40 words, MAXIMUM 60 words (Must span at least 15 seconds of speech)

    3. HUMOR: Preserve the exact same humor mechanism: {humor}.
       Adapt the TOPIC to '{niche}' but keep the comedic formula identical.

    4. BRAND SAFETY (MANDATORY):
       Abstract the creative mechanic — do NOT reproduce specific character designs,
       exact shot compositions, on-screen branding, logos, or watermarks from the reference.
       Generate fully original visual designs INSPIRED by the style, not copied from it.

    Return STRICT JSON matching the requested schema.
    """

    client = get_gemini_client()

    generation_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ConceptList
    )

    try:
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt,
                config=generation_config
            )
        except Exception as e:
            print(f"[Trend Remixer] Gemini 3.6 Flash failed, falling back: {e}")
            response = client.models.generate_content(
                model=GEMINI_FALLBACK_MODEL,
                contents=prompt,
                config=generation_config
            )

        cleaned = re.sub(r'```json|```', '', response.text).strip()
        concepts_data = json.loads(cleaned)

        # --- POST-PROCESSING ---
        if "concepts" in concepts_data:
            for concept in concepts_data["concepts"]:
                # 1. Sanitize every scene's veo_prompt
                if "scenes" in concept and concept["scenes"]:
                    for scene in concept["scenes"]:
                        scene["veo_prompt"] = _sanitize_veo_prompt(
                            scene["veo_prompt"], art_style, character_design
                        )
                    # 2. Populate backward-compat flat fields
                    concept["veo_prompt"] = concept["scenes"][0]["veo_prompt"]
                    flat_lines = []
                    for scene in concept["scenes"]:
                        flat_lines.extend(scene.get("dialogue_lines", []))
                    concept["script"] = flat_lines
                # 3. Legacy support: if Gemini returned old flat veo_prompt instead of scenes
                elif "veo_prompt" in concept and not concept.get("scenes"):
                    concept["veo_prompt"] = _sanitize_veo_prompt(
                        concept["veo_prompt"], art_style, character_design
                    )

        print("[Trend Remixer] Multi-scene remix complete with prompt sanitization.")
        return concepts_data
    except Exception as e:
        print(f"[Trend Remixer] Error during Gemini remixing: {e}")
        raise
