"""
Trend Cloner UCD Adapter — P3 Phase F
======================================
Flag-gated adoption path (env: UCD_TREND_ENABLED, default OFF).

When enabled, /api/trend-cloner/analyze routes its creative step through
this adapter instead of calling services.trend_remixer.remix_trend()
directly:

  1. Legacy remix_trend() still produces the STRUCTURE (scene beats,
     Hinglish dialogue, style-anchored veo prompts) - zero shape change.
  2. UCD OVERLAY: every scene's veo_prompt is prepended with the
     wow-moment retention directives compiled from a TrendAnalysis-derived
     SourceDNACluster (CADENCE IS KING word budgets, CINEMATIC VISUAL
     METAPHOR duty, curiosity-loop framing), then re-sanitized with the
     same style anchors.
  3. SEPARATION GUARD: generated dialogue is token-compared against the
     source transcript; overlap above TREND_SEPARATION_THRESHOLD fails
     CLOSED (ValueError) instead of serving a near-copy of the original.

Flag-OFF behavior is byte-identical: the router branch is not taken and
this module is never imported on that path.
"""
import os
from typing import Any, Dict

from core.models.clone_intent import (
    CharacterMode,
    CreativeIntent,
    EnvironmentMode,
    StoryMode,
    CloneIntent,
    build_preservation_profile,
)
from core.models.dna import (
    CameraDNA,
    CharacterDNA,
    PacingDNA,
    SourceDNACluster,
    VisualStyleDNA,
)
from core.models.transformation_context import TransformationContext  # noqa: F401 (re-exported for adapter consumers)
from core.services.source_dna_adapter import merge_trend_dna

UCD_TREND_FLAG = "UCD_TREND_ENABLED"

# Transcript-level copying is the direct-clone risk for Trend users, so the
# ceiling here is deliberately stricter than the blueprint-level 0.40.
TREND_SEPARATION_THRESHOLD = 0.30


def use_ucd_trend() -> bool:
    """Reads the Phase-F gate. Default OFF => byte-identical legacy path."""
    return os.getenv(UCD_TREND_FLAG, "0").strip().lower() in ("1", "true", "yes")


def _get(source: Any, key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)


def build_trend_intent(analysis: Any, *, user_id: str = "",
                       project_id: str = "", niche: str = "General",
                       topic: str = None) -> CloneIntent:
    """TREND_INSPIRED CloneIntent: structure preserved, story invented."""
    profile = build_preservation_profile(preserve_trend_structure=True)
    scenes = _get(analysis, "pacing_scenes") or []
    durations = [float(_get(s, "duration_seconds") or 0.0) for s in scenes]
    total = sum(d for d in durations if d > 0) or None
    return CloneIntent(
        user_id=user_id,
        project_id=project_id,
        preservation_profile=profile,
        character_mode=CharacterMode.CREATE_NEW,
        environment_mode=EnvironmentMode.CREATE_NEW,
        story_mode=StoryMode.TREND_INSPIRED,
        creative_intent=CreativeIntent(
            topic=topic or f"{niche} viral concept",
            language=str(_get(analysis, "source_language")
                         or "Hinglish / Hindi"),
            target_duration_seconds=total,
        ),
    )


def build_trend_dna_cluster(analysis: Any) -> SourceDNACluster:
    """
    TrendAnalysis -> SourceDNACluster (visual/camera/character/pacing),
    with TrendDNA filled by the shared merge_trend_dna bridge.
    Carries NO transcript/dialogue prose (schema section-3 guarantee).
    """
    art_style = str(_get(analysis, "art_style")
                    or "Cinematic digital animation")
    design = str(_get(analysis, "character_design")
                 or "Characters as they appear in the source video")

    scenes = _get(analysis, "pacing_scenes") or []
    durations = [float(_get(s, "duration_seconds") or 0.0) for s in scenes]
    durations = [d for d in durations if d > 0]
    avg = (sum(durations) / len(durations)) if durations else 4.0

    cluster = SourceDNACluster(
        visual_style=VisualStyleDNA(
            art_style=art_style,
            render_language=f"{art_style} render",
            lighting_style="Source-matched lighting",
            color_palette="Source-matched palette",
            realism_level="Stylized",
        ),
        character_dna=CharacterDNA(
            source_character_count=1,
            characters=[{"role": "PROTAGONIST", "visual_design": design}],
        ),
        camera_dna=CameraDNA(),   # legacy trend flow has no shot telemetry
        pacing_dna=PacingDNA(
            average_shot_duration=avg,
            fastest_shot_duration=min(durations) if durations else avg,
            slowest_shot_duration=max(durations) if durations else avg,
            cut_frequency="FAST" if avg <= 2.0 else (
                "MODERATE" if avg <= 4.0 else "SLOW"),
            rhythm_description="Legacy trend pacing profile",
            overall_intensity="HIGH",
        ),
        audio_dna=None,
        narrative_structure_dna=None,
    )
    return merge_trend_dna(cluster, analysis)


def _retention_overlay(cluster: SourceDNACluster) -> str:
    """Compact per-shot wow-moment overlay (no source prose - Veo-safe)."""
    trend = cluster.trend_dna
    pacing = cluster.pacing_dna
    avg = pacing.average_shot_duration if pacing else 4.0
    cap = max(3, int(round(avg * 2.8)))
    hook = trend.viral_hook_type if trend else "HIGH STAKES opening"
    archetype = trend.pacing_archetype if trend else "RAPID"
    return (
        "UCD VIRAL RETENTION OVERLAY - apply to THIS shot:\n"
        f"- HOOK ENERGY ({archetype}): {hook}. Land the tension "
        "inside the first seconds (3-SECOND RULE).\n"
        f"- CADENCE IS KING: any spoken line in this shot MUST NOT exceed "
        f"{cap} words (~{avg:.1f}s of screen time).\n"
        "- Carry ONE CINEMATIC VISUAL METAPHOR for the topic tension; "
        "escalate its scale versus the previous shot.\n"
        "- Compose final frames as a curiosity loop into the next beat; "
        "Veo-cinematic framing, dramatic lighting shift."
    )


def remix_trend_via_ucd(analysis: Any, niche: str = "General") -> Dict[str, Any]:
    """
    Flag-gated Phase-F entrypoint. Returns EXACTLY the legacy
    remix_trend() shape ({concepts: [...]}) enriched per scene with the
    UCD retention overlay, and hard-fails on transcript plagiarism.
    """
    # Lazy import keeps the OFF path free of any new-module cost.
    from services.trend_remixer import remix_trend as _legacy_remix
    from services.trend_remixer import _sanitize_veo_prompt

    concepts_data = _legacy_remix(analysis, niche)

    cluster = build_trend_dna_cluster(analysis)
    overlay = _retention_overlay(cluster)
    art_style = str(_get(analysis, "art_style") or "")
    design = str(_get(analysis, "character_design") or "")

    for concept in concepts_data.get("concepts", []):
        for scene in concept.get("scenes", []):
            original = scene.get("veo_prompt", "")
            enriched = _sanitize_veo_prompt(
                f"{overlay}\n{original}", art_style, design
            )
            scene["veo_prompt"] = enriched
        # Keep the backward-compat flat field pointing at the first scene.
        if concept.get("scenes"):
            concept["veo_prompt"] = concept["scenes"][0]["veo_prompt"]

    assert_dialogue_separation(analysis, concepts_data)
    return concepts_data


def assert_dialogue_separation(analysis: Any,
                               concepts_data: Dict[str, Any]) -> float:
    """
    Fail-closed separation guard: generated dialogue must not tokenize-
    overlap the source transcript beyond TREND_SEPARATION_THRESHOLD.
    Returns the worst overlap observed. Raises ValueError on violation so
    /analyze surfaces the failure instead of serving a near-copy.
    """
    from core.services.originality_validator import _tokenize_narrative

    transcript = str(_get(analysis, "transcript_text") or "")
    source_tokens = _tokenize_narrative(transcript)
    if not source_tokens:
        return 0.0

    worst = 0.0
    for concept in concepts_data.get("concepts", []):
        for scene in concept.get("scenes", []):
            generated_text = " ".join(
                str(_get(line, "text") or "")
                for line in scene.get("dialogue_lines", [])
            )
            generated_tokens = _tokenize_narrative(generated_text)
            if not generated_tokens:
                continue
            overlap = len(source_tokens & generated_tokens) / len(generated_tokens)
            worst = max(worst, overlap)
            if overlap > TREND_SEPARATION_THRESHOLD:
                raise ValueError(
                    "Trend separation violation: generated dialogue overlaps "
                    f"source transcript {overlap:.2f} > "
                    f"{TREND_SEPARATION_THRESHOLD:.2f} threshold."
                )
    return worst