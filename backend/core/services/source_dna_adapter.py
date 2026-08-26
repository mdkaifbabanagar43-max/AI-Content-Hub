"""
Source DNA Adapter — P3 Phase A
================================
Derives the nine spec'd DNA models from ALREADY-PERSISTED artifacts:

  - CloneBlueprint     (Video Cloner transform path — primary source)
  - SourceAnalysis     (ingestion-level analysis, richer scene semantics)
  - TrendAnalysis dict (legacy Trend Cloner — merged via merge_trend_dna)

STRICT NARRATIVE SEPARATION (schema §3): every builder copies ONLY structure,
timing, and style descriptors. Transcript text, dialogue-beat spoken text,
scene action prose, and narrative-beat descriptions are never copied into any
DNA. tests/test_source_dna_adapter.py::test_separation_guarantee enforces this
by scanning serialized clusters for planted transcript tokens.

All derivations are deterministic pure functions of their inputs (no I/O,
no LLM calls) so parity is testable forever.
"""
import re
from typing import Dict, Iterable, List, Optional

from core.models.clone_blueprint import CloneBlueprint
from core.models.dna import (
    AudioDNA,
    CameraDNA,
    CharacterDNA,
    EditingDNA,
    EnvironmentDNA,
    NarrativeStructureDNA,
    PacingDNA,
    SourceDNACluster,
    TrendDNA,
    VisualStyleDNA,
)

_CUT_FAST_S = 2.0          # avg shot duration at/below which cutting is FAST
_CUT_MODERATE_S = 4.0      # ... MODERATE band upper bound
_DENSITY_HIGH_S = 2.5      # visual density bands mirror cut frequency bands
_DENSITY_MEDIUM_S = 4.5

_SETTING_PATTERNS = (
    (re.compile(r"urban|street|city|downtown|skyline", re.I), "URBAN"),
    (re.compile(r"interior|room|kitchen|office|apartment|house|lab|garage", re.I), "INTERIOR"),
    (re.compile(r"studio", re.I), "STUDIO"),
    (re.compile(r"fantasy|magic|castle|dragon|enchanted", re.I), "FANTASY"),
    (re.compile(r"forest|nature|mountain|beach|field|jungle|desert", re.I), "NATURE"),
)


def _uniq_upper(values: Iterable[Optional[str]], drop: Iterable[str] = ("UNKNOWN", "")) -> List[str]:
    """Normalize to UPPER_SNAKE, drop empties/UNKNOWN, de-dupe preserving order."""
    out: List[str] = []
    dropped = {d.upper() for d in drop}
    for v in values:
        if not v:
            continue
        token = re.sub(r"[\s\-]+", "_", str(v)).strip("_").upper()
        if token and token not in dropped and token not in out:
            out.append(token)
    return out


def _cut_frequency(avg_shot_s: float) -> str:
    if avg_shot_s <= _CUT_FAST_S:
        return "FAST"
    if avg_shot_s <= _CUT_MODERATE_S:
        return "MODERATE"
    return "SLOW"


def _visual_density(avg_shot_s: float) -> str:
    if avg_shot_s <= _DENSITY_HIGH_S:
        return "HIGH"
    if avg_shot_s <= _DENSITY_MEDIUM_S:
        return "MEDIUM"
    return "LOW"


def _sfx_density(sfx_present: bool) -> str:
    # Binary source signal today; band widens when SFX counts exist upstream.
    return "HIGH" if sfx_present else "LOW"


def _setting_type(location_summary: str) -> str:
    for pattern, label in _SETTING_PATTERNS:
        if pattern.search(location_summary or ""):
            return label
    return "GENERIC"


def _first_non_null(*values: Optional[str]) -> Optional[str]:
    for v in values:
        if v:
            return v
    return None


def _dominant(items: List[str], limit: int = 3) -> List[str]:
    """Most-frequent-first ordering, ties broken by first appearance."""
    counts: Dict[str, int] = {}
    order: List[str] = []
    for it in items:
        if it not in counts:
            order.append(it)
        counts[it] = counts.get(it, 0) + 1
    ranked = sorted(order, key=lambda k: (-counts[k], order.index(k)))
    return ranked[:limit]


def _visual_style_from_clone(cb: CloneBlueprint) -> VisualStyleDNA:
    vsp = cb.visual_style_profile
    render = getattr(vsp, "visual_style_summary", None) or \
        f"{getattr(vsp, 'animation_or_live_action', None) or 'DIGITAL'} render"
    return VisualStyleDNA(
        art_style=getattr(vsp, "art_style", None) or "Cinematic digital animation",
        render_language=render,
        lighting_style=getattr(vsp, "lighting_summary", None) or "Cinematic lighting",
        color_palette=getattr(vsp, "color_tone", None) or "Natural",
        realism_level=getattr(vsp, "realism_level", None) or "Stylized",
        texture_detail=getattr(vsp, "content_elements", None),
    )


def _pacing_from_clone(cb: CloneBlueprint) -> PacingDNA:
    p = cb.pacing_profile
    avg = float(getattr(p, "average_shot_duration", 4.0) or 4.0)
    return PacingDNA(
        average_shot_duration=avg,
        fastest_shot_duration=float(getattr(p, "fastest_shot_duration", avg) or avg),
        slowest_shot_duration=float(getattr(p, "slowest_shot_duration", avg) or avg),
        cut_frequency=_cut_frequency(avg),
        rhythm_description=getattr(p, "rhythm_description", None) or "Dynamic narrative pacing",
        overall_intensity=getattr(p, "overall_intensity", None) or "Medium",
    )


def _camera_from_clone(cb: CloneBlueprint) -> CameraDNA:
    shot_types: List[str] = []
    motions: List[str] = []
    for scene in cb.scenes:
        for shot in scene.shot_sequence:
            shot_types.extend(_uniq_upper([getattr(shot, "shot_type", None)]))
            motions.extend(_uniq_upper([getattr(shot, "camera_motion", None)]))
    return CameraDNA(
        dominant_shot_types=_dominant(shot_types),
        motion_styles=_uniq_upper(motions),
        lens_character=None,
    )


def _editing_from_clone(cb: CloneBlueprint, avg_shot_s: float) -> EditingDNA:
    transitions: List[str] = []
    for scene in cb.scenes:
        transitions.extend(_uniq_upper([
            getattr(shot, "transition", None)
            for shot in scene.shot_sequence
            if getattr(shot, "transition", None)
        ]))
        transitions.extend(_uniq_upper([scene.transition]))

    shot_types: List[str] = [
        _uniq_upper([getattr(s, "shot_type", None)])[0]
        for s in (sh for sc in cb.scenes for sh in sc.shot_sequence)
        if _uniq_upper([getattr(s, "shot_type", None)])
    ]
    counts: Dict[str, int] = {}
    for st in shot_types:
        counts[st] = counts.get(st, 0) + 1
    total = sum(counts.values())
    framing = "CONSISTENT" if total and max(counts.values()) / total >= 0.6 else "VARIED"

    return EditingDNA(
        transition_styles=_uniq_upper(transitions) or ["CUT"],
        framing_consistency=framing,
        visual_density=_visual_density(avg_shot_s),
    )


def _characters_from_clone(cb: CloneBlueprint) -> CharacterDNA:
    # Flatten FIRST, then de-dupe once globally — a role recurring across
    # scenes must count exactly once (per-scene dedup would double-count).
    raw_roles: List[str] = []
    for scene in cb.scenes:
        raw_roles.extend(scene.character_roles or [])
    roles = _uniq_upper(raw_roles, drop=("UNKNOWN", ""))
    if not roles:
        roles = ["PROTAGONIST"]
    design = getattr(cb.visual_style_profile, "character_design", None) or \
        "Characters as they appear in the source video"
    return CharacterDNA(
        source_character_count=len(roles),
        characters=[{"role": role, "visual_design": design} for role in roles],
    )


def _environment_from_clone(cb: CloneBlueprint) -> EnvironmentDNA:
    location = _first_non_null(*(s.location_summary for s in cb.scenes))
    mood = _first_non_null(*(s.lighting_summary for s in cb.scenes)) or "Neutral"
    return EnvironmentDNA(
        setting_type=_setting_type(location or ""),
        architectural_style=None,
        environmental_mood=mood,
    )


_CLIMAX_TYPES = ("TWIST", "ESCALATION")


def _narrative_from_clone(cb: CloneBlueprint) -> NarrativeStructureDNA:
    hook = cb.hook
    start = getattr(hook, "hook_start_seconds", None)
    end = getattr(hook, "hook_end_seconds", None)
    duration = cb.source_duration_seconds or 0.0

    if start is not None and end is not None:
        hook_seconds = max(0.0, float(end) - float(start))
    elif start is not None:
        hook_seconds = min(3.0, max(0.0, duration - float(start)))
    else:
        hook_seconds = 0.0

    confidence = float(getattr(hook, "confidence", 0.0) or 0.0)
    intensity = "HIGH" if confidence >= 0.7 else ("MEDIUM" if confidence >= 0.4 else "LOW")

    beats = list(cb.narrative_structure)
    climax_pct = 70.0
    if beats and duration > 0:
        # The climax is the LAST climax-class beat (the peak just before
        # resolution), not merely the first ESCALATION on the way up.
        climax_beat = None
        for beat in beats:
            if getattr(beat, "type", "") in _CLIMAX_TYPES:
                climax_beat = beat
        if climax_beat is None:
            climax_beat = beats[-1]
        midpoint = (float(climax_beat.start_seconds) + float(climax_beat.end_seconds)) / 2.0
        climax_pct = round(max(0.0, min(100.0, midpoint / duration * 100.0)), 1)

    return NarrativeStructureDNA(
        hook_duration_seconds=round(hook_seconds, 2),
        hook_intensity=intensity,
        total_beats=len(beats),
        beat_types=[getattr(b, "type", "OTHER") for b in beats],
        climax_position_percent=climax_pct,
    )


def build_source_dna_cluster(clone_blueprint: CloneBlueprint) -> SourceDNACluster:
    """
    Primary Video-Cloner entrypoint: CloneBlueprint -> SourceDNACluster.
    Deterministic; safe to call on any persisted blueprint.
    """
    pacing = _pacing_from_clone(clone_blueprint)
    return SourceDNACluster(
        visual_style=_visual_style_from_clone(clone_blueprint),
        character_dna=_characters_from_clone(clone_blueprint),
        environment_dna=_environment_from_clone(clone_blueprint),
        camera_dna=_camera_from_clone(clone_blueprint),
        pacing_dna=pacing,
        editing_dna=_editing_from_clone(
            clone_blueprint, float(pacing.average_shot_duration)
        ),
        audio_dna=AudioDNA(
            has_speech=bool(getattr(clone_blueprint.audio_profile, "has_speech", False)),
            has_bgm=bool(getattr(clone_blueprint.audio_profile, "has_background_music", False)),
            music_mood=getattr(clone_blueprint.audio_profile, "music_mood", None),
            sfx_density=_sfx_density(bool(getattr(clone_blueprint.audio_profile, "sfx_present", False))),
        ),
        narrative_structure_dna=_narrative_from_clone(clone_blueprint),
        trend_dna=None,
    )


def merge_trend_dna(cluster: SourceDNACluster, trend_analysis, content_format: str = "SKIT") -> SourceDNACluster:
    """
    Legacy Trend-Cloner bridge: overlays TrendDNA onto a cluster from a
    TrendAnalysis payload (dict with humor_mechanism/pacing_scenes, or any
    object exposing the same attributes). Mutates and returns `cluster`.
    """
    def _get(source, key):
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    scenes = _get(trend_analysis, "pacing_scenes") or []
    durations = [float(_get(s, "duration_seconds") or 0.0) for s in scenes]
    durations = [d for d in durations if d > 0]
    avg = (sum(durations) / len(durations)) if durations else 4.0
    archetype = "RAPID" if avg <= 2.5 else ("STANDARD" if avg <= 5.0 else "DELIBERATE")

    cluster.trend_dna = TrendDNA(
        viral_hook_type=str(_get(trend_analysis, "humor_mechanism") or "UNKNOWN"),
        content_format=content_format,
        pacing_archetype=archetype,
    )
    return cluster


def build_from_source_analysis(analysis) -> SourceDNACluster:
    """
    Ingestion-level entrypoint: SourceAnalysis -> SourceDNACluster.
    Richer scene semantics than CloneBlueprint (shot types, camera motions,
    per-scene lighting/locations come from Gemini's semantic pass).
    """
    meta = analysis.media_metadata
    durations = [s.duration_seconds for s in analysis.scenes if s.duration_seconds > 0]
    avg = (sum(durations) / len(durations)) if durations else 4.0
    fastest = min(durations) if durations else avg
    slowest = max(durations) if durations else avg

    semantic = list(analysis.semantic_scenes)
    shot_types = _uniq_upper([getattr(s, "shot_type", None) for s in semantic])
    motions = _uniq_upper([getattr(s, "camera_motion", None) for s in semantic])

    roles: List[str] = []
    for s in semantic:
        roles.extend(_uniq_upper(getattr(s, "character_roles", []), drop=("UNKNOWN", "")))
    design = getattr(analysis.visual_style, "character_design", None) or \
        "Characters as they appear in the source video"
    role_list = _uniq_upper(roles) or ["PROTAGONIST"]

    location = _first_non_null(*(getattr(s, "location_summary", None) for s in semantic))
    mood = _first_non_null(*(getattr(s, "lighting_summary", None) for s in semantic)) or "Neutral"

    transitions = _uniq_upper([getattr(s, "transition", None) for s in semantic])
    # Overall intensity = strongest signal, ties broken toward the LATER scene
    # (escalation bias — short-form content peaks late).
    _INTENSITY_RANK = {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CLIMACTIC": 4}
    best_idx, best_rank = -1, -1
    for idx, s in enumerate(semantic):
        raw = str(getattr(s, "pacing_intensity", "MEDIUM")).upper()
        rank = _INTENSITY_RANK.get(raw, 0)
        if rank >= best_rank:
            best_rank, best_idx = rank, idx
    overall_intensity = (
        str(getattr(semantic[best_idx], "pacing_intensity", "MEDIUM")).upper()
        if best_idx >= 0 else "MEDIUM"
    )

    duration_total = float(meta.duration_seconds or 0.0)
    climax_pct = 70.0
    if analysis.scenes and duration_total > 0:
        # Timestamps live on SourceSceneSegment, NOT on SceneSemanticAnalysis.
        first_seg, last_seg = analysis.scenes[0], analysis.scenes[-1]
        midpoint = (float(first_seg.start_seconds) + float(last_seg.end_seconds)) / 2.0
        climax_pct = round(max(0.0, min(100.0, midpoint / duration_total * 100.0)), 1)

    hook = analysis.hook
    hs, he = getattr(hook, "hook_start_seconds", None), getattr(hook, "hook_end_seconds", None)
    hook_seconds = max(0.0, float(he) - float(hs)) if (hs is not None and he is not None) else 0.0
    confidence = float(getattr(hook, "confidence", 0.0) or 0.0)

    audio = analysis.audio_profile
    dominant_one = _dominant(shot_types, limit=1)
    consistent = bool(
        dominant_one and shot_types.count(dominant_one[0]) >= 0.6 * max(len(shot_types), 1)
    )

    return SourceDNACluster(
        visual_style=VisualStyleDNA(
            art_style=getattr(analysis.visual_style, "art_style", None) or "Cinematic digital animation",
            render_language=getattr(analysis.visual_style, "visual_style_summary", None)
            or f"{getattr(analysis.visual_style, 'animation_or_live_action', None) or 'DIGITAL'} render",
            lighting_style=getattr(analysis.visual_style, "lighting_summary", None) or "Cinematic lighting",
            color_palette=getattr(analysis.visual_style, "color_tone", None) or "Natural",
            realism_level=getattr(analysis.visual_style, "realism_level", None) or "Stylized",
            texture_detail=getattr(analysis.visual_style, "content_elements", None),
        ),
        character_dna=CharacterDNA(
            source_character_count=len(role_list),
            characters=[{"role": r, "visual_design": design} for r in role_list],
        ),
        environment_dna=EnvironmentDNA(
            setting_type=_setting_type(location or ""),
            architectural_style=None,
            environmental_mood=mood,
        ),
        camera_dna=CameraDNA(
            dominant_shot_types=_dominant(shot_types),
            motion_styles=motions,
            lens_character=None,
        ),
        pacing_dna=PacingDNA(
            average_shot_duration=round(avg, 3),
            fastest_shot_duration=float(fastest),
            slowest_shot_duration=float(slowest),
            cut_frequency=_cut_frequency(avg),
            rhythm_description=f"{len(durations)}-scene native cut rhythm",
            overall_intensity=overall_intensity,
        ),
        editing_dna=EditingDNA(
            transition_styles=transitions or ["CUT"],
            framing_consistency="CONSISTENT" if consistent else "VARIED",
            visual_density=_visual_density(avg),
        ),
        audio_dna=AudioDNA(
            has_speech=bool(getattr(audio, "has_speech", False)),
            has_bgm=bool(getattr(audio, "has_background_music", False)),
            music_mood=getattr(audio, "music_mood", None),
            sfx_density=_sfx_density(bool(getattr(audio, "sfx_present", False))),
        ),
        narrative_structure_dna=NarrativeStructureDNA(
            hook_duration_seconds=round(hook_seconds, 2),
            hook_intensity="HIGH" if confidence >= 0.7 else ("MEDIUM" if confidence >= 0.4 else "LOW"),
            total_beats=len(semantic),
            beat_types=[],
            climax_position_percent=climax_pct,
        ),
        trend_dna=None,
    )