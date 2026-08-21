"""
Visual Identity & Architecture Merge Test Suite
================================================
Validates VisualIdentityPack, CharacterVisualIdentity multi-angle sheets,
EnvironmentVisualIdentity, PropVisualIdentity, shot-aware ReferenceManager,
PromptCompiler sanitization, LipSync product modes, and execution contracts.
"""
import pytest
import uuid
import datetime
from unittest.mock import MagicMock, patch

from core.models.visual_identity import (
    VisualIdentityPack,
    CharacterVisualIdentity,
    EnvironmentVisualIdentity,
    PropVisualIdentity,
    VisualTreatment,
    ShotReferencePack
)
from core.models.character import Character
from core.models.scene import Scene
from core.models.blueprint import ProductionBlueprint, SceneBlueprint, DialogueLine, CameraDirection
from core.models.context import GenerationContext
from core.services.bible_loader import ResolvedScene
from core.services.reference_manager import ReferenceManager
from core.services.prompt_compiler import PromptCompiler
from core.services.visual_identity_service import VisualIdentityService
from core.models.operation_state import verify_execution_certificate

def test_visual_identity_pack_model_structure():
    """Verify VisualIdentityPack, CharacterVisualIdentity, EnvironmentVisualIdentity schema."""
    char = CharacterVisualIdentity(
        character_id="char_padlock_male",
        project_id="proj_test_001",
        name="Mr. Padlock",
        version=1,
        master_sheet_uri="gs://bucket/users/test/master_sheet.jpg",
        front_ref_uri="gs://bucket/users/test/front.jpg",
        three_quarter_left_uri="gs://bucket/users/test/3q_left.jpg",
        closeup_ref_uri="gs://bucket/users/test/closeup.jpg",
        full_body_ref_uri="gs://bucket/users/test/full_body.jpg",
        visual_descriptor="3D brass padlock character",
        status="APPROVED"
    )
    
    env = EnvironmentVisualIdentity(
        environment_id="env_porch",
        project_id="proj_test_001",
        name="Front Porch",
        version=1,
        canonical_uri="gs://bucket/users/test/env_porch.jpg",
        wide_ref_uri="gs://bucket/users/test/env_wide.jpg",
        status="APPROVED"
    )

    pack = VisualIdentityPack(
        pack_id="vip_test_001",
        project_id="proj_test_001",
        version=1,
        characters={"char_padlock_male": char},
        environments={"env_porch": env},
        visual_treatment=VisualTreatment(art_style="3D Pixar-style digital animation"),
        status="LOCKED"
    )

    dumped = pack.model_dump()
    assert dumped["pack_id"] == "vip_test_001"
    assert dumped["characters"]["char_padlock_male"]["front_ref_uri"] == "gs://bucket/users/test/front.jpg"
    assert dumped["environments"]["env_porch"]["wide_ref_uri"] == "gs://bucket/users/test/env_wide.jpg"
    assert dumped["status"] == "LOCKED"

def test_shot_aware_reference_selection_closeup():
    """Verify ReferenceManager selects closeup_ref_uri for closeup shot framing."""
    ref_mgr = ReferenceManager()
    ref_mgr.db = None # Isolated from network

    char = CharacterVisualIdentity(
        character_id="char_padlock_male",
        project_id="proj_test_001",
        name="Mr. Padlock",
        version=1,
        master_sheet_uri="gs://bucket/users/test_user/master.jpg",
        front_ref_uri="gs://bucket/users/test_user/front.jpg",
        closeup_ref_uri="gs://bucket/users/test_user/closeup.jpg",
        full_body_ref_uri="gs://bucket/users/test_user/full_body.jpg"
    )
    vip = VisualIdentityPack(
        pack_id="vip_001",
        project_id="proj_test_001",
        version=1,
        characters={"char_padlock_male": char}
    )

    context = GenerationContext(
        user_id="test_user",
        project_id="proj_test_001",
        job_id="job_001",
        metadata={"visual_identity_pack": vip}
    )

    scene = Scene(
        scene_id="scn_01",
        project_id="proj_test_001",
        scene_number=1,
        duration=5.0,
        camera="Close-up portrait on facial expression",
        character_ids=["char_padlock_male"]
    )
    resolved = ResolvedScene(scene=scene, characters=[], voices=[], props=[], style=None, location=None)

    res = ref_mgr.resolve_reference_with_telemetry(
        context=context,
        resolved_scene=resolved,
        target_character_id="char_padlock_male"
    )

    assert res.reference_uri == "gs://bucket/users/test_user/closeup.jpg"
    assert res.reference_source == "VISUAL_IDENTITY_PACK"

def test_shot_aware_reference_selection_wide_shot():
    """Verify ReferenceManager selects full_body_ref_uri for wide establishing shot."""
    ref_mgr = ReferenceManager()
    ref_mgr.db = None

    char = CharacterVisualIdentity(
        character_id="char_padlock_male",
        project_id="proj_test_001",
        name="Mr. Padlock",
        version=1,
        master_sheet_uri="gs://bucket/users/test_user/master.jpg",
        front_ref_uri="gs://bucket/users/test_user/front.jpg",
        closeup_ref_uri="gs://bucket/users/test_user/closeup.jpg",
        full_body_ref_uri="gs://bucket/users/test_user/full_body.jpg"
    )
    vip = VisualIdentityPack(
        pack_id="vip_001",
        project_id="proj_test_001",
        version=1,
        characters={"char_padlock_male": char}
    )

    context = GenerationContext(
        user_id="test_user",
        project_id="proj_test_001",
        job_id="job_001",
        metadata={"visual_identity_pack": vip}
    )

    scene = Scene(
        scene_id="scn_01",
        project_id="proj_test_001",
        scene_number=1,
        duration=5.0,
        camera="Wide establishing exterior shot",
        character_ids=["char_padlock_male"]
    )
    resolved = ResolvedScene(scene=scene, characters=[], voices=[], props=[], style=None, location=None)

    res = ref_mgr.resolve_reference_with_telemetry(
        context=context,
        resolved_scene=resolved,
        target_character_id="char_padlock_male"
    )

    assert res.reference_uri == "gs://bucket/users/test_user/full_body.jpg"
    assert res.reference_source == "VISUAL_IDENTITY_PACK"

def test_legacy_character_reference_fallback():
    """Verify existing single-reference characters still resolve seamlessly."""
    ref_mgr = ReferenceManager()
    ref_mgr.db = None

    legacy_char = Character(
        character_id="char_legacy",
        project_id="proj_test_001",
        name="Legacy Padlock",
        canonical_reference_uri="gs://bucket/users/test_user/legacy_ref.jpg"
    )

    context = GenerationContext(
        user_id="test_user",
        project_id="proj_test_001",
        job_id="job_001",
        metadata={}
    )

    scene = Scene(
        scene_id="scn_01",
        project_id="proj_test_001",
        scene_number=1,
        duration=5.0,
        character_ids=["char_legacy"]
    )
    resolved = ResolvedScene(scene=scene, characters=[legacy_char], voices=[], props=[], style=None, location=None)

    res = ref_mgr.resolve_reference_with_telemetry(
        context=context,
        resolved_scene=resolved,
        target_character_id="char_legacy"
    )

    assert res.reference_uri == "gs://bucket/users/test_user/legacy_ref.jpg"
    assert res.reference_source == "PROJECT_BIBLE"

def test_prompt_compiler_sanitizer_integration():
    """Verify PromptCompiler applies TrendRemixer sanitization to strip photorealistic terms on 3D animations."""
    compiler = PromptCompiler()
    context = GenerationContext(
        user_id="test_user",
        project_id="proj_001",
        job_id="job_001",
        metadata={"art_style": "3D Pixar-style digital animation"}
    )
    scene = Scene(
        scene_id="scn_01",
        project_id="proj_001",
        scene_number=1,
        duration=5.0,
        action="A photorealistic human character opens the door in live-action meme style"
    )
    resolved = ResolvedScene(scene=scene, characters=[], voices=[], props=[], style=None, location=None)

    prompt = compiler.compile(context, resolved)
    assert "photorealistic human" not in prompt.lower()
    assert "live-action" not in prompt.lower()

def test_blueprint_lip_sync_mode_preservation():
    """Verify ProductionBlueprint preserves use_lip_sync and allow_lip_sync_fallback."""
    bp = ProductionBlueprint(
        project_id="proj_001",
        title="Padlock Adventure",
        concept="Lost keys",
        genre="Comedy",
        target_duration_seconds=30.0,
        use_lip_sync=False,
        allow_lip_sync_fallback=True,
        scenes=[
            SceneBlueprint(
                scene_id="scn_01",
                scene_number=1,
                narrative_purpose="Establish scene",
                estimated_duration_seconds=5.0,
                use_lip_sync=False,
                allow_lip_sync_fallback=True
            )
        ]
    )

    dumped = bp.model_dump()
    assert dumped["use_lip_sync"] is False
    assert dumped["allow_lip_sync_fallback"] is True
    assert dumped["scenes"][0]["use_lip_sync"] is False

    reconstructed = ProductionBlueprint(**dumped)
    assert reconstructed.use_lip_sync is False
    assert reconstructed.allow_lip_sync_fallback is True

def test_execution_certificate_validation_with_unified_architecture(tmp_path):
    """Verify verify_execution_certificate still certifies valid multi-scene jobs."""
    temp_file = tmp_path / "final.mp4"
    temp_file.write_bytes(b"dummy mp4 video bytes")

    cert = verify_execution_certificate(
        job_id="bp_test_001",
        project_id="proj_001",
        expected_scenes_count=2,
        generated_scenes_count=2,
        all_scenes_approved=True,
        timeline_validated=True,
        normalized_scene_count=2,
        final_mp4_path=str(temp_file),
        final_duration=10.0,
        target_duration=10.0,
        final_upload_uri="https://storage.googleapis.com/test/final.mp4"
    )
    assert cert.certified is True
    assert len(cert.certification_errors) == 0
