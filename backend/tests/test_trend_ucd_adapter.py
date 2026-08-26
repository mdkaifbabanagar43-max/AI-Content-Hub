"""
P3 Phase F - Trend Cloner UCD adapter tests
============================================
Gate semantics, intent/cluster mapping, overlay enrichment shape, and the
fail-closed transcript separation guard.
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch

from services.intent_adapters.trend_adapter import (
    TREND_SEPARATION_THRESHOLD,
    assert_dialogue_separation,
    build_trend_dna_cluster,
    build_trend_intent,
    remix_trend_via_ucd,
    use_ucd_trend,
)

ANALYSIS = {
    "art_style": "3D Pixar-style digital animation",
    "character_design": "TOKEN_DESIGN_5RW round raccoon chef",
    "humor_mechanism": "Role reversal where objects act human",
    "source_language": "Hinglish / Hindi",
    "transcript_text": "Aaj hum banayenge TOKEN_SPOKEN_PHRASE_8ZT duniya ka "
                       "sabse tasty cake.",
    "pacing_scenes": [
        {"duration_seconds": 2.0},
        {"duration_seconds": 2.5},
        {"duration_seconds": 3.0},
    ],
}


# ─────────────────────────────────────────────────────────────
# GATE SEMANTICS
# ─────────────────────────────────────────────────────────────
def test_gate_defaults_off():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("UCD_TREND_ENABLED", None)
        assert use_ucd_trend() is False


def test_gate_enabled_via_env():
    with patch.dict(os.environ, {"UCD_TREND_ENABLED": "1"}):
        assert use_ucd_trend() is True
    with patch.dict(os.environ, {"UCD_TREND_ENABLED": "true"}):
        assert use_ucd_trend() is True


# ─────────────────────────────────────────────────────────────
# INTENT + CLUSTER MAPPING
# ─────────────────────────────────────────────────────────────
def test_build_trend_intent_mapping():
    intent = build_trend_intent(ANALYSIS, user_id="u1", project_id="p1",
                                niche="Fitness")
    assert intent.story_mode.value == "TREND_INSPIRED"
    assert intent.preservation_profile.preserve_trend_structure is True
    assert intent.creative_intent.topic == "Fitness viral concept"
    assert intent.creative_intent.language == "Hinglish / Hindi"
    assert intent.creative_intent.target_duration_seconds == pytest.approx(7.5)


def test_build_trend_dna_cluster_mapping():
    cluster = build_trend_dna_cluster(ANALYSIS)
    assert cluster.visual_style.art_style == "3D Pixar-style digital animation"
    assert cluster.character_dna.characters[0]["visual_design"].startswith(
        "TOKEN_DESIGN_5RW")
    # avg pacing = 2.5s -> MODERATE cut frequency; archetype RAPID (<=2.5 band edge)
    assert cluster.pacing_dna.average_shot_duration == pytest.approx(2.5)
    assert cluster.pacing_dna.cut_frequency == "MODERATE"
    assert cluster.trend_dna.viral_hook_type == "Role reversal where objects act human"
    assert cluster.trend_dna.pacing_archetype == "RAPID"
    # Separation: no transcript prose inside the cluster
    blob = cluster.model_dump_json()
    assert "TOKEN_SPOKEN_PHRASE" not in blob


def test_retention_overlay_budget_from_avg():
    cluster = build_trend_dna_cluster(ANALYSIS)
    from services.intent_adapters.trend_adapter import _retention_overlay
    overlay = _retention_overlay(cluster)
    assert "CADENCE IS KING" in overlay
    assert "MUST NOT exceed 7 words" in overlay   # round(2.5 * 2.8) = 7


# ─────────────────────────────────────────────────────────────
# ENRICHMENT (shape-compatible with legacy remix output)
# ─────────────────────────────────────────────────────────────
def _canned_concepts(dialogue_text: str) -> dict:
    return {
        "concepts": [{
            "title": "Chef Raccoon Rumble",
            "description": "d",
            "scenes": [
                {"scene_id": 1, "shot_type": "wide_establish",
                 "veo_prompt": "Raccoon chef enters neon kitchen",
                 "duration_s": 4.0,
                 "dialogue_lines": [{"speaker": "Male",
                                     "text": dialogue_text,
                                     "meme_overlay": "none"}]},
                {"scene_id": 2, "shot_type": "punchline_closeup",
                 "veo_prompt": "Close-up victory grin",
                 "duration_s": 3.0, "dialogue_lines": []},
            ],
            "script": [], "veo_prompt": "",
            "outro_text_card": "Follow for more!",
        }]
    }


@patch("services.trend_remixer.remix_trend")
def test_remix_via_ucd_enriches_every_scene(mock_legacy):
    mock_legacy.return_value = _canned_concepts(
        "Naya swag laayenge aaj set par!")
    result = remix_trend_via_ucd(ANALYSIS, niche="Fitness")

    scene_prompts = [s["veo_prompt"] for s in result["concepts"][0]["scenes"]]
    assert len(scene_prompts) == 2
    for prompt in scene_prompts:
        assert "UCD VIRAL RETENTION OVERLAY" in prompt
        # Original creative content survives the overlay verbatim
        assert ("Raccoon chef enters neon kitchen" in prompt
                or "Close-up victory grin" in prompt)
        assert "9:16 vertical" in prompt          # sanitizer still applied
    # Backward-compat flat field synced to first scene
    assert result["concepts"][0]["veo_prompt"] == scene_prompts[0]
    mock_legacy.assert_called_once_with(ANALYSIS, "Fitness")  # positional, same as legacy router


# ─────────────────────────────────────────────────────────────
# SEPARATION GUARD (fail-closed)
# ─────────────────────────────────────────────────────────────
def test_separation_guard_passes_original_dialogue():
    analysis = dict(ANALYSIS)
    data = _canned_concepts("Naya swag laayenge aaj set par!")
    worst = assert_dialogue_separation(analysis, data)
    assert worst <= TREND_SEPARATION_THRESHOLD


def test_separation_guard_raises_on_transcript_copy():
    analysis = dict(ANALYSIS)
    copied = "Aaj hum banayenge duniya ka sabse tasty cake."
    data = _canned_concepts(copied)
    with pytest.raises(ValueError, match="separation violation"):
        assert_dialogue_separation(analysis, data)


def test_separation_guard_noop_without_transcript():
    analysis = dict(ANALYSIS)
    analysis["transcript_text"] = ""
    data = _canned_concepts("Kuch bhi bol do!")
    assert assert_dialogue_separation(analysis, data) == 0.0