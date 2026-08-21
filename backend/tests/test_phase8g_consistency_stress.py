import pytest
from unittest.mock import patch, MagicMock
import os

from core.models.context import GenerationContext
from core.models.blueprint import (
    ProductionBlueprint,
    SceneBlueprint,
    CameraDirection,
    DialogueLine,
    QualityStrategy
)
from core.models.character import Character
from core.models.voice import Voice
from core.services.bible_loader import ResolvedScene
from core.services.reference_manager import ReferenceManager
from core.services.prompt_compiler import PromptCompiler
from core.services.canonical_generation_engine import (
    CanonicalGenerationEngine,
    CanonicalGenerationRequest,
    CanonicalGenerationResult
)
from core.services.quality_reviewer import QualityReviewResult
from core.services.timeline_builder import TimelineBuilder
from services.trend_remixer import _sanitize_veo_prompt

# ===========================================================================
# 8-SCENE SYNTHETIC 30–60 SECOND TEST SCENARIO
# ===========================================================================

def build_phase8g_test_blueprint() -> ProductionBlueprint:
    """
    Constructs the controlled 8-scene (41s total) synthetic blueprint
    featuring two recurring characters (Mr. Brass Padlock & Mrs. Silver Padlock).
    """
    cam_tracking = CameraDirection(shot_type="MEDIUM", lens="35mm", camera_motion="TRACKING", angle="EYE_LEVEL", framing="CENTERED", depth_of_field="SHALLOW", lighting="BRIGHT_DAYLIGHT")
    cam_wide = CameraDirection(shot_type="WIDE", lens="24mm", camera_motion="STATIC", angle="EYE_LEVEL", framing="WIDE_TWO_SHOT", depth_of_field="MEDIUM", lighting="BRIGHT_DAYLIGHT")
    cam_close = CameraDirection(shot_type="CLOSE_UP", lens="50mm", camera_motion="STATIC", angle="EYE_LEVEL", framing="TIGHT", depth_of_field="SHALLOW", lighting="BRIGHT_DAYLIGHT")
    cam_dolly = CameraDirection(shot_type="MEDIUM", lens="35mm", camera_motion="DOLLY", angle="SLIGHT_LOW", framing="CENTERED", depth_of_field="SHALLOW", lighting="BRIGHT_DAYLIGHT")
    
    scenes = [
        SceneBlueprint(
            scene_id="scn_g1_intro",
            scene_number=1,
            narrative_purpose="Establish canonical appearance of Character A approaching wooden door",
            estimated_duration_seconds=5.0,
            action="Anthropomorphic brass padlock-headed male character walks toward the wooden front door carrying keys.",
            emotion="neutral",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_tracking,
            character_ids=["char_padlock_male"],
            scene_quality_priority="CHARACTER_CRITICAL"
        ),
        SceneBlueprint(
            scene_id="scn_g2_b_enters",
            scene_number=2,
            narrative_purpose="Character B enters and approaches Character A",
            estimated_duration_seconds=5.0,
            action="Anthropomorphic silver padlock-headed female character in colorful traditional saree approaches the front porch.",
            emotion="happy",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_wide,
            character_ids=["char_padlock_female", "char_padlock_male"],
            scene_quality_priority="CHARACTER_CRITICAL"
        ),
        SceneBlueprint(
            scene_id="scn_g3_dialogue",
            scene_number=3,
            narrative_purpose="Short conversation near the door",
            estimated_duration_seconds=5.0,
            action="Brass padlock husband gestures toward the door lock while silver padlock wife responds.",
            emotion="curious",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_close,
            character_ids=["char_padlock_male", "char_padlock_female"],
            dialogue=[
                DialogueLine(
                    character_id="char_padlock_male",
                    voice_id="voice_male_01",
                    text="Did you remember the lock?",
                    emotion="curious",
                    delivery_style="comedic",
                    estimated_duration_seconds=2.4
                )
            ],
            scene_quality_priority="BALANCED"
        ),
        SceneBlueprint(
            scene_id="scn_g4_action",
            scene_number=4,
            narrative_purpose="Character A attempts comedic locking action",
            estimated_duration_seconds=6.0,
            action="Brass padlock husband safely secures the door handle using a small novelty baby prop.",
            emotion="excited",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_dolly,
            character_ids=["char_padlock_male", "char_padlock_female"],
            scene_quality_priority="ACTION_CRITICAL"
        ),
        SceneBlueprint(
            scene_id="scn_g5_camera_change",
            scene_number=5,
            narrative_purpose="Camera framing shift to test identity persistence",
            estimated_duration_seconds=5.0,
            action="Silver padlock wife reacts with amusement and smiles near the front porch entrance.",
            emotion="happy",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_close,
            character_ids=["char_padlock_female"],
            scene_quality_priority="CHARACTER_CRITICAL"
        ),
        SceneBlueprint(
            scene_id="scn_g6_movement",
            scene_number=6,
            narrative_purpose="Character A turns and walks while maintaining body proportions",
            estimated_duration_seconds=5.0,
            action="Brass padlock husband walks a few paces along the porch and turns back to face his wife.",
            emotion="confident",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_tracking,
            character_ids=["char_padlock_male"],
            scene_quality_priority="CHARACTER_CRITICAL"
        ),
        SceneBlueprint(
            scene_id="scn_g7_two_char_close",
            scene_number=7,
            narrative_purpose="Both characters in close framing testing cross-contamination",
            estimated_duration_seconds=5.0,
            action="Silver padlock wife checks the door handle while brass padlock husband gives a thumbs up.",
            emotion="happy",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_wide,
            character_ids=["char_padlock_female", "char_padlock_male"],
            scene_quality_priority="BALANCED"
        ),
        SceneBlueprint(
            scene_id="scn_g8_ending",
            scene_number=8,
            narrative_purpose="Both characters conclude story together",
            estimated_duration_seconds=5.0,
            action="Both brass padlock husband and silver padlock wife wave cheerfully toward the camera from the front porch.",
            emotion="happy",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_wide,
            character_ids=["char_padlock_male", "char_padlock_female"],
            scene_quality_priority="VISUAL_QUALITY_CRITICAL"
        )
    ]
    
    return ProductionBlueprint(
        blueprint_id="bp_stress_8g_001",
        blueprint_version=1,
        project_id="proj_stress_8g",
        title="Padlock Couple Door Lock Comedy",
        concept="A 3D animated comedy about a brass padlock-headed husband attempting to lock the house door with humorous props while his silver padlock-headed wife reacts.",
        genre="Animated Comedy",
        authoritative_art_style="Stylized high-quality 3D animated film, consistent CGI character design",
        authoritative_character_design="Anthropomorphic brass padlock-headed male in modern Indian attire and silver padlock-headed female in traditional Indian saree",
        target_duration_seconds=41.0,
        scenes=scenes,
        quality_strategy=QualityStrategy(max_retries=1, min_overall_score=7.0),
        status="APPROVED"
    )

# ===========================================================================
# 100-POINT CONSISTENCY SCORING SYSTEM
# ===========================================================================

def calculate_consistency_score(
    char_identity_ok: bool,
    char_appearance_ok: bool,
    clothing_consistency_ok: bool,
    visual_style_ok: bool,
    environment_continuity_ok: bool,
    multi_char_separation_ok: bool,
    voice_consistency_ok: bool,
    dialogue_timing_ok: bool,
    object_physics_ok: bool,
    timeline_accuracy_ok: bool
) -> int:
    """Computes the 100-point consistency score as specified in Step 14."""
    score = 0
    if char_identity_ok: score += 20
    if char_appearance_ok: score += 15
    if clothing_consistency_ok: score += 10
    if visual_style_ok: score += 10
    if environment_continuity_ok: score += 10
    if multi_char_separation_ok: score += 10
    if voice_consistency_ok: score += 10
    if dialogue_timing_ok: score += 5
    if object_physics_ok: score += 5
    if timeline_accuracy_ok: score += 5
    return score

# ===========================================================================
# UNIT & STRESS TEST CASES
# ===========================================================================

def test_8_scene_scenario_blueprint_properties():
    """Validates structural correctness and duration target of the 8-scene scenario."""
    bp = build_phase8g_test_blueprint()
    assert len(bp.scenes) == 8
    total_dur = sum(s.estimated_duration_seconds for s in bp.scenes)
    assert total_dur == 41.0
    assert bp.authoritative_art_style == "Stylized high-quality 3D animated film, consistent CGI character design"
    assert "brass padlock" in bp.authoritative_character_design.lower()
    assert "silver padlock" in bp.authoritative_character_design.lower()


def test_multi_character_reference_isolation_across_8_scenes():
    """
    Tests that across all 8 scenes, Character A resolves to URI_A and Character B resolves to URI_B
    with EXACTLY ONE generation call per character (2 total) and zero cross-contamination.
    """
    ref_manager = ReferenceManager()
    ref_manager.db = MagicMock()
    context = GenerationContext(
        user_id="user_stress_01",
        project_id="proj_stress_8g",
        job_id="bp_stress_8g_001",
        metadata={
            "art_style": "Stylized high-quality 3D animated film",
            "character_design": "Brass padlock male and Silver padlock female"
        }
    )
    
    char_a = Character(character_id="char_padlock_male", project_id="proj_stress_8g", name="Mr. Brass Padlock")
    char_b = Character(character_id="char_padlock_female", project_id="proj_stress_8g", name="Mrs. Silver Padlock")
    
    bp = build_phase8g_test_blueprint()
    
    # Mapping of scene -> primary character
    expected_char_map = {
        1: char_a,
        2: char_b,
        3: char_a,
        4: char_a,
        5: char_b,
        6: char_a,
        7: char_b,
        8: char_a
    }
    
    def mock_generator(desc, **kwargs):
        c_id = kwargs.get("character_id", "")
        if c_id == "char_padlock_female":
            return "gs://shortcutai-bucket/characters/char_padlock_female/canonical_ref_02.jpg"
        return "gs://shortcutai-bucket/characters/char_padlock_male/canonical_ref_01.jpg"

    with patch("services.asset_generator.generate_character_reference", side_effect=mock_generator) as mock_gen:
        resolved_uris = {}
        for scene in bp.scenes:
            primary_c = expected_char_map[scene.scene_number]
            resolved_s = ResolvedScene(scene=scene, characters=[primary_c], voices=[], style=None, location=None, props=[])
            
            res = ref_manager.resolve_reference_with_telemetry(context, resolved_s)
            resolved_uris[scene.scene_number] = res.reference_uri
            
        # Verify Character A gets URI_A across all its scenes (1, 3, 4, 6, 8)
        assert resolved_uris[1] == "gs://shortcutai-bucket/characters/char_padlock_male/canonical_ref_01.jpg"
        assert resolved_uris[3] == "gs://shortcutai-bucket/characters/char_padlock_male/canonical_ref_01.jpg"
        assert resolved_uris[4] == "gs://shortcutai-bucket/characters/char_padlock_male/canonical_ref_01.jpg"
        assert resolved_uris[6] == "gs://shortcutai-bucket/characters/char_padlock_male/canonical_ref_01.jpg"
        assert resolved_uris[8] == "gs://shortcutai-bucket/characters/char_padlock_male/canonical_ref_01.jpg"
        
        # Verify Character B gets URI_B across all its scenes (2, 5, 7)
        assert resolved_uris[2] == "gs://shortcutai-bucket/characters/char_padlock_female/canonical_ref_02.jpg"
        assert resolved_uris[5] == "gs://shortcutai-bucket/characters/char_padlock_female/canonical_ref_02.jpg"
        assert resolved_uris[7] == "gs://shortcutai-bucket/characters/char_padlock_female/canonical_ref_02.jpg"
        
        # Verify exactly TWO generation calls occurred (one for male, one for female)
        assert mock_gen.call_count == 2


def test_prompt_compiler_no_generic_human_substitution():
    """
    Verifies that PromptCompiler and sanitizer preserve the authoritative 3D padlock
    character language and do not allow generic human substitutions.
    """
    bp = build_phase8g_test_blueprint()
    compiler = PromptCompiler()
    context = GenerationContext(user_id="u1", project_id="p1", job_id="j1")
    
    char_a = Character(character_id="char_padlock_male", project_id="p1", name="Mr. Brass Padlock")
    
    for scene in bp.scenes:
        resolved = ResolvedScene(scene=scene, characters=[char_a], voices=[], style=None, location=None, props=[])
        compiled = compiler.compile(context, resolved, scene_blueprint=scene)
        sanitized = _sanitize_veo_prompt(compiled, bp.authoritative_art_style, bp.authoritative_character_design)
        
        # Must retain 3D animation style and padlock character design
        assert "3D animated" in sanitized or "3D Pixar" in sanitized or "CGI" in sanitized
        assert "padlock" in sanitized.lower()
        
        # Must NOT contain forbidden photorealistic keywords
        assert "photorealistic" not in sanitized.lower()
        assert "live-action" not in sanitized.lower()
        assert "real human" not in sanitized.lower()


def test_timeline_reconciliation_exact_duration_tolerance():
    """
    Verifies that TimelineBuilder receives all 8 normalized scenes and
    produces total duration within the strict ±0.20s tolerance of 41.0s.
    """
    timeline = TimelineBuilder("proj_stress_8g")
    bp = build_phase8g_test_blueprint()
    
    # Mock video file existence and duration reading
    with patch("os.path.exists", return_value=True), \
         patch("moviepy.editor.VideoFileClip") as mock_clip:
        
        mock_clip_inst = MagicMock()
        mock_clip_inst.duration = 8.0 # Raw chunk duration
        mock_clip.return_value = mock_clip_inst
        
        for s in bp.scenes:
            simulated_raw_path = f"/tmp/scene_{s.scene_id}.mp4"
            timeline.add_scene(s, s.estimated_duration_seconds, simulated_raw_path, [])
            
        timeline.reconcile_timing()
        assert timeline.validate() is True
        
        total_timeline_duration = sum(item.expected_duration for item in timeline.timeline.items)
        expected_duration = 41.0
        duration_delta = abs(total_timeline_duration - expected_duration)
        
        assert duration_delta <= 0.20, f"Timeline duration delta {duration_delta}s exceeded tolerance of 0.20s"
        assert total_timeline_duration == 41.0
        assert timeline.timeline.items[-1].end_time == 41.0


def test_consistency_scoring_evaluation():
    """Tests the 100-point consistency scoring formula under nominal and degraded conditions."""
    # Nominal pass scenario: all 10 criteria met -> 100/100
    perfect_score = calculate_consistency_score(
        char_identity_ok=True,
        char_appearance_ok=True,
        clothing_consistency_ok=True,
        visual_style_ok=True,
        environment_continuity_ok=True,
        multi_char_separation_ok=True,
        voice_consistency_ok=True,
        dialogue_timing_ok=True,
        object_physics_ok=True,
        timeline_accuracy_ok=True
    )
    assert perfect_score == 100
    
    # Degraded scenario: character identity failure (e.g. human substitution in one scene)
    degraded_score = calculate_consistency_score(
        char_identity_ok=False, # -20
        char_appearance_ok=False, # -15
        clothing_consistency_ok=True,
        visual_style_ok=True,
        environment_continuity_ok=True,
        multi_char_separation_ok=True,
        voice_consistency_ok=True,
        dialogue_timing_ok=True,
        object_physics_ok=True,
        timeline_accuracy_ok=True
    )
    assert degraded_score == 65
    assert degraded_score < 70  # Correctly flags as architectural/generation problem
