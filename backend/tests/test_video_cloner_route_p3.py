"""
P3 Phase C - transform ROUTE wiring tests
==========================================
Proves the /transform endpoint delegates to the UniversalCreativeDirector
boundary and maps outcomes correctly:

  - success          -> 200 with the synthesized blueprint
  - gate rejection   -> 422 carrying actionable G2/G3/G4 findings
  - unexpected error -> 500

UCD internals are intentionally mocked here; boundary behavior itself is
covered exhaustively by test_universal_creative_director.py.
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from core.services.production_director import BlueprintValidationException
from test_source_dna_adapter import _make_clone_blueprint

client = TestClient(app)

ROUTE = "/projects/proj_route/clone-blueprints/cb_route/transform"


@pytest.fixture(autouse=True)
def override_auth():
    """Canonical FastAPI auth bypass: dependency_overrides beats the
    function reference captured at route-registration time."""
    from core.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: "u_route"
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _payload() -> dict:
    return {
        "topic": "Bitcoin heist in Paris",
        "clone_mode": "style_only",
        "target_duration_seconds": 15.0,
    }


def _canned_bp():
    from core.models.blueprint import ProductionBlueprint, SceneBlueprint

    bp = ProductionBlueprint(
        project_id="proj_route", blueprint_id="pb_route",
        title="Route Fixture", concept="c", genre="Comedy",
        target_duration_seconds=15.0,
    )
    bp.scenes.append(SceneBlueprint(
        scene_id="s1", scene_number=1, narrative_purpose="Hook",
        estimated_duration_seconds=5.0,
    ))
    bp.status = "DRAFT"
    return bp


@patch("routers.video_cloner.clone_blueprint_repo")
@patch("routers.video_cloner.production_blueprint_repo")
@patch("routers.video_cloner.UniversalCreativeDirector")
def test_transform_route_delegates_to_ucd(
    mock_ucd_cls, mock_pb_repo, mock_cb_repo
):
    cb = _make_clone_blueprint()
    mock_cb_repo.get_latest.return_value = cb
    canned = _canned_bp()

    ucd_instance = mock_ucd_cls.return_value
    ucd_instance.transform.return_value = canned

    response = client.post(
        ROUTE, json=_payload(), headers={"Authorization": "Bearer x"}
    )

    assert response.status_code == 200
    assert response.json()["blueprint_id"] == "pb_route"

    # Delegation contract: legacy request + source lineage handed to UCD
    ucd_instance.transform.assert_called_once()
    kwargs = ucd_instance.transform.call_args.kwargs
    assert kwargs["legacy_request"] is not None
    assert kwargs["legacy_request"].topic == "Bitcoin heist in Paris"
    assert kwargs["legacy_request"].clone_mode == "style_only"
    assert kwargs["source_video_id"] == cb.source_video_id

    # Route-level save preserved (double-save with internal DRAFT save is
    # pre-existing legacy behavior - kept for zero-delta switching)
    mock_pb_repo.save.assert_called_once_with("u_route", canned)

    mock_ucd_cls.assert_called_once_with(user_id="u_route",
                                         project_id="proj_route")


@patch("routers.video_cloner.clone_blueprint_repo")
@patch("routers.video_cloner.production_blueprint_repo")
@patch("routers.video_cloner.UniversalCreativeDirector")
def test_transform_gate_rejection_maps_to_422(
    mock_ucd_cls, mock_pb_repo, mock_cb_repo
):
    mock_cb_repo.get_latest.return_value = _make_clone_blueprint()

    ucd_instance = mock_ucd_cls.return_value
    ucd_instance.transform.side_effect = BlueprintValidationException(
        "P3 validation pipeline rejected the synthesized blueprint.",
        errors=[
            "G2_preservation_compliance: Character preservation violated; "
            "source IDs reused while preserve_characters=False: PROTAGONIST"
        ],
    )

    response = client.post(
        ROUTE, json=_payload(), headers={"Authorization": "Bearer x"}
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "validation pipeline" in detail
    assert "G2_preservation_compliance" in detail
    mock_pb_repo.save.assert_not_called()


@patch("routers.video_cloner.clone_blueprint_repo")
@patch("routers.video_cloner.production_blueprint_repo")
@patch("routers.video_cloner.UniversalCreativeDirector")
def test_transform_unexpected_error_maps_to_500(
    mock_ucd_cls, mock_pb_repo, mock_cb_repo
):
    mock_cb_repo.get_latest.return_value = _make_clone_blueprint()
    mock_ucd_cls.return_value.transform.side_effect = RuntimeError("boom")

    response = client.post(
        ROUTE, json=_payload(), headers={"Authorization": "Bearer x"}
    )

    assert response.status_code == 500
    assert "Transformation failed: boom" in response.json()["detail"]


def test_transform_missing_blueprint_maps_to_404():
    with patch("routers.video_cloner.clone_blueprint_repo") as mock_cb_repo:
        mock_cb_repo.get_latest.return_value = None
        response = client.post(ROUTE, json=_payload())
    assert response.status_code == 404
    assert "CloneBlueprint not found" in response.json()["detail"]