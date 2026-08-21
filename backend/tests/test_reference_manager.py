import pytest
from unittest.mock import patch, MagicMock
from core.models.context import GenerationContext
from core.models.blueprint import SceneBlueprint, CameraDirection
from core.models.character import Character
from core.models.character_asset import CharacterAsset
from core.services.bible_loader import ResolvedScene
from core.services.reference_manager import ReferenceManager, ReferenceResolutionResult
from core.services.canonical_generation_engine import (
    CanonicalGenerationEngine,
    CanonicalGenerationRequest,
    CanonicalGenerationResult
)
from core.services.quality_reviewer import QualityReviewResult

# ---------------------------------------------------------------------------
# TEST 1: Existing Bible asset is reused
# ---------------------------------------------------------------------------
def test_existing_bible_asset_is_reused():
    ref_manager = ReferenceManager()
    context = GenerationContext(user_id="u1", project_id="p1", job_id="j1")
    
    char = Character(
        character_id="char_padlock_01",
        project_id="p1",
        name="Mr. Padlock",
        canonical_reference_uri="gs://shortcutai-bucket/characters/char_padlock_01/canonical_ref.jpg"
    )
    scene_bp = SceneBlueprint(scene_id="scn_1", scene_number=1, narrative_purpose="Intro", estimated_duration_seconds=2.6)
    resolved = ResolvedScene(scene=scene_bp, characters=[char], voices=[], style=None, location=None, props=[])
    
    with patch("services.asset_generator.generate_character_reference") as mock_gen:
        res = ref_manager.resolve_reference_with_telemetry(context, resolved)
        assert res.reference_uri == "gs://shortcutai-bucket/characters/char_padlock_01/canonical_ref.jpg"
        assert res.reference_source == "PROJECT_BIBLE"
        assert res.reference_validation_status == "VALID"
        assert mock_gen.call_count == 0  # Zero generation calls

# ---------------------------------------------------------------------------
# TEST 2 & 3: Missing Bible asset triggers exactly ONE generation and caches it
# ---------------------------------------------------------------------------
def test_missing_bible_asset_triggers_single_generation_and_caches():
    ref_manager = ReferenceManager()
    ref_manager.db = MagicMock()
    context = GenerationContext(
        user_id="u1", project_id="p1", job_id="j1",
        metadata={"art_style": "3D Pixar", "character_design": "Brass padlock head"}
    )
    
    char = Character(character_id="char_padlock_01", project_id="p1", name="Mr. Padlock", canonical_reference_uri=None)
    scene_bp = SceneBlueprint(scene_id="scn_1", scene_number=1, narrative_purpose="Intro", estimated_duration_seconds=2.6)
    resolved = ResolvedScene(scene=scene_bp, characters=[char], voices=[], style=None, location=None, props=[])
    
    generated_uri = "gs://shortcutai-bucket/users/u1/projects/p1/characters/char_padlock_01/canonical_ref_123.jpg"
    with patch("services.asset_generator.generate_character_reference", return_value=generated_uri) as mock_gen:
        res = ref_manager.resolve_reference_with_telemetry(context, resolved)
        
        assert res.reference_uri == generated_uri
        assert res.reference_source == "GENERATED_ASSET"
        assert res.reference_generation_status == "SUCCESS"
        assert res.reference_validation_status == "VALID"
        assert mock_gen.call_count == 1
        
        # Verify in-memory cache is populated
        assert context.metadata["reference_cache"]["char_padlock_01"] == generated_uri

# ---------------------------------------------------------------------------
# TEST 4 & 5: Multiple scenes reuse the exact same reference without re-generating
# ---------------------------------------------------------------------------
def test_multiple_scenes_reuse_same_character_reference():
    ref_manager = ReferenceManager()
    ref_manager.db = MagicMock()
    context = GenerationContext(
        user_id="u1", project_id="p1", job_id="j1",
        metadata={"art_style": "3D Pixar", "character_design": "Brass padlock head"}
    )
    
    char = Character(character_id="char_padlock_01", project_id="p1", name="Mr. Padlock")
    scene1 = ResolvedScene(scene=SceneBlueprint(scene_id="scn_1", scene_number=1, narrative_purpose="Beat 1", estimated_duration_seconds=2.5), characters=[char], voices=[], style=None, location=None, props=[])
    scene2 = ResolvedScene(scene=SceneBlueprint(scene_id="scn_2", scene_number=2, narrative_purpose="Beat 2", estimated_duration_seconds=2.5), characters=[char], voices=[], style=None, location=None, props=[])
    scene3 = ResolvedScene(scene=SceneBlueprint(scene_id="scn_3", scene_number=3, narrative_purpose="Beat 3", estimated_duration_seconds=2.5), characters=[char], voices=[], style=None, location=None, props=[])
    
    generated_uri = "gs://shortcutai-bucket/users/u1/projects/p1/characters/char_padlock_01/canonical_ref_123.jpg"
    with patch("services.asset_generator.generate_character_reference", return_value=generated_uri) as mock_gen:
        res1 = ref_manager.resolve_reference_with_telemetry(context, scene1)
        res2 = ref_manager.resolve_reference_with_telemetry(context, scene2)
        res3 = ref_manager.resolve_reference_with_telemetry(context, scene3)
        
        assert res1.reference_uri == generated_uri
        assert res2.reference_uri == generated_uri
        assert res3.reference_uri == generated_uri
        
        assert res1.reference_source == "GENERATED_ASSET"
        assert res2.reference_source == "CACHE"
        assert res3.reference_source == "CACHE"
        
        assert mock_gen.call_count == 1  # Called only once across all 3 scenes

# ---------------------------------------------------------------------------
# TEST 6: Multi-character support resolves separate references
# ---------------------------------------------------------------------------
def test_multiple_characters_receive_separate_references():
    ref_manager = ReferenceManager()
    ref_manager.db = MagicMock()
    context = GenerationContext(
        user_id="u1", project_id="p1", job_id="j1",
        metadata={"art_style": "3D Pixar"}
    )
    
    char_a = Character(character_id="char_padlock_husband", project_id="p1", name="Husband Padlock")
    char_b = Character(character_id="char_padlock_wife", project_id="p1", name="Wife Padlock")
    
    scene_a = ResolvedScene(scene=SceneBlueprint(scene_id="scn_1", scene_number=1, narrative_purpose="Husband intro", estimated_duration_seconds=2.5), characters=[char_a], voices=[], style=None, location=None, props=[])
    scene_b = ResolvedScene(scene=SceneBlueprint(scene_id="scn_2", scene_number=2, narrative_purpose="Wife reaction", estimated_duration_seconds=2.5), characters=[char_b], voices=[], style=None, location=None, props=[])
    
    def mock_generator_side_effect(subject, **kwargs):
        if "husband" in kwargs.get("character_id", ""):
            return "gs://bucket/husband_ref.jpg"
        return "gs://bucket/wife_ref.jpg"
        
    with patch("services.asset_generator.generate_character_reference", side_effect=mock_generator_side_effect) as mock_gen:
        res_a = ref_manager.resolve_reference_with_telemetry(context, scene_a)
        res_b = ref_manager.resolve_reference_with_telemetry(context, scene_b)
        
        assert res_a.reference_uri == "gs://bucket/husband_ref.jpg"
        assert res_b.reference_uri == "gs://bucket/wife_ref.jpg"
        assert res_a.character_id == "char_padlock_husband"
        assert res_b.character_id == "char_padlock_wife"
        assert mock_gen.call_count == 2
        
        # Verify both are cached under their own IDs
        assert context.metadata["reference_cache"]["char_padlock_husband"] == "gs://bucket/husband_ref.jpg"
        assert context.metadata["reference_cache"]["char_padlock_wife"] == "gs://bucket/wife_ref.jpg"

# ---------------------------------------------------------------------------
# TEST 7: Invalid URI scheme triggers validation failure and clean fallback
# ---------------------------------------------------------------------------
def test_invalid_uri_triggers_validation_failure():
    ref_manager = ReferenceManager()
    context = GenerationContext(user_id="u1", project_id="p1", job_id="j1")
    
    char = Character(
        character_id="char_bad_uri",
        project_id="p1",
        name="Bad URI Char",
        canonical_reference_uri="ftp://invalid-server/image.png"
    )
    scene_bp = SceneBlueprint(scene_id="scn_1", scene_number=1, narrative_purpose="Intro", estimated_duration_seconds=2.5)
    resolved = ResolvedScene(scene=scene_bp, characters=[char], voices=[], style=None, location=None, props=[])
    
    with patch("services.asset_generator.generate_character_reference", return_value=None):
        res = ref_manager.resolve_reference_with_telemetry(context, resolved)
        assert res.reference_uri is None
        assert res.fallback_mode == "PROMPT_ONLY"
        assert res.reference_failure_reason is not None

# ---------------------------------------------------------------------------
# TEST 8: Cross-tenant / wrong-user asset is rejected
# ---------------------------------------------------------------------------
def test_cross_tenant_asset_rejected():
    ref_manager = ReferenceManager()
    context = GenerationContext(user_id="user_legitimate_001", project_id="proj_001", job_id="j1")
    
    # Character references an asset path belonging to another user
    char = Character(
        character_id="char_victim",
        project_id="proj_001",
        name="Victim Char",
        canonical_reference_uri="gs://shortcutai-bucket/users/user_attacker_002/projects/proj_attacker/characters/secret.jpg"
    )
    scene_bp = SceneBlueprint(scene_id="scn_1", scene_number=1, narrative_purpose="Intro", estimated_duration_seconds=2.5)
    resolved = ResolvedScene(scene=scene_bp, characters=[char], voices=[], style=None, location=None, props=[])
    
    with patch("services.asset_generator.generate_character_reference", return_value=None):
        res = ref_manager.resolve_reference_with_telemetry(context, resolved)
        # Should be rejected because it belongs to user_attacker_002
        assert res.reference_uri is None
        assert res.fallback_mode == "PROMPT_ONLY"

# ---------------------------------------------------------------------------
# TEST 9: Reference generation failure produces structured fallback telemetry
# ---------------------------------------------------------------------------
def test_reference_generation_failure_produces_structured_fallback():
    ref_manager = ReferenceManager()
    ref_manager.db = MagicMock()
    context = GenerationContext(
        user_id="u1", project_id="p1", job_id="j1",
        metadata={"art_style": "3D Pixar", "character_design": "Brass padlock head"}
    )
    
    char = Character(character_id="char_padlock_01", project_id="p1", name="Mr. Padlock")
    scene_bp = SceneBlueprint(scene_id="scn_1", scene_number=1, narrative_purpose="Intro", estimated_duration_seconds=2.5)
    resolved = ResolvedScene(scene=scene_bp, characters=[char], voices=[], style=None, location=None, props=[])
    
    with patch("services.asset_generator.generate_character_reference", side_effect=RuntimeError("Provider 404")):
        res = ref_manager.resolve_reference_with_telemetry(context, resolved)
        
        assert res.reference_uri is None
        assert res.reference_generation_attempted is True
        assert res.reference_generation_status == "FAILED"
        assert "Provider 404" in (res.reference_failure_reason or "")
        assert res.fallback_mode == "PROMPT_ONLY"

# ---------------------------------------------------------------------------
# TEST 10: Veo receives the validated reference URI in CanonicalGenerationEngine
# ---------------------------------------------------------------------------
def test_veo_receives_validated_reference_uri():
    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1",
        project_id="p1",
        job_id="j1",
        scene_id="scn_1",
        raw_prompt="Padlock character steps outside",
        art_style="3D Pixar-style",
        character_design="Padlock head character",
        reference_image_uri="gs://shortcutai-bucket/characters/ref_001.jpg",
        reference_requested=True,
        reference_source="GENERATED_ASSET",
        reference_validation_status="VALID",
        dialogue_text="",
        quality_priority="ACTION_CRITICAL",
        expected_duration=5.0
    )
    
    mock_review = QualityReviewResult(
        character_consistency=9.0,
        scene_adherence=9.0,
        visual_quality=9.0,
        continuity=9.0,
        overall=9.0,
        issues=[],
        recommended_action="accept"
    )
    
    with patch("core.services.canonical_generation_engine.generate_video_with_veo", return_value=b"fake_mp4_bytes") as mock_veo, \
         patch.object(engine.quality_reviewer, "review_video", return_value=mock_review), \
         patch("core.repositories.attempt_repo.GenerationAttemptRepository.save") as mock_save_attempt:
        
        res = engine.generate_scene(req)
        assert res.status == "COMPLETED"
        assert mock_veo.call_count == 1
        
        # Verify kwargs passed to generate_video_with_veo
        call_kwargs = mock_veo.call_args.kwargs
        assert call_kwargs.get("reference_image_uri") == "gs://shortcutai-bucket/characters/ref_001.jpg"
        
        # Verify attempt telemetry saved with reference fields
        assert mock_save_attempt.call_count >= 1
        saved_attempt = mock_save_attempt.call_args[0][3]
        assert saved_attempt.reference_uri == "gs://shortcutai-bucket/characters/ref_001.jpg"
        assert saved_attempt.reference_source == "GENERATED_ASSET"
        assert saved_attempt.reference_validation_status == "VALID"

# ---------------------------------------------------------------------------
# TEST 11: Interleaved multi-character scene ordering preserves cached references
# ---------------------------------------------------------------------------
def test_interleaved_multi_character_scene_sequence():
    ref_manager = ReferenceManager()
    ref_manager.db = MagicMock()
    context = GenerationContext(user_id="u1", project_id="p1", job_id="j1")
    
    char_a = Character(character_id="char_A", project_id="p1", name="Character A")
    char_b = Character(character_id="char_B", project_id="p1", name="Character B")
    
    # Scene 1: Char A, Scene 2: Char B, Scene 3: Char A, Scene 4: Char B
    s1 = ResolvedScene(scene=SceneBlueprint(scene_id="s1", scene_number=1, narrative_purpose="A", estimated_duration_seconds=2.0), characters=[char_a], voices=[], style=None, location=None, props=[])
    s2 = ResolvedScene(scene=SceneBlueprint(scene_id="s2", scene_number=2, narrative_purpose="B", estimated_duration_seconds=2.0), characters=[char_b], voices=[], style=None, location=None, props=[])
    s3 = ResolvedScene(scene=SceneBlueprint(scene_id="s3", scene_number=3, narrative_purpose="A again", estimated_duration_seconds=2.0), characters=[char_a], voices=[], style=None, location=None, props=[])
    s4 = ResolvedScene(scene=SceneBlueprint(scene_id="s4", scene_number=4, narrative_purpose="B again", estimated_duration_seconds=2.0), characters=[char_b], voices=[], style=None, location=None, props=[])
    
    def mock_gen_cb(subject, **kwargs):
        c_id = kwargs.get("character_id", "")
        return f"gs://bucket/{c_id}_ref.jpg"
        
    with patch("services.asset_generator.generate_character_reference", side_effect=mock_gen_cb) as mock_gen:
        r1 = ref_manager.resolve_reference_with_telemetry(context, s1)
        r2 = ref_manager.resolve_reference_with_telemetry(context, s2)
        r3 = ref_manager.resolve_reference_with_telemetry(context, s3)
        r4 = ref_manager.resolve_reference_with_telemetry(context, s4)
        
        assert r1.reference_uri == "gs://bucket/char_A_ref.jpg"
        assert r2.reference_uri == "gs://bucket/char_B_ref.jpg"
        assert r3.reference_uri == "gs://bucket/char_A_ref.jpg"
        assert r4.reference_uri == "gs://bucket/char_B_ref.jpg"
        
        # Generation was called exactly twice (once for A, once for B)
        assert mock_gen.call_count == 2
