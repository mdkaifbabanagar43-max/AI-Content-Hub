"""
P3 Phase A — PreservationProfile parity tests (plan §5a matrix)
================================================================
Every row of the approved flag-mapping matrix becomes an executable assertion:
if the contract and the normalizer ever drift, these fail loudly.
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.models.clone_intent import (
    CharacterMode,
    CreativeIntent,
    EnvironmentMode,
    StoryMode,
    CloneIntent,
    PreservationProfile,
    build_preservation_profile,
)
from core.models.transformation import ProductionTransformationRequest
from config import ORIGINALITY_THRESHOLD


# ─────────────────────────────────────────────────────────────
# §5a PARITY TABLE — build_preservation_profile()
# ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "kwargs,expected",
    [
        # Row: pure defaults == spec defaults
        (
            {},
            dict(preserve_visual_style=True, preserve_characters=False,
                 preserve_environment=False, preserve_camera_language=True,
                 preserve_pacing_editing=True, preserve_audio_style=False,
                 preserve_voice_style=False, preserve_trend_structure=False),
        ),
        # Row: one legacy bit feeds TWO profile toggles (the critical split)
        (
            {"preserve_camera_pacing": False},
            dict(preserve_camera_language=False, preserve_pacing_editing=False),
        ),
        # Row: granular refinement ORs back into the split pair independently
        (
            {"preserve_camera_pacing": False, "preserve_camera_language": True},
            dict(preserve_camera_language=True, preserve_pacing_editing=False),
        ),
        (
            {"preserve_camera_pacing": False, "preserve_pacing": True},
            dict(preserve_camera_language=False, preserve_pacing_editing=True),
        ),
        # Row: forward-compat toggles pass through (prompt-directive no-ops today)
        (
            {"preserve_audio_style": True, "preserve_voice_style": True},
            dict(preserve_audio_style=True, preserve_voice_style=True),
        ),
        # Row: trend structure direct map
        (
            {"preserve_trend_structure": True},
            dict(preserve_trend_structure=True),
        ),
    ],
)
def test_parity_table(kwargs, expected):
    profile = build_preservation_profile(**kwargs)
    actual = profile.model_dump()
    for key, value in expected.items():
        assert actual[key] == value, f"parity drift on {key}: {actual} vs expected {expected}"


def test_full_visual_clone_splits_true():
    p = build_preservation_profile(
        preserve_visual_style=True, preserve_characters=True,
        preserve_environment=True, preserve_camera_pacing=True,
    )
    assert p.preserve_camera_language is True
    assert p.preserve_pacing_editing is True


def test_emotional_arc_accepted_as_noop():
    """Q3 dual-accept: granular emotional arc never breaks the mapper."""
    p = build_preservation_profile(preserve_emotional_arc=True)
    assert isinstance(p, PreservationProfile)


# ─────────────────────────────────────────────────────────────
# PRESET AUTO-SYNC via ProductionTransformationRequest (§5b)
# ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "mode,exp",
    [
        ("style_only", dict(style=True, chars=False, env=False, cam=True)),
        ("characters_and_style", dict(style=True, chars=True, env=False, cam=True)),
        ("full_visual_clone", dict(style=True, chars=True, env=True, cam=True)),
        ("trend_inspired", dict(style=False, chars=False, env=False, cam=True)),
        ("characters_only", dict(style=True, chars=True, env=False, cam=False)),  # Q2 gap-closer
    ],
)
def test_preset_auto_sync(mode, exp):
    req = ProductionTransformationRequest(clone_mode=mode)
    assert req.preserve_visual_style is exp["style"]
    assert req.preserve_characters is exp["chars"]
    assert req.preserve_environment is exp["env"]
    assert req.preserve_camera_pacing is exp["cam"]


def test_requested_character_ids_still_force_preserve():
    req = ProductionTransformationRequest(requested_character_ids=["char_hero"])
    assert req.preserve_characters is True


def test_originality_threshold_config_constant():
    """Q5: threshold centralized; default matches historical literal."""
    assert ORIGINALITY_THRESHOLD == pytest.approx(0.40)


# ─────────────────────────────────────────────────────────────
# MODE ENUMS + D3 ACCEPT-AND-DEGRADE CONTRACT
# ─────────────────────────────────────────────────────────────
def test_mixed_mode_accepted_and_stored():
    intent = CloneIntent(
        user_id="u1",
        project_id="p1",
        character_mode=CharacterMode.MIXED,
        creative_intent=CreativeIntent(topic="Bitcoin heist in Paris"),
        requested_character_ids=["char_lead_1"],
    )
    # Stored verbatim...
    assert intent.character_mode == CharacterMode.MIXED
    # ...and carries the subset the Phase-B degrader will intersect with.
    assert intent.requested_character_ids == ["char_lead_1"]


def test_story_and_environment_modes_available():
    assert StoryMode.TREND_INSPIRED.value == "TREND_INSPIRED"
    assert EnvironmentMode.ADAPT.value == "ADAPT"


def test_clone_intent_defaults_match_spec():
    intent = CloneIntent(
        user_id="u", project_id="p", creative_intent=CreativeIntent(topic="t")
    )
    assert intent.character_mode == CharacterMode.CREATE_NEW
    assert intent.environment_mode == EnvironmentMode.CREATE_NEW
    assert intent.story_mode == StoryMode.NEW_STORY
    assert intent.preservation_profile == PreservationProfile()