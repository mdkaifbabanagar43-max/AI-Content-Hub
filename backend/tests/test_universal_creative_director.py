"""
P3 Phase B — UniversalCreativeDirector boundary tests
======================================================
1. GOLDEN DUAL-RUN: identical frozen LLM response replayed through the legacy
   director path AND the UCD boundary must produce structurally equivalent
   blueprints (volatile IDs/timestamps excluded).
2. Normalization contract: Q3 permanent dual-accept, profile-wins rule,
   story-mode mapping.
3. Prompt compiler toggle matrix + D3 MIXED degradation + separation scan.
4. ValidationPipeline gates: G2 leak detection, advisory findings.
"""
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.models.blueprint import ProductionBlueprint
from core.models.clone_intent import (
    CharacterMode,
    CreativeIntent,
    EnvironmentMode,
    StoryMode,
    CloneIntent,
    PreservationProfile,
)
from core.models.transformation import ProductionTransformationRequest
from core.models.transformation_context import (
    TransformationContext,
    effective_character_mode,
)
from core.services.production_director import ProductionDirector
from core.services.source_dna_adapter import build_source_dna_cluster
from core.services.universal_creative_director import UniversalCreativeDirector
from core.services.validation_pipeline import ValidationPipeline

# Reuse the rich Phase-A fixture (planted separation tokens included)
from test_source_dna_adapter import _make_clone_blueprint, FORBIDDEN_TOKENS

# A canned, fully-valid synthesis response (raccoon heist — zero narrative
# overlap with the fixture's source prose, so G3 passes cleanly).
CANNED_BLUEPRINT = {
    "project_id": "proj_golden",
    "title": "Pastry Heist in Paris",
    "concept": "Animated raccoons raid a croissant vault",
    "genre": "Comedy",
    "target_duration_seconds": 15.0,
    "aspect_ratio": "9:16",
    "scenes": [
        {"scene_id": "scn_1", "scene_number": 1,
         "narrative_purpose": "Hook", "estimated_duration_seconds": 5.0,
         "character_ids": ["char_lead_1"],
         "dialogue": [{"character_id": "char_lead_1",
                       "text": "We hit the croissant vault at midnight."}],
         "action": "Raccoons stack pastries into a getaway tower"},
        {"scene_id": "scn_2", "scene_number": 2,
         "narrative_purpose": "Escalation", "estimated_duration_seconds": 5.0,
         "character_ids": ["char_lead_1"], "dialogue": [],
         "action": "Limbo under a rolling-pin laser grid"},
        {"scene_id": "scn_3", "scene_number": 3,
         "narrative_purpose": "Resolution", "estimated_duration_seconds": 5.0,
         "character_ids": ["char_lead_1"], "dialogue": [],
         "action": "Escape down the Seine on a baguette raft"},
    ],
}

_VOLATILE_FIELDS = ("blueprint_id", "created_at", "updated_at",
                    "estimate_generated_at")


def _strip_volatile(bp: ProductionBlueprint) -> dict:
    data = bp.model_dump()
    for key in _VOLATILE_FIELDS:
        data.pop(key, None)
    # validation_report exists ONLY on the UCD path by design (Q4: metadata
    # attached post-synthesis); exclude it from structural equivalence.
    data.pop("validation_report", None)
    return data


def _make_offline_director(user="u_golden", project="proj_golden"):
    """Director whose LLM call, bible loads, entity checks and saves are inert."""
    director = ProductionDirector(user_id=user, project_id=project)
    frozen = json.dumps(CANNED_BLUEPRINT)
    director._invoke_story_model = MagicMock(return_value=frozen)
    director._build_planning_context = MagicMock(return_value="")
    director._validate_entities = MagicMock(return_value=[])
    director.repo.save = MagicMock()
    return director


def test_golden_dual_run_structural_equivalence():
    cb = _make_clone_blueprint()
    request = ProductionTransformationRequest(
        topic="Bitcoin Heist in Paris",
        clone_mode="custom",
        target_duration_seconds=15.0,
    )

    # ── OLD PATH: legacy director, inline prompt builder ──────────
    legacy = _make_offline_director()
    old_bp = legacy.transform_clone_blueprint(cb, request)

    # ── NEW PATH: UCD boundary, TransformationContext prompt ─────
    ucd = UniversalCreativeDirector(user_id="u_golden", project_id="proj_golden")
    ucd.director._invoke_story_model = MagicMock(
        return_value=json.dumps(CANNED_BLUEPRINT))
    ucd.director._validate_entities = MagicMock(return_value=[])
    ucd.director.repo.save = MagicMock()

    intent, merged = UniversalCreativeDirector.normalize_legacy(
        request, user_id="u_golden", project_id="proj_golden")
    assert merged is False
    new_bp = ucd.transform(cb, intent=intent)

    # Structural deep-diff (volatile identity/timestamps excluded)
    assert _strip_volatile(old_bp) == _strip_volatile(new_bp)

    # Boundary obligations on the new path only:
    assert new_bp.validation_report is not None
    gate_names = [g["name"] for g in new_bp.validation_report["gates"]]
    assert gate_names == ["G1_schema_pydantic", "G2_preservation_compliance",
                          "G3_narrative_originality", "G4_entity_bible_ids"]
    assert new_bp.validation_report["passed"] is True


# ─────────────────────────────────────────────────────────────
# NORMALIZATION CONTRACT (Q3 dual-accept, profile-wins)
# ─────────────────────────────────────────────────────────────
def test_normalize_legacy_defaults_map_to_modes():
    request = ProductionTransformationRequest(topic="t")
    intent, merged = UniversalCreativeDirector.normalize_legacy(
        request, user_id="u", project_id="p")
    assert merged is False
    assert intent.story_mode == StoryMode.STRUCTURE_INSPIRED  # preserve_structure default True
    assert intent.character_mode == CharacterMode.CREATE_NEW
    assert intent.environment_mode == EnvironmentMode.CREATE_NEW


def test_normalize_legacy_trend_and_new_story_mapping():
    trend_req = ProductionTransformationRequest(topic="t", preserve_trend_structure=True)
    intent_trend, _ = UniversalCreativeDirector.normalize_legacy(
        trend_req, user_id="u", project_id="p")
    assert intent_trend.story_mode == StoryMode.TREND_INSPIRED

    fresh_req = ProductionTransformationRequest(topic="t", preserve_structure=False)
    intent_fresh, _ = UniversalCreativeDirector.normalize_legacy(
        fresh_req, user_id="u", project_id="p")
    assert intent_fresh.story_mode == StoryMode.NEW_STORY


def test_profile_wins_conflict_tags_merged():
    """Profile block + legacy booleans together: profile wins, tag set."""
    request = ProductionTransformationRequest(
        topic="t",
        preservation_profile=PreservationProfile(preserve_characters=True),
        preserve_characters=False,  # legacy disagrees; explicitly provided
    )
    intent, merged = UniversalCreativeDirector.normalize_legacy(
        request, user_id="u", project_id="p")
    assert merged is True
    assert intent.preservation_profile.preserve_characters is True


# ─────────────────────────────────────────────────────────────
# PROMPT COMPILER — D3 degradation + separation scan
# ─────────────────────────────────────────────────────────────
def _intent_with(**overrides) -> CloneIntent:
    profile = PreservationProfile(**overrides.pop("profile", {}))
    return CloneIntent(
        user_id="u", project_id="p",
        character_mode=overrides.pop("character_mode", CharacterMode.CREATE_NEW),
        environment_mode=overrides.pop("environment_mode", EnvironmentMode.CREATE_NEW),
        story_mode=overrides.pop("story_mode", StoryMode.NEW_STORY),
        preservation_profile=profile,
        creative_intent=CreativeIntent(topic="Bank Heist in Paris"),
        requested_character_ids=overrides.pop(
            "requested_character_ids", ["char_requested_1"]),
        **overrides,
    )


def test_mixed_mode_degrades_to_requested_keep_list():
    intent = _intent_with(character_mode=CharacterMode.MIXED,
                          requested_character_ids=["char_requested_1"])
    assert effective_character_mode(intent) == CharacterMode.PRESERVE_SOURCE

    dna = build_source_dna_cluster(_make_clone_blueprint())
    prompt = TransformationContext().compile_prompt(intent, dna)
    assert "MIXED CHARACTER MODE (DEGRADED)" in prompt
    assert "char_requested_1" in prompt


def test_compiled_prompt_never_contains_source_narrative_prose():
    """Schema §3 at the string level: even ALL-PRESERVE prompts stay clean."""
    intent = _intent_with(profile={
        "preserve_visual_style": True, "preserve_environment": True,
        "preserve_camera_language": True, "preserve_pacing_editing": True,
    }, story_mode=StoryMode.STRUCTURE_INSPIRED)
    dna = build_source_dna_cluster(_make_clone_blueprint())
    prompt = TransformationContext().compile_prompt(intent, dna)
    for token in FORBIDDEN_TOKENS:
        assert token not in prompt, f"separation violation in compiled prompt: {token}"


# ─────────────────────────────────────────────────────────────
# PROMPT COMPILER — toggle matrix
# ─────────────────────────────────────────────────────────────
def test_toggle_matrix_injects_only_authorized_sections():
    cb = _make_clone_blueprint()
    dna = build_source_dna_cluster(cb)

    all_on_profile = {
        "preserve_visual_style": True, "preserve_characters": False,
        "preserve_environment": True, "preserve_camera_language": True,
        "preserve_pacing_editing": True, "preserve_audio_style": True,
        "preserve_voice_style": True, "preserve_trend_structure": True,
    }
    intent_on = _intent_with(profile=all_on_profile,
                             environment_mode=EnvironmentMode.PRESERVE_SOURCE,
                             story_mode=StoryMode.STRUCTURE_INSPIRED)
    prompt_on = TransformationContext().compile_prompt(intent_on, dna)
    for marker in ("SOURCE VISUAL STYLE (MANDATORY TO PRESERVE)",
                   "CAMERA LANGUAGE (PRESERVE)",
                   "PACING (PRESERVE RHYTHM)",
                   "AUDIO STYLE (PRESERVE)",
                   "VOICE STYLE (PRESERVE)",
                   "ENVIRONMENT (PRESERVE SOURCE WORLD)"):
        assert marker in prompt_on, f"missing section: {marker}"

    all_off_profile = {k: False for k in all_on_profile}
    intent_off = _intent_with(profile=all_off_profile)
    prompt_off = TransformationContext().compile_prompt(intent_off, dna)
    for marker in ("MANDATORY TO PRESERVE",
                   "CAMERA LANGUAGE (PRESERVE)",
                   "PACING (PRESERVE RHYTHM)",
                   "AUDIO STYLE (PRESERVE)",
                   "VOICE STYLE (PRESERVE)",
                   "ENVIRONMENT (PRESERVE SOURCE WORLD)"):
        assert marker not in prompt_off, f"unauthorized section leaked: {marker}"


# ─────────────────────────────────────────────────────────────
# VALIDATION PIPELINE GATES
# ─────────────────────────────────────────────────────────────
def _pipeline() -> ValidationPipeline:
    director = MagicMock()
    director._validate_entities = MagicMock(return_value=[])
    return ValidationPipeline(director)


def test_g2_flags_character_leak_when_not_preserving():
    pipeline = _pipeline()
    intent = _intent_with()  # characters NOT preserved
    source_bp = _make_clone_blueprint()

    leaked_bp = ProductionBlueprint(
        project_id="p", title="leak", concept="c", genre="Comedy",
        target_duration_seconds=5.0,
        required_character_ids=["PROTAGONIST"],
    )
    report = pipeline.run(intent, source_bp, leaked_bp,
                          context=SimpleNamespace())

    g2 = next(g for g in report.gates if g.name == "G2_preservation_compliance")
    assert g2.passed is False
    assert any("PROTAGONIST" in f for f in g2.findings)
    assert report.passed is False


def test_g2_advisory_findings_present_but_non_blocking():
    pipeline = _pipeline()
    intent = _intent_with()  # environment off -> advisory expected
    clean_bp = ProductionBlueprint(
        project_id="p", title="clean", concept="c", genre="Comedy",
        target_duration_seconds=5.0,
        required_character_ids=["char_lead_1"],
    )
    report = pipeline.run(intent, _make_clone_blueprint(), clean_bp,
                          context=SimpleNamespace())
    findings = report.findings_for("G2_preservation_compliance") \
        if hasattr(report, "findings_for") else [
            f for g in report.gates if g.name == "G2_preservation_compliance"
            for f in g.findings
        ]
    assert any(f.startswith("ADVISORY: environment") for f in findings)
    assert report.passed is True  # advisories never block


def test_transform_requires_intent_or_legacy_request():
    ucd = UniversalCreativeDirector()
    with pytest.raises(ValueError):
        ucd.transform(_make_clone_blueprint())


# ─────────────────────────────────────────────────────────────
# WOW-MOMENT VIRAL PROMPT ENGINEERING
# ─────────────────────────────────────────────────────────────
_ALL_OFF = {k: False for k in (
    "preserve_visual_style", "preserve_characters", "preserve_environment",
    "preserve_camera_language", "preserve_pacing_editing",
    "preserve_audio_style", "preserve_voice_style",
    "preserve_trend_structure")}


def test_wow_moment_craft_mandates_always_present():
    """Craft mandates carry zero source data -> safe under ANY toggle state."""
    dna = build_source_dna_cluster(_make_clone_blueprint())
    intent = _intent_with(profile=dict(_ALL_OFF))
    prompt = TransformationContext().compile_prompt(intent, dna)
    for marker in ("VIRAL RETENTION MANDATE - CINEMATIC VISUAL METAPHOR",
                   "THE WOW MOMENT (NON-NEGOTIABLE)",
                   "VEO CINEMATOGRAPHY CONTRACT"):
        assert marker in prompt


def test_hook_and_word_budget_gated_by_pacing_toggle():
    # Fixture DNA: hook 2.5s · average shot 2.0s -> cap = round(2.0*2.8) = 6
    dna = build_source_dna_cluster(_make_clone_blueprint())

    p_on = TransformationContext().compile_prompt(
        _intent_with(profile={"preserve_pacing_editing": True}), dna)
    assert "CADENCE IS KING" in p_on
    assert "first 2.5s" in p_on            # mirrors NarrativeStructureDNA hook
    assert "MUST NOT exceed 6 words" in p_on

    p_off = TransformationContext().compile_prompt(
        _intent_with(profile={"preserve_pacing_editing": False}), dna)
    assert "CADENCE IS KING" not in p_off
    assert "MUST NOT exceed" not in p_off  # unauthorized source-calibration leak


def test_wow_climax_exact_percent_only_when_structure_preserved():
    # Fixture DNA: TWIST midpoint 7s of 20s -> 35%
    dna = build_source_dna_cluster(_make_clone_blueprint())

    structured = _intent_with(story_mode=StoryMode.STRUCTURE_INSPIRED)
    p_struct = TransformationContext().compile_prompt(structured, dna)
    assert "at EXACTLY 35% of the runtime" in p_struct

    fresh = _intent_with(story_mode=StoryMode.NEW_STORY)
    p_fresh = TransformationContext().compile_prompt(fresh, dna)
    assert "between 65% and 80% of the runtime" in p_fresh