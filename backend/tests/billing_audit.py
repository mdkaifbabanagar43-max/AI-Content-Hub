import sys
import os

# Add backend to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)


def run_audit():
    print("🕵️ STARING BANK-GRADE BILLING AUDIT")
    print("===================================")

    # Heavy live-Firebase imports are kept INSIDE the script entrypoint so
    # that pytest collection of the regression tests below can never crash
    # on machines without credentials.
    try:
        from services.credit_service import deduct_credits_atomic, check_feature_access
        from models import InsufficientFundsError, FeatureLockedError
        from firebase_utils import db
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Ensure you are running this from the root of the repo or backend folder.")
        sys.exit(1)
    
    # SETUP
    starter_id = "audit_starter_user"
    broke_id = "audit_broke_user"
    rich_id = "audit_rich_user"
    
    # Clean previous test data
    print("\n🧹 Cleaning Test Data...")
    db.collection("users").document(starter_id).set({"plan": "starter", "credits": 50})
    db.collection("users").document(broke_id).set({"plan": "starter", "credits": 5})
    db.collection("users").document(rich_id).set({"plan": "creator", "credits": 100})
    print("✅ Test Users Reset.")
    
    # CHECK A: Feature Gate
    print("\n🧪 Check A: The Feature Gate (LipSync Locked for Starter)")
    try:
        check_feature_access('starter', 'lipsync')
        print("❌ FAILED: Starter user accessed LipSync!")
    except FeatureLockedError:
        print("✅ PASSED: System blocked Starter user from LipSync.")
    except Exception as e:
        print(f"❌ ERROR: Unexpected exception: {e}")

    # CHECK B: Bankruptcy Check
    print("\n🧪 Check B: The Bankruptcy Check (5 Credits vs 10 Cost)")
    try:
        deduct_credits_atomic(broke_id, 10, "test_bankruptcy")
        print("❌ FAILED: Broke user spent money they don't have!")
    except InsufficientFundsError:
         print("✅ PASSED: Transaction rejected due to insufficient funds.")
    except Exception as e:
        print(f"❌ ERROR: Unexpected exception: {e}")
        
    # CHECK C: Deduction Integrity
    print("\n🧪 Check C: The Deduction Integrity (100 - 20 = 80)")
    try:
        deduct_credits_atomic(rich_id, 20, "test_deduction")
        
        # Verify DB State
        doc = db.collection("users").document(rich_id).get()
        new_bal = doc.to_dict().get('credits')
        
        if new_bal == 80:
             print(f"✅ PASSED: Balance is exactly 80. (Verified in DB)")
        else:
             print(f"❌ FAILED: Balance is {new_bal}, expected 80.")
             
    except Exception as e:
        print(f"❌ ERROR: Deduction failed: {e}")

    # CHECK D: Plan Sync & Webhook Simulation
    print("\n🧪 Check D: The Plan Sync (Upgrade to Agency)")
    try:
        # Simulate Webhook Update
        db.collection("users").document(starter_id).update({
            "plan": "agency",
            "credits": 10000
        })
        
        # Verify
        doc = db.collection("users").document(starter_id).get()
        data = doc.to_dict()
        if data['plan'] == 'agency' and data['credits'] == 10000:
             print("✅ PASSED: User successfully upgraded to Agency.")
        else:
             print(f"❌ FAILED: Upgrade failed. Plan: {data.get('plan')}")
             
    except Exception as e:
        print(f"❌ ERROR: Sync failed: {e}")

    print("\n===================================")
    print("🎉 AUDIT COMPLETE.")

if __name__ == "__main__":
    run_audit()


# ═══════════════════════════════════════════════════════════════════════════
# P0 BILLING REGRESSION TESTS (pytest, fully mocked — no GCP/Firebase needed)
#
# Bug being guarded against:
#   run_production_job() previously swallowed ALL exceptions after marking the
#   blueprint FAILED. The Cloud Tasks worker then fell through to
#   mark_completed(), COMMITTING the user's credit reservation even though
#   generation failed. Contract now enforced:
#     1. Orchestrator: any failure must RAISE (fail-closed).
#     2. Worker: raised failure => release_reservation() called,
#        mark_completed() NEVER called.
# ═══════════════════════════════════════════════════════════════════════════
import pytest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from main import app  # Mirrors tests/test_cloud_tasks.py conventions
from core.models.blueprint import ProductionBlueprint, SceneBlueprint
from core.repositories.job_repo import GenerationJobRepository

client = TestClient(app)


def _make_blueprint(blueprint_id: str) -> ProductionBlueprint:
    """Minimal APPROVED single-scene blueprint for orchestrator tests."""
    bp = ProductionBlueprint(
        project_id="billing_proj",
        blueprint_id=blueprint_id,
        title="P0 Billing Regression",
        concept="Ensure failed jobs never commit credits",
        genre="Comedy",
        target_duration_seconds=5.0,
        status="APPROVED",
    )
    bp.scenes.append(
        SceneBlueprint(
            scene_id="scn_fail_1",
            scene_number=1,
            narrative_purpose="Hook",
            estimated_duration_seconds=5.0,
        )
    )
    return bp


def _reference_resolution():
    """Concrete reference telemetry payload (string fields only)."""
    return SimpleNamespace(
        reference_uri="gs://fake-bucket/refs/char_ref.png",
        reference_requested=True,
        reference_source="bible",
        reference_asset_id="asset_char_1",
        reference_generation_attempted=True,
        reference_generation_status="SUCCEEDED",
        reference_validation_status="VALID",
        reference_failure_reason=None,
        fallback_mode=None,
    )


@patch("routers.video_cloner.production_blueprint_repo")
@patch("routers.video_cloner.attempt_repo")
@patch("routers.video_cloner.ProjectBibleLoader")
@patch("routers.video_cloner.PromptCompiler")
@patch("routers.video_cloner.ReferenceManager")
@patch("routers.video_cloner.ContinuityManager")
@patch("routers.video_cloner.TimelineBuilder")
@patch("core.services.canonical_generation_engine.CanonicalGenerationEngine")
@patch("core.repositories.visual_identity_repo.VisualIdentityRepository")
def test_failed_generation_propagates_and_marks_blueprint_failed(
    mock_vip_repo,
    mock_engine_cls,
    mock_timeline_cls,
    mock_continuity,
    mock_refman,
    mock_compiler,
    mock_bible_loader,
    mock_attempt_repo,
    mock_bp_repo,
):
    """
    CONTRACT 1 (orchestrator): If any scene-generation step explodes, the
    exception MUST escape run_production_job() (after persisting the FAILED
    blueprint status) so upstream callers can distinguish success/failure.
    """
    bp = _make_blueprint("bp_billing_propagate")
    mock_bp_repo.get.return_value = bp

    # Fresh attempt checkpoint per scene (forces real GenerationAttempt creation)
    mock_attempt_repo.get.return_value = None

    # Neutralize context-building collaborators
    mock_vip_repo.return_value.get_latest.return_value = None
    mock_bible_loader.return_value.resolve_scene_blueprint.return_value = None
    mock_compiler.return_value.compile.return_value = "compiled cinematic prompt"
    mock_continuity.return_value.get_previous_state.return_value = None
    mock_refman.return_value.resolve_reference_with_telemetry.return_value = (
        _reference_resolution()
    )

    # THE FAILURE: canonical engine blows up mid-scene (simulated Veo outage)
    mock_engine_cls.return_value.generate_scene.side_effect = RuntimeError(
        "Veo provider exploded"
    )

    from routers.video_cloner import run_production_job

    with pytest.raises(RuntimeError, match="Veo provider exploded"):
        run_production_job("billing_user", "billing_proj", "bp_billing_propagate")

    # Terminal state must be persisted BEFORE propagation
    assert bp.status == "FAILED"
    mock_bp_repo.save.assert_called()


@patch("core.auth_oidc.id_token.verify_oauth2_token")
@patch("routers.video_cloner.run_production_job")
@patch("routers.video_cloner.GenerationJobRepository")
@patch("routers.video_cloner.production_blueprint_repo")
def test_worker_releases_credits_and_never_commits_on_permanent_failure(
    mock_bp_repo,
    mock_job_repo_cls,
    mock_run_job,
    mock_verify,
):
    """
    CONTRACT 2 (Cloud Tasks worker): a permanent generation failure must
    RELEASE the credit reservation and return HTTP 200 {"status": "FAILED"}
    so Cloud Tasks stops retrying — and must NEVER commit credits.
    """
    from config import SERVICE_ACCOUNT_EMAIL

    mock_verify.return_value = {"email": SERVICE_ACCOUNT_EMAIL}

    repo_instance = MagicMock(spec=GenerationJobRepository)
    mock_job_repo_cls.return_value = repo_instance
    repo_instance.try_start_job.return_value = True  # acquire idempotency lock

    mock_blueprint = MagicMock()
    mock_blueprint.status = "APPROVED"
    mock_bp_repo.get.return_value = mock_blueprint

    # Orchestrator honors the fail-closed contract by raising on failure
    mock_run_job.side_effect = RuntimeError("boom: veo quota exhausted")

    payload = {
        "schema_version": 1,
        "job_id": "job_billing_fail",
        "user_id": "u1",
        "project_id": "p1",
        "blueprint_id": "b1",
    }
    response = client.post(
        "/projects/_internal/tasks/generate-production",
        json=payload,
        headers={"Authorization": "Bearer fake_token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert "boom" in body["reason"]

    # 💰 THE ACTUAL MONEY ASSERTIONS
    repo_instance.release_reservation.assert_called_once_with(
        "u1", "p1", "b1", "job_billing_fail"
    )
    repo_instance.mark_completed.assert_not_called()


@patch("core.auth_oidc.id_token.verify_oauth2_token")
@patch("routers.video_cloner.run_production_job")
@patch("routers.video_cloner.GenerationJobRepository")
@patch("routers.video_cloner.production_blueprint_repo")
def test_worker_still_commits_credits_on_success(
    mock_bp_repo,
    mock_job_repo_cls,
    mock_run_job,
    mock_verify,
):
    """
    Guardrail: the P0 fix must not break the happy path — successful
    generations are still committed exactly once.
    """
    from config import SERVICE_ACCOUNT_EMAIL

    mock_verify.return_value = {"email": SERVICE_ACCOUNT_EMAIL}

    repo_instance = MagicMock(spec=GenerationJobRepository)
    mock_job_repo_cls.return_value = repo_instance
    repo_instance.try_start_job.return_value = True

    mock_blueprint = MagicMock()
    mock_blueprint.status = "APPROVED"
    mock_bp_repo.get.return_value = mock_blueprint

    payload = {
        "schema_version": 1,
        "job_id": "job_billing_success",
        "user_id": "u1",
        "project_id": "p1",
        "blueprint_id": "b1",
    }
    response = client.post(
        "/projects/_internal/tasks/generate-production",
        json=payload,
        headers={"Authorization": "Bearer fake_token"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    repo_instance.mark_completed.assert_called_once_with(
        "u1", "p1", "b1", "job_billing_success"
    )
    repo_instance.release_reservation.assert_not_called()
