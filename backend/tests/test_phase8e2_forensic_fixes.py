import os
import uuid
import pytest
from unittest.mock import MagicMock, patch

from core.models.blueprint import (
    ProductionBlueprint,
    SceneBlueprint,
    CameraDirection,
    DialogueLine,
    ContinuityRequirement,
    QualityStrategy
)
from core.models.clone_blueprint import CloneBlueprint, CloneSceneBlueprint, CloneShot, PacingProfile
from core.models.source_analysis import SourceVisualStyle, HookAnalysis, CTAAnalysis, SourceAudioProfile
from core.models.context import GenerationContext
from core.models.character import Character
from core.models.style import Style
from core.services.quality_reviewer import QualityReviewResult
from core.services.bible_loader import ResolvedScene
from core.services.prompt_compiler import PromptCompiler, normalize_enum_val
from core.services.reference_manager import ReferenceManager
from core.services.production_director import ProductionDirector
from core.models.transformation import ProductionTransformationRequest
from core.services.canonical_generation_engine import (
    CanonicalGenerationEngine,
    CanonicalGenerationRequest,
    CanonicalGenerationResult
)
from services.trend_remixer import _sanitize_veo_prompt


# ---------------------------------------------------------------------------
# 1 & 2. ENUM NORMALIZATION & TYPE SAFETY
# ---------------------------------------------------------------------------

def test_normalize_enum_val_various_types():
    assert normalize_enum_val(None) == ""
    assert normalize_enum_val(None, default="DEFAULT") == "DEFAULT"
    assert normalize_enum_val("WIDE") == "WIDE"
    
    class MockEnum:
        value = "DOLLY"
    
    assert normalize_enum_val(MockEnum()) == "DOLLY"
    assert normalize_enum_val(123) == "123"


def test_prompt_compiler_no_camera_direction_attribute_error():
    """Confirms 'CameraDirection' object has no attribute 'lower' is impossible."""
    cam = CameraDirection(
        shot_type="MEDIUM",
        lens="35mm",
        camera_motion="DOLLY",
        angle="SLIGHT_LOW",
        framing="WIDE_TWO_SHOT",
        depth_of_field="SHALLOW",
        lighting="BRIGHT_DAYLIGHT"
    )
    scene_bp = SceneBlueprint(
        scene_id="scn_test_001",
        scene_number=3,
        narrative_purpose="Punchline",
        estimated_duration_seconds=7.5,
        action="Padlock husband locks door with baby prop.",
        emotion="excited",
        environment="Front porch of house with traditional wooden door",
        camera=cam,
        scene_quality_priority="ACTION_CRITICAL"
    )
    resolved = ResolvedScene(
        scene=scene_bp,
        characters=[],
        voices=[],
        style=Style(style_id="sty_01", project_id="p1", name="Pixar", visual_style="3D Pixar-style digital animation"),
        location=None,
        props=[]
    )
    context = GenerationContext(user_id="u1", project_id="p1", job_id="j1")
    compiler = PromptCompiler()
    
    # Must compile cleanly without any exception
    compiled = compiler.compile(context, resolved, scene_blueprint=scene_bp)
    
    assert "MEDIUM SHOT" in compiled
    assert "35mm lens" in compiled
    assert "DOLLY camera motion" in compiled
    assert "SLIGHT_LOW angle" in compiled
    assert "WIDE_TWO_SHOT framing" in compiled
    assert "SHALLOW depth of field" in compiled
    assert "BRIGHT_DAYLIGHT" in compiled
    assert "Front porch of house with traditional wooden door" in compiled
    assert "Padlock husband locks door with baby prop." in compiled


# ---------------------------------------------------------------------------
# 3, 4, 5, 6, 7, 8. SCENE 3 COMPLETE STRUCTURED PROMPT PRESERVATION
# ---------------------------------------------------------------------------

def test_scene_3_structured_prompt_full_preservation():
    cam = CameraDirection(
        shot_type="MEDIUM",
        lens="35mm",
        camera_motion="DOLLY",
        angle="SLIGHT_LOW",
        framing="WIDE_TWO_SHOT",
        depth_of_field="SHALLOW",
        lighting="BRIGHT_DAYLIGHT"
    )
    scene_bp = SceneBlueprint(
        scene_id="scn_225ccfe5",
        scene_number=3,
        narrative_purpose="Deliver punchline by locking door with a baby human.",
        estimated_duration_seconds=7.467,
        action="Padlock wife reminds husband to secure the door; husband safely attaches a tiny human baby prop to the door handles as a lock.",
        emotion="excited",
        environment="Front porch of house with traditional wooden door",
        camera=cam,
        scene_quality_priority="ACTION_CRITICAL"
    )
    resolved = ResolvedScene(
        scene=scene_bp,
        characters=[],
        voices=[],
        style=Style(style_id="sty_01", project_id="p1", name="Pixar", visual_style="3D Pixar-style animation"),
        location=None,
        props=[]
    )
    context = GenerationContext(user_id="u1", project_id="p1", job_id="j1")
    compiler = PromptCompiler()
    
    compiled = compiler.compile(context, resolved, scene_blueprint=scene_bp)
    
    # Sanitize prompt using authoritative visual identity
    art_style = "3D Pixar-style animation"
    char_design = "3D anthropomorphic couple with brass padlock heads wearing modern and traditional Indian clothing"
    final_sanitized = _sanitize_veo_prompt(compiled, art_style, char_design)
    
    # Assertions on final compiled & sanitized prompt
    assert "3D Pixar-style animation" in final_sanitized
    assert "brass padlock heads" in final_sanitized
    assert "Front porch of house with traditional wooden door" in final_sanitized
    assert "Padlock wife reminds husband to secure the door" in final_sanitized
    assert "MEDIUM SHOT" in final_sanitized
    assert "DOLLY camera motion" in final_sanitized
    assert "BRIGHT_DAYLIGHT" in final_sanitized
    assert "9:16 vertical orientation" in final_sanitized
    assert "live-action" not in final_sanitized.lower()
    assert "real human" not in final_sanitized.lower()


# ---------------------------------------------------------------------------
# 9, 10, 11. CHARACTER REFERENCE GENERATION, CACHING & PASSAGE TO VEO
# ---------------------------------------------------------------------------

def test_reference_manager_fallback_generation_and_caching():
    ref_manager = ReferenceManager()
    context = GenerationContext(
        user_id="u1",
        project_id="p1",
        job_id="j1",
        metadata={
            "art_style": "3D Pixar-style animation",
            "character_design": "3D anthropomorphic couple with brass padlock heads"
        }
    )
    
    scene1_bp = SceneBlueprint(
        scene_id="scn_1", scene_number=1, narrative_purpose="Intro", estimated_duration_seconds=2.6,
        camera=CameraDirection(shot_type="MEDIUM")
    )
    scene2_bp = SceneBlueprint(
        scene_id="scn_2", scene_number=2, narrative_purpose="Reaction", estimated_duration_seconds=2.3,
        camera=CameraDirection(shot_type="CLOSE_UP")
    )
    
    resolved_scene_1 = ResolvedScene(scene=scene1_bp, characters=[], voices=[], style=None, location=None, props=[])
    resolved_scene_2 = ResolvedScene(scene=scene2_bp, characters=[], voices=[], style=None, location=None, props=[])
    
    with patch("services.asset_generator.generate_character_reference", return_value="gs://bucket/padlock_char_ref_001.png") as mock_gen:
        # Scene 1: should generate and cache
        ref1 = ref_manager.get_reference_uri(context, resolved_scene_1)
        assert ref1 == "gs://bucket/padlock_char_ref_001.png"
        assert mock_gen.call_count == 1
        
        # Scene 2: must reuse the EXACT same cached URI without generating again
        ref2 = ref_manager.get_reference_uri(context, resolved_scene_2)
        assert ref2 == "gs://bucket/padlock_char_ref_001.png"
        assert ref1 == ref2
        assert mock_gen.call_count == 1  # Not called again


def test_reference_uri_passed_to_veo():
    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1",
        project_id="p1",
        job_id="j1",
        scene_id="scn_1",
        raw_prompt="Padlock character steps outside",
        art_style="3D Pixar-style",
        character_design="Padlock head character",
        reference_image_uri="gs://bucket/padlock_char_ref_001.png",
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
         patch("core.repositories.attempt_repo.GenerationAttemptRepository.save"):
        
        result = engine.generate_scene(req)
        
        # Verify reference_image_uri was passed to generate_video_with_veo
        mock_veo.assert_called_once()
        _, kwargs = mock_veo.call_args
        assert kwargs["reference_image_uri"] == "gs://bucket/padlock_char_ref_001.png"
        assert kwargs["target_duration"] == 5


# ---------------------------------------------------------------------------
# 12 & 13. PRODUCTION BLUEPRINT IDENTITY & CONTEXT PROPAGATION
# ---------------------------------------------------------------------------

def test_production_blueprint_identity_propagation():
    director = ProductionDirector("u1", "p1")
    
    style_profile = SourceVisualStyle(
        art_style="3D Pixar-style animation",
        character_design="3D anthropomorphic couple with brass padlock heads",
        visual_style_summary="Vibrant 3D animation",
        lighting_summary="Sunny daylight",
        color_tone="Warm and saturated",
        realism_level="Stylized 3D"
    )
    
    clone_bp = CloneBlueprint(
        clone_blueprint_id="cl_001",
        source_video_id="src_001",
        project_id="p1",
        user_id="u1",
        source_analysis_version="1.0.0",
        title="Test Clone",
        source_duration_seconds=19.12,
        target_duration_seconds=19.12,
        aspect_ratio="9:16",
        hook=HookAnalysis(hook_type="ROLE_REVERSAL", confidence=0.9),
        pacing_profile=PacingProfile(overall_intensity="MEDIUM", average_shot_duration=3.8, fastest_shot_duration=2.3, slowest_shot_duration=7.5, scene_count=5, shot_count=5, rhythm_description=""),
        visual_style_profile=style_profile,
        audio_profile=SourceAudioProfile(has_speech=False),
        cta_structure=CTAAnalysis(exists=False),
        scenes=[]
    )
    
    req = ProductionTransformationRequest(
        topic="Role reversed locks",
        story_change="None",
        target_duration_seconds=19.12,
        preserve_characters=True
    )
    
    mock_pb = ProductionBlueprint(
        project_id="p1",
        title="Original Production",
        concept="Locks with baby",
        genre="Comedy",
        target_duration_seconds=19.12,
        scenes=[]
    )
    
    with patch("core.services.production_director.get_gemini_client") as mock_gemini, \
         patch.object(director.repo, "save"):
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = mock_pb.model_dump_json()
        mock_client.models.generate_content.return_value = mock_response
        mock_gemini.return_value = mock_client
        
        pb = director.transform_clone_blueprint(clone_bp, req)
        
        assert pb.visual_style_profile is not None
        assert pb.visual_style_profile.art_style == "3D Pixar-style animation"
        assert pb.authoritative_art_style == "3D Pixar-style animation"
        assert pb.authoritative_character_design == "3D anthropomorphic couple with brass padlock heads"
        assert pb.source_clone_blueprint_id == "cl_001"


# ---------------------------------------------------------------------------
# 14 & 15. DIALOGUE-PRESENT VS EMPTY DIALOGUE BEHAVIOR
# ---------------------------------------------------------------------------

def test_empty_dialogue_skips_elevenlabs():
    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1",
        project_id="p1",
        job_id="j1",
        scene_id="scn_no_dial",
        raw_prompt="Silent action shot",
        art_style="3D Pixar",
        character_design="Padlock man",
        dialogue_text="",  # Empty
        expected_duration=7.467
    )
    
    mock_review = QualityReviewResult(
        character_consistency=9.0, scene_adherence=9.0, visual_quality=9.0, continuity=9.0,
        overall=9.0, issues=[], recommended_action="accept"
    )
    
    with patch("services.elevenlabs_service.generate_voiceover") as mock_tts, \
         patch("core.services.canonical_generation_engine.generate_video_with_veo", return_value=b"video_bytes"), \
         patch.object(engine.quality_reviewer, "review_video", return_value=mock_review), \
         patch("core.repositories.attempt_repo.GenerationAttemptRepository.save"):
        
        result = engine.generate_scene(req)
        
        # ElevenLabs must NOT be called
        mock_tts.assert_not_called()
        assert result.audio_path is None
        assert result.audio_duration == 0.0


def test_dialogue_present_calls_elevenlabs():
    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1",
        project_id="p1",
        job_id="j1",
        scene_id="scn_with_dial",
        raw_prompt="Talking character",
        art_style="3D Pixar",
        character_design="Padlock man",
        dialogue_text="Did you remember to lock the front door?",
        speaker="Male",
        expected_duration=5.0
    )
    
    mock_review = QualityReviewResult(
        character_consistency=9.0, scene_adherence=9.0, visual_quality=9.0, continuity=9.0,
        overall=9.0, issues=[], recommended_action="accept"
    )
    
    with patch("core.services.canonical_generation_engine.generate_voiceover", return_value=r"d:\fake_audio.mp3") as mock_tts, \
         patch("os.path.exists", return_value=True), \
         patch("core.services.canonical_generation_engine.AudioFileClip") as mock_aclip, \
         patch("core.services.canonical_generation_engine.generate_video_with_veo", return_value=b"video_bytes"), \
         patch.object(engine.quality_reviewer, "review_video", return_value=mock_review), \
         patch("core.repositories.attempt_repo.GenerationAttemptRepository.save"):
        
        mock_clip_instance = MagicMock()
        mock_clip_instance.duration = 3.2
        mock_aclip.return_value.__enter__.return_value = mock_clip_instance
        
        result = engine.generate_scene(req)
        
        mock_tts.assert_called_once()
        assert result.audio_path == r"d:\fake_audio.mp3"
        assert result.audio_duration == 3.2


# ---------------------------------------------------------------------------
# 16 & 17. ADAPTIVE RETRY & HARD CAP = 1
# ---------------------------------------------------------------------------

def test_adaptive_retry_modifies_prompt_and_respects_hard_cap():
    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1",
        project_id="p1",
        job_id="j1",
        scene_id="scn_3",
        raw_prompt="Padlock husband attaches baby prop to door handles.",
        art_style="3D Pixar-style",
        character_design="Brass padlock couple",
        quality_priority="ACTION_CRITICAL",
        max_retries=1,  # Hard cap = 1 (2 attempts total)
        expected_duration=7.5
    )
    
    # Reviewer rejects Attempt 1 with action issues, then accepts Attempt 2
    review_reject = QualityReviewResult(
        character_consistency=8.0, scene_adherence=6.0, visual_quality=8.5, continuity=8.0,
        overall=6.0, issues=["Subject position unclear during door lock attachment"], recommended_action="reject"
    )
    review_accept = QualityReviewResult(
        character_consistency=9.0, scene_adherence=9.0, visual_quality=9.0, continuity=9.0,
        overall=8.9, issues=[], recommended_action="accept"
    )
    
    prompts_sent_to_veo = []
    
    def fake_veo(prompt, **kwargs):
        prompts_sent_to_veo.append(prompt)
        return b"fake_bytes"
    
    with patch("core.services.canonical_generation_engine.generate_video_with_veo", side_effect=fake_veo), \
         patch.object(engine.quality_reviewer, "review_video", side_effect=[review_reject, review_accept]), \
         patch("core.repositories.attempt_repo.GenerationAttemptRepository.save"):
        
        result = engine.generate_scene(req)
        
        assert len(prompts_sent_to_veo) == 2
        # Attempt 1 vs Attempt 2 must differ
        assert prompts_sent_to_veo[0] != prompts_sent_to_veo[1]
        # Attempt 2 must include targeted action-critical directive
        assert "DIRECTOR'S NOTE: Clarify physical action staging" in prompts_sent_to_veo[1]
        assert "Subject position unclear" in prompts_sent_to_veo[1]


# ---------------------------------------------------------------------------
# 18 & 19. GENERATION ATTEMPT AUDIT PERSISTENCE & ISOLATION
# ---------------------------------------------------------------------------

def test_generation_attempt_persisted_with_complete_telemetry():
    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1",
        project_id="p1",
        job_id="j1",
        scene_id="scn_audit_test",
        raw_prompt="Padlock character closes door",
        art_style="3D Pixar",
        character_design="Padlock couple",
        reference_image_uri="gs://bucket/ref.png",
        quality_priority="BALANCED",
        expected_duration=5.0
    )
    
    review_accept = QualityReviewResult(
        character_consistency=8.9, scene_adherence=8.5, visual_quality=8.8, continuity=8.7,
        overall=8.7, issues=[], recommended_action="accept"
    )
    
    saved_attempts = []
    
    def fake_save(user_id, project_id, attempt_id, attempt_doc):
        saved_attempts.append(attempt_doc.model_dump())
    
    with patch("core.services.canonical_generation_engine.generate_video_with_veo", return_value=b"fake_bytes"), \
         patch.object(engine.quality_reviewer, "review_video", return_value=review_accept), \
         patch("core.repositories.attempt_repo.GenerationAttemptRepository.save", side_effect=fake_save):
        
        result = engine.generate_scene(req)
        
        assert len(saved_attempts) >= 2  # At least 1 BEFORE provider call, 1 AFTER review
        first_save = saved_attempts[0]
        final_save = saved_attempts[-1]
        
        # Must record prompt and reference URI before call
        assert first_save["prompt"] != ""
        assert first_save["reference_uri"] == "gs://bucket/ref.png"
        assert first_save["status"] == "IN_PROGRESS"
        
        # Must record review score and completion after
        assert final_save["status"] == "COMPLETED"
        assert final_save["score"] == 8.7
        assert final_save["output_uri"] is not None
