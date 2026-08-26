import pytest
from core.models.clone_blueprint import CloneBlueprint, CloneSceneBlueprint, NarrativeBeat, PacingProfile
from core.models.source_analysis import HookAnalysis, SourceVisualStyle, SourceAudioProfile, CTAAnalysis
from core.models.blueprint import ProductionBlueprint, SceneBlueprint, DialogueLine
from core.services.originality_validator import (
    validate_blueprint_originality,
    compute_narrative_similarity,
    OriginalityValidationException
)

@pytest.fixture
def mock_source_clone_blueprint():
    return CloneBlueprint(
        clone_blueprint_id="cl_padlock_source",
        source_video_id="src_padlock_vid",
        project_id="proj_padlock",
        user_id="user_test",
        source_analysis_version="1.0",
        title="Padlock Locked Out of House",
        source_duration_seconds=15.0,
        target_duration_seconds=15.0,
        aspect_ratio="9:16",
        hook=HookAnalysis(
            hook_type="CONFLICT",
            hook_description="Protagonist carrying heavy grocery bags arrives at house door and searches for keys",
            confidence=0.95,
            hook_start_seconds=0.0,
            hook_end_seconds=3.0
        ),
        narrative_structure=[
            NarrativeBeat(type="HOOK", start_seconds=0.0, end_seconds=3.0, description="Character carrying groceries arrives at front door"),
            NarrativeBeat(type="CONFLICT", start_seconds=3.0, end_seconds=8.0, description="Character searches pockets for house keys and tries to unlock door"),
            NarrativeBeat(type="TWIST", start_seconds=8.0, end_seconds=12.0, description="Second padlock character looks through window laughing at forgotten keys"),
            NarrativeBeat(type="RESOLUTION", start_seconds=12.0, end_seconds=15.0, description="Character gives funny confused pose outside locked door")
        ],
        pacing_profile=PacingProfile(
            overall_intensity="High",
            average_shot_duration=3.75,
            fastest_shot_duration=2.0,
            slowest_shot_duration=5.0,
            scene_count=3,
            shot_count=4,
            rhythm_description="Fast comedic cuts"
        ),
        visual_style_profile=SourceVisualStyle(
            art_style="3D Pixar-style digital animation",
            character_design="Brass padlock head character with expressive animated eyes",
            lighting="Bright afternoon sunlight",
            render_language="Octane 3D render"
        ),
        audio_profile=SourceAudioProfile(
            has_speech=True,
            speech_tempo="FAST",
            has_background_music=True,
            music_mood="Upbeat comedic"
        ),
        cta_structure=CTAAnalysis(exists=False, type="NONE", start_seconds=15.0, end_seconds=15.0),
        scenes=[
            CloneSceneBlueprint(
                scene_id="scn_1",
                scene_number=1,
                source_start_seconds=0.0,
                source_end_seconds=5.0,
                source_duration_seconds=5.0,
                narrative_purpose="Introduction",
                visual_action="Protagonist carries groceries and reaches the front porch door",
                dialogue_intent="Complaining about heavy grocery bags",
                emotion="tired",
                pacing="moderate"
            ),
            CloneSceneBlueprint(
                scene_id="scn_2",
                scene_number=2,
                source_start_seconds=5.0,
                source_end_seconds=10.0,
                source_duration_seconds=5.0,
                narrative_purpose="Conflict",
                visual_action="Tries keys in the padlock door lock but fails",
                dialogue_intent="Frustration at locked door",
                emotion="frustrated",
                pacing="fast"
            )
        ]
    )

def test_originality_check_fails_on_verbatim_plot_copy(mock_source_clone_blueprint):
    """When generated blueprint duplicates the source plot, it must be rejected."""
    copied_production_bp = ProductionBlueprint(
        project_id="proj_padlock",
        blueprint_id="pb_copied",
        title="Padlock Locked Out of House Copy",
        concept="Character carrying groceries arrives at locked front door and tries keys",
        genre="3D Comedy",
        target_duration_seconds=15.0,
        scenes=[
            SceneBlueprint(
                scene_id="scene_1",
                scene_number=1,
                narrative_purpose="Character carrying grocery bags arrives at house door",
                action="Protagonist carries groceries and drops bags in front of the locked door",
                dialogue=[DialogueLine(text="Oh no the door is locked!", character_id="char_padlock_1")]
            ),
            SceneBlueprint(
                scene_id="scene_2",
                scene_number=2,
                narrative_purpose="Trying to open locked door with keys",
                action="Tries keys in the padlock door lock but fails and searches pockets",
                dialogue=[DialogueLine(text="Where did I leave my keys?", character_id="char_padlock_1")]
            )
        ]
    )

    similarity, matched = compute_narrative_similarity(mock_source_clone_blueprint, copied_production_bp)
    assert similarity > 0.40
    assert any(k in matched for k in ["groceries", "door", "locked", "keys"])

    with pytest.raises(OriginalityValidationException) as exc:
        validate_blueprint_originality(mock_source_clone_blueprint, copied_production_bp, max_allowed_similarity=0.40)
    assert "Originality Check FAILED" in str(exc.value)

def test_originality_check_passes_on_new_narrative(mock_source_clone_blueprint):
    """When generated blueprint creates a new story (Bank Heist), it must pass cleanly."""
    heist_production_bp = ProductionBlueprint(
        project_id="proj_padlock",
        blueprint_id="pb_heist",
        title="The Midnight Vault Heist",
        concept="A comedic bank vault heist where a sneaky thief attempts to crack high-tech laser alarms",
        genre="Heist Comedy",
        target_duration_seconds=15.0,
        authoritative_art_style="3D Pixar-style digital animation",
        authoritative_character_design="Brass padlock head character with expressive animated eyes",
        scenes=[
            SceneBlueprint(
                scene_id="scene_1",
                scene_number=1,
                narrative_purpose="Infiltration",
                action="Character crawls stealthily beneath crisscrossing security lasers inside a dark bank lobby",
                dialogue=[DialogueLine(text="Ten seconds until the guards change shifts.", character_id="char_padlock_1")]
            ),
            SceneBlueprint(
                scene_id="scene_2",
                scene_number=2,
                narrative_purpose="Vault Cracking",
                action="Character spins the massive chrome bank safe combination dial with a stethoscope",
                dialogue=[DialogueLine(text="Almost cracked the gold jackpot!", character_id="char_padlock_1")]
            ),
            SceneBlueprint(
                scene_id="scene_3",
                scene_number=3,
                narrative_purpose="Heist Twist",
                action="Vault door swings open revealing bags overflowing with sparkling diamond gems",
                dialogue=[DialogueLine(text="We are rich beyond our wildest dreams!", character_id="char_padlock_1")]
            )
        ]
    )

    similarity, matched = compute_narrative_similarity(mock_source_clone_blueprint, heist_production_bp)
    assert similarity < 0.20
    assert validate_blueprint_originality(mock_source_clone_blueprint, heist_production_bp, max_allowed_similarity=0.40) is True
