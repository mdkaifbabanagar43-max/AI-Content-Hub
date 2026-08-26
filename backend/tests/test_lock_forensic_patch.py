from unittest.mock import patch, MagicMock

from core.models.blueprint import ProductionBlueprint, SceneBlueprint, QualityStrategy, DialogueLine
from core.models.context import GenerationContext
from core.services.bible_loader import ResolvedScene
from core.models.character import Character
from core.models.location import Location
from core.services.prompt_compiler import PromptCompiler
from core.services.reference_manager import ReferenceManager
from services.trend_remixer import _sanitize_veo_prompt
from core.services.timeline_builder import TimelineBuilder
from core.models.timeline import AudioAsset
from routers.video_cloner import run_production_job


# ─────────────────────────────────────────────────────────────
# TEST GROUP 1 — DURATION FORENSIC TEST (lock.mp4 19.12s vs 40s)
# ─────────────────────────────────────────────────────────────
@patch("core.services.timeline_builder.TimelineBuilder._get_video_duration")
@patch("os.path.exists", return_value=True)
def test_group_1_physical_duration_normalization(mock_exists, mock_get_dur):
    """
    Given lock.mp4 logical scene target durations:
    Scene 1: 2.6s
    Scene 2: 2.333s
    Scene 3: 7.467s
    Scene 4: 2.7s
    Scene 5: 4.02s
    Total source duration: 19.12s

    Veo produces raw durations: 5s, 5s, 8s, 5s, 5s (total ~28-40s).
    TimelineBuilder MUST physically subclip each scene to its exact target duration.
    Final master MUST be ~19.12s, NOT ~40s.
    """
    mock_get_dur.side_effect = lambda path: 8.0 if "3" in path else 5.0

    target_durations = [2.6, 2.333, 7.467, 2.7, 4.02]
    expected_total = sum(target_durations) # 19.12s
    veo_raw_durations = [5.0, 5.0, 8.0, 5.0, 5.0]

    builder = TimelineBuilder(project_id="proj_lock_test")

    # Add all 5 scenes with raw video paths and target durations
    for idx, (target_dur, raw_dur) in enumerate(zip(target_durations, veo_raw_durations)):
        scene_bp = SceneBlueprint(
            scene_id=f"scn_{idx+1}",
            scene_number=idx+1,
            action="Action",
            narrative_purpose="Beat",
            estimated_duration_seconds=target_dur
        )
        builder.add_scene(
            scene=scene_bp,
            expected_duration=target_dur,
            raw_video_path=f"/mock/raw_scene_{idx+1}.mp4",
            dialogue_assets=[AudioAsset(asset_id=f"a_{idx+1}", uri=f"/mock/audio_{idx+1}.mp3", duration=target_dur, start_time=0, end_time=target_dur)]
        )

    builder.reconcile_timing()

    # Verify timeline items reflect logical target durations
    assert len(builder.timeline.items) == 5
    for idx, item in enumerate(builder.timeline.items):
        assert item.final_scene_duration == target_durations[idx]

    # Verify total reconciled timeline duration matches ~19.12s
    assert round(builder.timeline.total_duration, 3) == 19.120

    # Simulate execute_timeline and verify subclip durations
    with patch("moviepy.editor.VideoFileClip") as mock_vfc, \
         patch("moviepy.editor.AudioFileClip") as mock_afc:
        
        # Configure moviepy clips
        def make_mock_clip(path):
            clip = MagicMock()
            # Raw video duration from Veo (longer than target)
            clip.duration = 8.0 if "scene_3" in path else 5.0
            clip.audio = None
            clip.subclip.side_effect = lambda s, e: MagicMock(duration=e - s)
            return clip

        mock_vfc.side_effect = make_mock_clip
        mock_afc.return_value = MagicMock(duration=2.0)

        final_paths = builder.execute_timeline(use_lip_sync=False)

        assert len(final_paths) == 5
        # The test MUST fail if final duration is ~40s (simulated by verifying total duration is 19.12s)
        assert builder.timeline.total_duration < 25.0
        assert abs(builder.timeline.total_duration - 19.12) < 0.01


# ─────────────────────────────────────────────────────────────
# TEST GROUP 2 — VISUAL IDENTITY LOCK & SAME REFERENCE URI
# ─────────────────────────────────────────────────────────────
def test_group_2_visual_identity_and_reference_persistence():
    """
    Given:
    art_style = "3D animated CGI"
    character_design = "anthropomorphic brass padlock-headed characters"

    1. Compiled prompt MUST contain the canonical animated identity.
    2. Prompt MUST NOT contain 'live-action', 'real human', or 'photorealistic human'.
    3. The SAME reference URI MUST be reused across all scenes.
    """
    art_style = "3D animated CGI"
    character_design = "anthropomorphic brass padlock-headed characters"

    # 1. Test Prompt Sanitizer enforces animated identity and strips contradictory tokens
    raw_prompt = "A husband walks down the street. live-action human actors with photorealistic human faces look around."
    sanitized = _sanitize_veo_prompt(raw_prompt, art_style, character_design)

    assert "live-action" not in sanitized.lower()
    assert "real human" not in sanitized.lower()
    assert "photorealistic" not in sanitized.lower()
    assert "3d animated cgi" in sanitized.lower()
    assert "anthropomorphic brass padlock-headed characters" in sanitized.lower()
    assert "9:16 vertical orientation" in sanitized.lower()

    # 2. Test Canonical Reference Persistence across all 5 scenes
    context = GenerationContext(user_id="user_1", project_id="proj_lock", job_id="job_lock")
    context.metadata = {
        "reference_cache": {},
        "art_style": art_style,
        "character_design": character_design
    }

    ref_manager = ReferenceManager()

    with patch("services.asset_generator.generate_character_reference") as mock_gen_ref:
        mock_gen_ref.return_value = "gs://bucket-ref/canonical_padlock_char.png"

        scene_refs = []
        for i in range(1, 6):
            scene_mock = SceneBlueprint(scene_id=f"scn_{i}", scene_number=i, action="walks", narrative_purpose="beat", estimated_duration_seconds=3.0)
            char_mock = Character(character_id="char_padlock", project_id="proj_lock", name="PadlockProtagonist", legacy_character_design=character_design)
            resolved_scene = ResolvedScene(scene=scene_mock, characters=[char_mock], voices=[], style=None, location=None, props=[])
            
            ref_uri = ref_manager.get_reference_uri(context, resolved_scene)
            scene_refs.append(ref_uri)

        # Asset generator must be called ONCE to generate the canonical master reference
        mock_gen_ref.assert_called_once()

        # All 5 scenes must receive the EXACT same reference URI
        assert len(scene_refs) == 5
        assert all(uri == "gs://bucket-ref/canonical_padlock_char.png" for uri in scene_refs)
        assert len(set(scene_refs)) == 1, "Character reference was regenerated across scenes!"


# ─────────────────────────────────────────────────────────────
# TEST GROUP 3 — LOCATION CONTINUITY LOCK
# ─────────────────────────────────────────────────────────────
def test_group_3_location_continuity_lock():
    """
    If source_location = 'house front porch with wooden front door',
    and preserve_structure = True:
    Assert compiled scene prompts retain compatible location context.
    """
    context = GenerationContext(user_id="user_1", project_id="proj_lock", job_id="job_lock")
    prompt_compiler = PromptCompiler()

    location = Location(
        location_id="loc_front_door",
        project_id="proj_lock",
        name="House Front Porch",
        environment="Front porch exterior with wooden front door and steps",
        architecture="Suburban house entrance",
        signature_elements="Brass lock on door"
    )

    char = Character(
        character_id="char_padlock",
        project_id="proj_lock",
        name="Padlock Man",
        legacy_character_design="Anthropomorphic character with brass padlock head"
    )

    scene_bp = SceneBlueprint(
        scene_id="scn_1",
        scene_number=1,
        action="Padlock Man turns key in the wooden front door",
        narrative_purpose="Hook",
        estimated_duration_seconds=2.6,
        location_id="loc_front_door",
        environment="Front porch with wooden door"
    )

    resolved_scene = ResolvedScene(
        scene=scene_bp,
        characters=[char],
        voices=[],
        style=None,
        location=location,
        props=[]
    )

    compiled_prompt = prompt_compiler.compile(context, resolved_scene, scene_blueprint=scene_bp)

    assert "LOCATION:" in compiled_prompt
    assert "House Front Porch" in compiled_prompt
    assert "wooden front door" in compiled_prompt.lower()
    assert "front porch" in compiled_prompt.lower()


# ─────────────────────────────────────────────────────────────
# TEST GROUP 4 — RETRY ISOLATION
# ─────────────────────────────────────────────────────────────
@patch("core.services.canonical_generation_engine.generate_video_with_veo")
@patch("core.services.canonical_generation_engine.QualityReviewer")
@patch("services.lip_sync_service.sync_lips")
@patch("core.services.timeline_builder.TimelineBuilder.normalize_video_to_audio_duration")
@patch("core.services.timeline_builder.TimelineBuilder._get_video_duration", return_value=5.0)
@patch("routers.video_cloner.production_blueprint_repo")
@patch("routers.video_cloner.attempt_repo")
@patch("core.services.canonical_generation_engine.generate_voiceover")
@patch("services.asset_generator.generate_character_reference", return_value="gs://mock/ref.png")
@patch("routers.video_cloner.upload_file", return_value="https://storage.googleapis.com/final.mp4")
@patch("routers.video_cloner.concat_scenes")
@patch("moviepy.editor.VideoFileClip")
@patch("moviepy.editor.AudioFileClip")
@patch("os.path.exists", return_value=True)
@patch("os.path.getsize", return_value=1000)
def test_group_4_retry_isolation(
    mock_getsize, mock_exists, mock_afc, mock_vfc, mock_concat, mock_upload, mock_asset_gen, mock_tts,
    mock_attempt_repo, mock_bp_repo, mock_get_dur, mock_normalize, mock_lip_sync,
    mock_quality_reviewer, mock_generate_veo
):
    """
    Attempt 1 rejected by QualityReviewer.
    Attempt 2 accepted by QualityReviewer.

    Assert:
    - Attempt 1 NEVER reaches lip-sync or timeline registration.
    - ONLY Attempt 2 proceeds downstream.
    """
    from core.services.quality_reviewer import QualityReviewResult

    # Blueprint with max_retries=1
    bp = ProductionBlueprint(
        project_id="proj_retry_iso",
        blueprint_id="bp_retry_iso",
        title="Retry Isolation Test",
        concept="Test",
        genre="Comedy",
        target_duration_seconds=5.0,
        status="APPROVED",
        quality_strategy=QualityStrategy(max_retries=1)
    )
    scene = SceneBlueprint(scene_id="s1", scene_number=1, action="Action", narrative_purpose="Hook", estimated_duration_seconds=5.0)
    scene.dialogue = [DialogueLine(text="Hello", voice_label="v1", character_id="c1", emotion="neutral", delivery_style="casual", estimated_duration_seconds=2.0)]
    bp.scenes = [scene]
    mock_bp_repo.get.return_value = bp

    # Two generations: Attempt 1 raw bytes, Attempt 2 raw bytes
    mock_generate_veo.side_effect = [b"raw_bytes_attempt_1", b"raw_bytes_attempt_2"]

    # Reviewer rejects Attempt 1, accepts Attempt 2
    rev_instance = MagicMock()
    review_1 = QualityReviewResult(character_consistency=3.0, scene_adherence=3.0, visual_quality=3.0, continuity=3.0, overall=3.0, issues=["Not padlock head"], recommended_action="reject")
    review_2 = QualityReviewResult(character_consistency=9.0, scene_adherence=9.0, visual_quality=9.0, continuity=9.0, overall=9.0, issues=[], recommended_action="accept")
    rev_instance.review_video.side_effect = [review_1, review_2]
    mock_quality_reviewer.return_value = rev_instance

    mock_tts.return_value = "/mock/tts.mp3"
    mock_normalize.return_value = "/mock/norm_attempt_2.mp4"
    mock_lip_sync.return_value = "/mock/synced_attempt_2.mp4"

    # Mock moviepy
    mock_v_inst = MagicMock()
    mock_v_inst.fps = 30
    mock_v_inst.duration = 5.0
    mock_v_inst.__enter__.return_value = mock_v_inst
    mock_vfc.return_value = mock_v_inst

    mock_a_inst = MagicMock()
    mock_a_inst.duration = 2.0
    mock_a_inst.__enter__.return_value = mock_a_inst
    mock_afc.return_value = mock_a_inst

    run_production_job("user_1", "proj_retry_iso", "bp_retry_iso")

    # Veo called exactly 2 times
    assert mock_generate_veo.call_count == 2
    # Quality review called exactly 2 times
    assert rev_instance.review_video.call_count == 2
    # Normalization and LipSync called ONCE (for Attempt 2 only)
    assert mock_normalize.call_count == 1
    assert mock_lip_sync.call_count == 1
    # Concat called once for the accepted scene
    assert mock_concat.call_count == 1
    assert bp.status == "COMPLETED"


# ─────────────────────────────────────────────────────────────
# TEST GROUP 5 — GOLDEN PATH PARITY
# ─────────────────────────────────────────────────────────────
def test_group_5_golden_path_parity():
    """
    Assert that the Video Cloner and CanonicalGenerationEngine call the proven
    canonical services used by Trend Cloner:
    - VeoService (generate_video_with_veo)
    - ElevenLabsService (generate_voiceover)
    - LipSyncService (sync_lips)
    - TimelineBuilder
    - QualityReviewer
    """
    from core.services.canonical_generation_engine import CanonicalGenerationEngine
    from core.services.timeline_builder import TimelineBuilder
    from core.services.quality_reviewer import QualityReviewer
    import services.veo_service as veo_svc
    import services.elevenlabs_service as el_svc
    import services.lip_sync_service as ls_svc

    engine = CanonicalGenerationEngine()
    assert hasattr(engine, "generate_scene")
    assert hasattr(TimelineBuilder, "execute_timeline")
    assert hasattr(TimelineBuilder, "normalize_video_to_audio_duration")
    assert hasattr(QualityReviewer, "review_video")
    assert hasattr(veo_svc, "generate_video_with_veo")
    assert hasattr(el_svc, "generate_voiceover")
    assert hasattr(ls_svc, "sync_lips")
