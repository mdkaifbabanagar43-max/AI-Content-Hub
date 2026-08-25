"""
P3 Phase A — SourceDNAAdapter tests
====================================
1. Round-trip mapping fidelity on a fully-populated fixture CloneBlueprint
2. Minimal-blueprint fallbacks (empty scenes/shots/beats)
3. STRICT NARRATIVE SEPARATION: planted transcript/dialogue/action tokens must
   never appear in any serialized cluster (schema §3 made executable)
4. SourceAnalysis ingestion path
5. TrendDNA merge bridge
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from types import SimpleNamespace

from core.models.clone_blueprint import (
    CloneBlueprint,
    CloneSceneBlueprint,
    CloneShot,
    NarrativeBeat,
    PacingProfile,
)
from core.models.dna import SourceDNACluster
from core.models.source_analysis import (
    HookAnalysis,
    CTAAnalysis,
    SourceAnalysis,
    SourceAudioProfile,
    SourceDialogueBeat,
    SourceMediaMetadata,
    SourceSceneSegment,
    SourceVisualStyle,
    SceneSemanticAnalysis,
)
from core.services.source_dna_adapter import (
    build_from_source_analysis,
    build_source_dna_cluster,
    merge_trend_dna,
)

# Planted narrative-prose tokens that must NEVER leak into DNA clusters
TOKEN_DIALOGUE = "ZEPHYR_DIALOGUE_TOKEN_9QF"
TOKEN_ACTION = "ZEPHYR_ACTION_TOKEN_4KD"
TOKEN_SPOKEN = "ZEPHYR_SPOKEN_TOKEN_7MB"
TOKEN_TRANSCRIPT = "ZEPHYR_TRANSCRIPT_TOKEN_2VX"


def _make_clone_blueprint() -> CloneBlueprint:
    vsp = SimpleNamespace(
        art_style="3D Pixar-style digital animation",
        character_design="Round-headed inventor in goggles",
        visual_style_summary="Glossy ANIMATION render",
        color_tone="Teal-orange",
        lighting_summary="Warm sunset rim light",
        animation_or_live_action="ANIMATION",
        realism_level="Semi-stylized",
        content_elements=None,
    )
    shots_s1 = [
        CloneShot(shot_number=1, source_start_seconds=0.0, source_end_seconds=2.5,
                  duration_seconds=2.5, shot_type="Wide", camera_motion="Static",
                  framing=None, lens_description=None, camera_angle=None,
                  composition=None, visual_action=f"Hero {TOKEN_ACTION} sprints",
                  transition="Hard cut"),
        CloneShot(shot_number=2, source_start_seconds=2.5, source_end_seconds=4.0,
                  duration_seconds=1.5, shot_type="Wide", camera_motion="Pan",
                  framing=None, lens_description=None, camera_angle=None,
                  composition=None, visual_action="Crowd reacts", transition=None),
    ]
    shots_s3 = [
        CloneShot(shot_number=5, source_start_seconds=16.0, source_end_seconds=20.0,
                  duration_seconds=4.0, shot_type="Close-up", camera_motion="Tracking",
                  framing=None, lens_description=None, camera_angle=None,
                  composition=None, visual_action="Goggles glint", transition="Whip pan"),
    ]
    scene = lambda n, sid, s0, s1_, shots, roles, loc, light: CloneSceneBlueprint(
        scene_id=sid, scene_number=n, source_start_seconds=s0, source_end_seconds=s1_,
        source_duration_seconds=s1_ - s0, narrative_purpose=f"Beat {n}",
        visual_action=f"Scene {n} prose {TOKEN_ACTION}", dialogue_intent=TOKEN_DIALOGUE,
        emotion="excited", pacing="FAST", shot_sequence=shots, character_roles=roles,
        location_summary=loc, prop_summary=None, lighting_summary=light, transition=None,
        audio_structure=None,
    )
    beats = [
        NarrativeBeat(type="HOOK", start_seconds=0.0, end_seconds=2.5, description="d", importance="HIGH"),
        NarrativeBeat(type="ESCALATION", start_seconds=2.5, end_seconds=6.0, description="d"),
        NarrativeBeat(type="TWIST", start_seconds=6.0, end_seconds=8.0, description="d", importance="HIGH"),
        NarrativeBeat(type="RESOLUTION", start_seconds=16.0, end_seconds=20.0, description="d"),
    ]

    return CloneBlueprint(
        clone_blueprint_id="cb_fixture_p3a",
        source_video_id="sv_fixture",
        project_id="proj_p3a",
        user_id="user_p3a",
        source_analysis_version="1.0.0",
        title="Fixture Blueprint",
        source_duration_seconds=20.0,
        target_duration_seconds=15.0,
        aspect_ratio="9:16",
        hook=HookAnalysis(hook_type="CONFLICT", hook_start_seconds=0.0,
                          hook_end_seconds=2.5, hook_description=None, confidence=0.9),
        narrative_structure=beats,
        pacing_profile=PacingProfile(
            overall_intensity="HIGH", average_shot_duration=2.0,
            fastest_shot_duration=0.8, slowest_shot_duration=4.5,
            scene_count=3, shot_count=3, rhythm_description="Snappy TOKEN_RHYTHM_2K",
        ),
        visual_style_profile=SourceVisualStyle(
            art_style=vsp.art_style, character_design=vsp.character_design,
            visual_style_summary=vsp.visual_style_summary, color_tone=vsp.color_tone,
            lighting_summary=vsp.lighting_summary,
            animation_or_live_action=vsp.animation_or_live_action,
            realism_level=vsp.realism_level, content_elements=None,
        ),
        audio_profile=SourceAudioProfile(has_speech=True, speech_tempo="FAST",
                                         has_background_music=True, music_mood="Tense",
                                         sfx_present=True),
        cta_structure=CTAAnalysis(exists=False, type="NONE"),
        scenes=[
            scene(1, "s1", 0.0, 8.0, shots_s1, ["PROTAGONIST", "SECONDARY_CHARACTER"],
                  "Downtown city street at night", "Neon practicals"),
            scene(2, "s2", 8.0, 16.0, [], [], None, None),
            scene(3, "s3", 16.0, 20.0, shots_s3, ["PROTAGONIST"], None, None),
        ],
    )


# ─────────────────────────────────────────────────────────────
# ROUND-TRIP MAPPING FIDELITY
# ─────────────────────────────────────────────────────────────
def test_visual_style_mapping():
    cluster = build_source_dna_cluster(_make_clone_blueprint())
    vs = cluster.visual_style
    assert vs.art_style == "3D Pixar-style digital animation"
    assert vs.render_language == "Glossy ANIMATION render"
    assert vs.lighting_style == "Warm sunset rim light"
    assert vs.color_palette == "Teal-orange"
    assert vs.realism_level == "Semi-stylized"


def test_camera_dominance_and_motions():
    cluster = build_source_dna_cluster(_make_clone_blueprint())
    assert cluster.camera_dna.dominant_shot_types[0] == "WIDE"      # 2 of 3 shots
    assert set(cluster.camera_dna.motion_styles) == {"STATIC", "PAN", "TRACKING"}


def test_pacing_cut_frequency_and_density():
    cluster = build_source_dna_cluster(_make_clone_blueprint())
    assert cluster.pacing_dna.average_shot_duration == 2.0
    assert cluster.pacing_dna.cut_frequency == "FAST"       # avg 2.0 <= 2.0
    assert cluster.editing_dna.visual_density == "HIGH"


def test_editing_transitions_and_framing():
    cluster = build_source_dna_cluster(_make_clone_blueprint())
    assert "HARD_CUT" in cluster.editing_dna.transition_styles
    assert "WHIP_PAN" in cluster.editing_dna.transition_styles
    # WIDE appears in 2 of 3 shots (66% >= 60%) -> CONSISTENT
    assert cluster.editing_dna.framing_consistency == "CONSISTENT"


def test_characters_roles_and_count():
    cluster = build_source_dna_cluster(_make_clone_blueprint())
    roles = [c["role"] for c in cluster.character_dna.characters]
    assert roles == ["PROTAGONIST", "SECONDARY_CHARACTER"]
    assert cluster.character_dna.source_character_count == 2


def test_environment_setting_heuristic():
    cluster = build_source_dna_cluster(_make_clone_blueprint())
    assert cluster.environment_dna.setting_type == "URBAN"
    assert cluster.environment_dna.environmental_mood == "Neon practicals"


def test_narrative_hook_beats_and_climax_position():
    cluster = build_source_dna_cluster(_make_clone_blueprint())
    ns = cluster.narrative_structure_dna
    assert ns.hook_duration_seconds == 2.5          # end - start
    assert ns.hook_intensity == "HIGH"              # confidence 0.9
    assert ns.total_beats == 4
    assert ns.beat_types.count("TWIST") == 1
    # TWIST midpoint (6+8)/2 = 7s of a 20s source -> 35%
    assert ns.climax_position_percent == pytest.approx(35.0)


def test_audio_profile_mapping():
    cluster = build_source_dna_cluster(_make_clone_blueprint())
    assert cluster.audio_dna.has_speech is True
    assert cluster.audio_dna.has_bgm is True
    assert cluster.audio_dna.music_mood == "Tense"
    assert cluster.audio_dna.sfx_density == "HIGH"


# ─────────────────────────────────────────────────────────────
# STRICT NARRATIVE SEPARATION (schema §3 executable)
# ─────────────────────────────────────────────────────────────
FORBIDDEN_TOKENS = (TOKEN_DIALOGUE, TOKEN_ACTION, TOKEN_SPOKEN, TOKEN_TRANSCRIPT)


def _assert_no_narrative_leak(cluster: SourceDNACluster):
    blob = cluster.model_dump_json()
    for token in FORBIDDEN_TOKENS:
        assert token not in blob, f"SEPARATION VIOLATION: {token} leaked into DNA cluster"


def test_separation_guarantee_on_clone_blueprint():
    _assert_no_narrative_leak(build_source_dna_cluster(_make_clone_blueprint()))


# ─────────────────────────────────────────────────────────────
# MINIMAL BLUEPRINT FALLBACKS
# ─────────────────────────────────────────────────────────────
def test_minimal_blueprint_yields_valid_cluster():
    minimal = CloneBlueprint(
        clone_blueprint_id="cb_min", source_video_id="sv", project_id="p", user_id="u",
        source_analysis_version="1.0.0",
        title="min", source_duration_seconds=10.0, target_duration_seconds=8.0,
        aspect_ratio="9:16",
        hook=HookAnalysis(hook_type="NONE", confidence=0.1),
        pacing_profile=PacingProfile(
            overall_intensity="LOW", average_shot_duration=5.5,
            fastest_shot_duration=4.0, slowest_shot_duration=7.0,
            scene_count=1, shot_count=1, rhythm_description="Calm",
        ),
        visual_style_profile=SourceVisualStyle(art_style="Anime", character_design="x"),
        audio_profile=SourceAudioProfile(),
        cta_structure=CTAAnalysis(exists=False, type="NONE"),
        scenes=[],
    )
    cluster = build_source_dna_cluster(minimal)
    assert cluster.character_dna.source_character_count == 1     # PROTAGONIST fallback
    assert cluster.camera_dna.dominant_shot_types == []
    assert cluster.editing_dna.transition_styles == ["CUT"]
    assert cluster.editing_dna.visual_density == "LOW"           # avg 5.5 > 4.5
    assert cluster.narrative_structure_dna.total_beats == 0
    assert cluster.narrative_structure_dna.climax_position_percent == 70.0
    _assert_no_narrative_leak(cluster)


# ─────────────────────────────────────────────────────────────
# SOURCEANALYSIS INGESTION PATH
# ─────────────────────────────────────────────────────────────
def _make_source_analysis() -> SourceAnalysis:
    semantic = [
        SceneSemanticAnalysis(
            scene_number=1, narrative_purpose="setup",
            visual_action=f"Prose {TOKEN_ACTION}", emotion="curious",
            pacing_intensity="MEDIUM", shot_type="WIDE", camera_motion="STATIC",
            character_roles=["PROTAGONIST"], location_summary="cozy kitchen interior",
            prop_summary=None, lighting_summary="Soft window light", transition=None,
            dialogue_intent=None,
        ),
        SceneSemanticAnalysis(
            scene_number=2, narrative_purpose="payoff",
            visual_action=f"More prose {TOKEN_ACTION}", emotion="excited",
            pacing_intensity="HIGH", shot_type="CLOSE_UP", camera_motion="PAN",
            character_roles=["PROTAGONIST", "NARRATOR"],
            location_summary=None, prop_summary=None, lighting_summary=None,
            transition="DISSOLVE", dialogue_intent=None,
        ),
    ]
    return SourceAnalysis(
        source_video_id="sv_sa",
        media_metadata=SourceMediaMetadata(
            duration_seconds=8.0, width=1080, height=1920, fps=30.0,
            aspect_ratio="9:16", has_audio=True,
        ),
        transcript_text=f"Spoken words {TOKEN_TRANSCRIPT} and more.",
        scenes=[
            SourceSceneSegment(scene_number=1, start_seconds=0.0, end_seconds=2.0,
                               duration_seconds=2.0),
            SourceSceneSegment(scene_number=2, start_seconds=2.0, end_seconds=8.0,
                               duration_seconds=6.0),
        ],
        semantic_scenes=semantic,
        hook=HookAnalysis(hook_type="MYSTERY", hook_start_seconds=0.0,
                          hook_end_seconds=1.5, confidence=0.55),
        cta=CTAAnalysis(exists=False, type="NONE"),
        visual_style=SourceVisualStyle(art_style="Claymation", character_design="x"),
        audio_profile=SourceAudioProfile(has_speech=True, sfx_present=False),
        dialogue_beats=[SourceDialogueBeat(text=TOKEN_SPOKEN)],
    )


def test_source_analysis_ingestion_path():
    analysis = _make_source_analysis()
    cluster = build_from_source_analysis(analysis)

    # Pacing derived from scene-segment durations: avg 4.0 -> MODERATE
    assert cluster.pacing_dna.average_shot_duration == 4.0
    assert cluster.pacing_dna.fastest_shot_duration == 2.0
    assert cluster.pacing_dna.slowest_shot_duration == 6.0
    assert cluster.pacing_dna.cut_frequency == "MODERATE"
    assert cluster.pacing_dna.overall_intensity == "HIGH"       # majority vote

    assert cluster.camera_dna.dominant_shot_types == ["WIDE", "CLOSE_UP"]
    assert set(cluster.camera_dna.motion_styles) == {"STATIC", "PAN"}
    roles = [c["role"] for c in cluster.character_dna.characters]
    assert roles == ["PROTAGONIST", "NARRATOR"]

    assert cluster.environment_dna.setting_type == "INTERIOR"
    assert cluster.editing_dna.transition_styles == ["DISSOLVE"]
    assert cluster.narrative_structure_dna.hook_duration_seconds == 1.5
    assert cluster.narrative_structure_dna.hook_intensity == "MEDIUM"

    _assert_no_narrative_leak(cluster)   # TOKEN_SPOKEN / TOKEN_TRANSCRIPT contained


def test_merge_trend_dna_from_dict_payload():
    cluster = build_source_dna_cluster(_make_clone_blueprint())
    payload = {
        "humor_mechanism": "Role reversal meme where tools act human",
        "pacing_scenes": [{"duration_seconds": 2.0}, {"duration_seconds": 2.0},
                          {"duration_seconds": 3.0}],
    }
    merged = merge_trend_dna(cluster, payload)
    assert merged.trend_dna is not None
    assert merged.trend_dna.viral_hook_type.startswith("Role reversal")
    assert merged.trend_dna.pacing_archetype == "RAPID"          # avg 2.33 <= 2.5
    assert merged.trend_dna.content_format == "SKIT"


def test_merge_trend_dna_object_payload_and_format_override():
    cluster = SourceDNACluster()
    payload = SimpleNamespace(
        humor_mechanism="Deadpan explainer gag",
        pacing_scenes=[SimpleNamespace(duration_seconds=9.0)],
    )
    merge_trend_dna(cluster, payload, content_format="EXPLAINER")
    assert cluster.trend_dna.content_format == "EXPLAINER"
    assert cluster.trend_dna.pacing_archetype == "DELIBERATE"    # 9s > 5s