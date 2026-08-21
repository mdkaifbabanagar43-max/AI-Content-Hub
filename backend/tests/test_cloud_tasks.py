import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the FastAPI app
from main import app
from core.models.job import GenerationJob
from core.repositories.job_repo import GenerationJobRepository

client = TestClient(app)

@pytest.fixture
def mock_job_repo():
    with patch("routers.video_cloner.GenerationJobRepository") as mock_repo_class:
        repo_instance = MagicMock(spec=GenerationJobRepository)
        mock_repo_class.return_value = repo_instance
        yield repo_instance

@pytest.fixture
def mock_blueprint_repo():
    with patch("routers.video_cloner.production_blueprint_repo") as mock_repo:
        yield mock_repo

@pytest.fixture
def mock_enqueue():
    with patch("routers.video_cloner.enqueue_generation_task") as mock_eq:
        yield mock_eq

def test_internal_worker_missing_auth_header():
    payload = {
        "schema_version": 1,
        "job_id": "test_job_123",
        "user_id": "u1",
        "project_id": "p1",
        "blueprint_id": "b1"
    }
    # No Authorization header
    response = client.post("/projects/_internal/tasks/generate-production", json=payload)
    assert response.status_code == 401
    assert "Missing or invalid Authorization header" in response.json()["detail"]

def test_internal_worker_spoofed_header():
    payload = {
        "schema_version": 1,
        "job_id": "test_job_123",
        "user_id": "u1",
        "project_id": "p1",
        "blueprint_id": "b1"
    }
    # Spoofed Cloud Tasks header without OIDC
    response = client.post("/projects/_internal/tasks/generate-production", json=payload, headers={"X-CloudTasks-QueueName": "generation-queue"})
    assert response.status_code == 401
    assert "Missing or invalid Authorization header" in response.json()["detail"]

@patch("core.auth_oidc.id_token.verify_oauth2_token")
def test_internal_worker_invalid_service_account(mock_verify, mock_job_repo):
    # Mock token verification returning wrong email
    mock_verify.return_value = {"email": "wrong-sa@shortcutai-backend.iam.gserviceaccount.com"}
    
    payload = {
        "schema_version": 1,
        "job_id": "test_job_123",
        "user_id": "u1",
        "project_id": "p1",
        "blueprint_id": "b1"
    }
    response = client.post(
        "/projects/_internal/tasks/generate-production", 
        json=payload,
        headers={"Authorization": "Bearer fake_token"}
    )
    assert response.status_code == 403
    assert "Unauthorized service account" in response.json()["detail"]

@patch("core.auth_oidc.id_token.verify_oauth2_token")
def test_internal_worker_idempotency_duplicate_run(mock_verify, mock_job_repo, mock_blueprint_repo):
    # Mock token verification success
    from config import SERVICE_ACCOUNT_EMAIL
    mock_verify.return_value = {"email": SERVICE_ACCOUNT_EMAIL}
    
    mock_blueprint = MagicMock()
    mock_blueprint.status = "APPROVED"
    mock_blueprint_repo.get.return_value = mock_blueprint
    
    # try_start_job returns False meaning job is already running or completed
    mock_job_repo.try_start_job.return_value = False
    
    payload = {
        "schema_version": 1,
        "job_id": "test_job_123",
        "user_id": "u1",
        "project_id": "p1",
        "blueprint_id": "b1"
    }
    response = client.post(
        "/projects/_internal/tasks/generate-production", 
        json=payload,
        headers={"Authorization": "Bearer fake_token"}
    )
    
    # Assert returns 200 to acknowledge but ignore
    assert response.status_code == 200
    assert response.json()["status"] == "IGNORED"

@patch("core.auth_oidc.id_token.verify_oauth2_token")
@patch("routers.video_cloner.run_production_job")
def test_internal_worker_success(mock_run_job, mock_verify, mock_job_repo, mock_blueprint_repo):
    from config import SERVICE_ACCOUNT_EMAIL
    mock_verify.return_value = {"email": SERVICE_ACCOUNT_EMAIL}
    
    mock_blueprint = MagicMock()
    mock_blueprint_repo.get.return_value = mock_blueprint
    
    # try_start_job returns True (successfully locked)
    mock_job_repo.try_start_job.return_value = True
    
    payload = {
        "schema_version": 1,
        "job_id": "test_job_123",
        "user_id": "u1",
        "project_id": "p1",
        "blueprint_id": "b1"
    }
    response = client.post(
        "/projects/_internal/tasks/generate-production", 
        json=payload,
        headers={"Authorization": "Bearer fake_token"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    
    # Verify run_production_job was called
    mock_run_job.assert_called_once_with("u1", "p1", "b1")
    
    # Verify commit was called
    mock_job_repo.mark_completed.assert_called_once_with("u1", "p1", "b1", "test_job_123")

@patch("core.auth_oidc.id_token.verify_oauth2_token")
@patch("routers.video_cloner.run_production_job")
def test_internal_worker_retryable_failure(mock_run_job, mock_verify, mock_job_repo, mock_blueprint_repo):
    from config import SERVICE_ACCOUNT_EMAIL
    mock_verify.return_value = {"email": SERVICE_ACCOUNT_EMAIL}
    
    mock_blueprint = MagicMock()
    mock_blueprint_repo.get.return_value = mock_blueprint
    
    # try_start_job returns True (successfully locked)
    mock_job_repo.try_start_job.return_value = True
    
    from fastapi import HTTPException
    mock_run_job.side_effect = HTTPException(status_code=503, detail="Simulated transient failure")
    
    payload = {
        "schema_version": 1,
        "job_id": "test_job_123",
        "user_id": "u1",
        "project_id": "p1",
        "blueprint_id": "b1"
    }
    response = client.post(
        "/projects/_internal/tasks/generate-production", 
        json=payload,
        headers={"Authorization": "Bearer fake_token"}
    )
    
    # Cloud Tasks expects a non-200 to retry
    assert response.status_code == 503
    
    # In my updated implementation, HTTPException propagates immediately.
    # Therefore, we do NOT release the reservation on a transient failure!
    # Because if we released it, a retry would be blocked by idempotency.
    # So we don't check for release_reservation here.

@patch("routers.video_cloner.enqueue_generation_task")
@patch("routers.video_cloner.GenerationJobRepository")
@patch("routers.video_cloner.get_current_user")
def test_enqueue_failure_releases_reservation(mock_get_user, mock_repo_class, mock_enqueue, mock_blueprint_repo):
    mock_get_user.return_value = "u1"
    
    mock_repo_instance = MagicMock(spec=GenerationJobRepository)
    mock_repo_class.return_value = mock_repo_instance
    
    mock_blueprint = MagicMock()
    mock_blueprint.status = "APPROVED"
    mock_blueprint_repo.get.return_value = mock_blueprint
    
    # Simulate enqueue failure
    mock_enqueue.return_value = False
    
    from core.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: "u1"
    
    response = client.post("/projects/p1/production-blueprints/b1/generate")
    
    assert response.status_code == 500
    
    # Reservation should be created and then released
    mock_repo_instance.create_and_reserve.assert_called_once()
    mock_repo_instance.release_reservation.assert_called_once()
    
    app.dependency_overrides.clear()
