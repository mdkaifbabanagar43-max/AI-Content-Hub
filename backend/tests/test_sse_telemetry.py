"""
Unit and Integration Tests for Real-Time SSE Telemetry Streaming Engine
"""

import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from core.auth import get_current_user, get_current_user_flexible
from core.services.telemetry_broadcaster import (
    TelemetryBroadcaster,
    broadcast_event,
    BUFFER_MAX_LEN
)
from core.models.blueprint import ProductionBlueprint, SceneBlueprint
from core.repositories.blueprint_repo import BlueprintRepository


@pytest.fixture
def clean_broadcaster():
    """Returns a fresh TelemetryBroadcaster instance with cleared subscribers and buffers."""
    b = TelemetryBroadcaster()
    with b._sub_lock:
        b._subscribers.clear()
        b._event_buffers.clear()
    return b


def test_broadcaster_singleton(clean_broadcaster):
    b1 = TelemetryBroadcaster()
    b2 = TelemetryBroadcaster()
    assert b1 is b2
    assert b1 is clean_broadcaster


def test_broadcaster_event_payload_structure(clean_broadcaster):
    payload = clean_broadcaster.broadcast(
        blueprint_id="bp_test_123",
        event_type="SCENE_START",
        data={"scene_id": "scn_1", "expected_duration": 5.0}
    )
    assert payload["event"] == "SCENE_START"
    assert payload["blueprint_id"] == "bp_test_123"
    assert payload["scene_id"] == "scn_1"
    assert payload["expected_duration"] == 5.0
    assert "timestamp" in payload


def test_broadcaster_ring_buffer_replay(clean_broadcaster):
    bp_id = "bp_buffer_test"
    # Broadcast 60 events (more than buffer max len 50)
    for i in range(60):
        clean_broadcaster.broadcast(bp_id, "PROGRESS", {"tick": i})

    buffer = clean_broadcaster._event_buffers[bp_id]
    assert len(buffer) == BUFFER_MAX_LEN
    # First item in buffer should be tick 10 (0..9 dropped by deque maxlen)
    assert buffer[0]["tick"] == 10
    assert buffer[-1]["tick"] == 59


def test_broadcaster_stream_receives_live_events(clean_broadcaster):
    async def _run_test():
        bp_id = "bp_live_stream_test"
        stream_gen = clean_broadcaster.stream_events(bp_id, include_buffer=False, heartbeat_interval=1.0)

        # First event is STREAM_CONNECTED
        first_chunk = await anext(stream_gen)
        assert "data: " in first_chunk
        init_data = json.loads(first_chunk.replace("data: ", "").strip())
        assert init_data["event"] == "STREAM_CONNECTED"

        # Broadcast an event
        clean_broadcaster.broadcast(bp_id, "QUALITY_REVIEW_SCORED", {"score": 9.2, "passed": True})

        second_chunk = await anext(stream_gen)
        data = json.loads(second_chunk.replace("data: ", "").strip())
        assert data["event"] == "QUALITY_REVIEW_SCORED"
        assert data["score"] == 9.2
        assert data["passed"] is True

        # Terminal event stops the stream
        clean_broadcaster.broadcast(bp_id, "ASSEMBLY_COMPLETE", {"status": "COMPLETED"})
        third_chunk = await anext(stream_gen)
        term_data = json.loads(third_chunk.replace("data: ", "").strip())
        assert term_data["event"] == "ASSEMBLY_COMPLETE"

        # Next iteration should finish generator
        with pytest.raises(StopAsyncIteration):
            await anext(stream_gen)

    asyncio.run(_run_test())


def test_broadcaster_channel_isolation(clean_broadcaster):
    async def _run_test():
        bp_a = "bp_channel_a"
        bp_b = "bp_channel_b"

        stream_a = clean_broadcaster.stream_events(bp_a, include_buffer=False)
        stream_b = clean_broadcaster.stream_events(bp_b, include_buffer=False)

        await anext(stream_a)  # STREAM_CONNECTED
        await anext(stream_b)  # STREAM_CONNECTED

        # Broadcast to B only
        clean_broadcaster.broadcast(bp_b, "SCENE_START", {"scene_id": "b_1"})

        # Broadcast terminal to B
        clean_broadcaster.broadcast(bp_b, "ASSEMBLY_COMPLETE", {})

        chunk_b1 = await anext(stream_b)
        data_b1 = json.loads(chunk_b1.replace("data: ", "").strip())
        assert data_b1["scene_id"] == "b_1"

        # A should NOT receive B's event
        clean_broadcaster.broadcast(bp_a, "ASSEMBLY_COMPLETE", {})
        chunk_a = await anext(stream_a)
        data_a = json.loads(chunk_a.replace("data: ", "").strip())
        assert data_a["event"] == "ASSEMBLY_COMPLETE"

    asyncio.run(_run_test())


def test_auth_flexible_supports_both_header_and_query(clean_broadcaster):
    client = TestClient(app)
    user_id = "test_user_sse"
    project_id = "proj_sse_001"
    bp_id = "bp_sse_auth_test"

    app.dependency_overrides[get_current_user] = lambda: user_id
    app.dependency_overrides[get_current_user_flexible] = lambda: user_id

    mock_db = MagicMock()
    repo = BlueprintRepository()
    repo.db = mock_db

    bp = ProductionBlueprint(
        project_id=project_id,
        blueprint_id=bp_id,
        source_clone_blueprint_id="source_1",
        title="Test BP",
        concept="Concept",
        genre="Action",
        target_duration_seconds=15.0,
        scenes=[SceneBlueprint(scene_number=1, scene_id="scn_1", prompt="Hero walks", visual_description="Hero", dialogue=[], camera_direction=None, estimated_duration_seconds=5.0)],
        status="APPROVED"
    )

    with patch("core.repositories.blueprint_repo.BlueprintRepository.get", return_value=bp):
        # Broadcast terminal event into buffer so the stream finishes cleanly for TestClient
        clean_broadcaster.broadcast(bp_id, "ASSEMBLY_COMPLETE", {"status": "COMPLETED"})

        # 1. Test via query param token
        resp_query = client.get(f"/projects/{project_id}/production-blueprints/{bp_id}/events?token=mock_jwt_token")
        assert resp_query.status_code == 200
        assert "text/event-stream" in resp_query.headers.get("content-type", "")
        assert "STREAM_CONNECTED" in resp_query.text
        assert "ASSEMBLY_COMPLETE" in resp_query.text

        # 2. Test via standard Authorization header
        resp_header = client.get(
            f"/projects/{project_id}/production-blueprints/{bp_id}/events",
            headers={"Authorization": "Bearer mock_jwt_token"}
        )
        assert resp_header.status_code == 200
        assert "text/event-stream" in resp_header.headers.get("content-type", "")
        assert "STREAM_CONNECTED" in resp_header.text
        assert "ASSEMBLY_COMPLETE" in resp_header.text

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_user_flexible, None)


def test_sse_endpoint_404_for_unknown_blueprint():
    client = TestClient(app)
    user_id = "test_user_sse"
    project_id = "proj_sse_001"
    bp_id = "unknown_bp_id"

    app.dependency_overrides[get_current_user_flexible] = lambda: user_id

    with patch("core.repositories.blueprint_repo.BlueprintRepository.get", return_value=None), \
         patch("core.repositories.clone_blueprint_repo.CloneBlueprintRepository.get_latest", return_value=None):
        resp = client.get(f"/projects/{project_id}/production-blueprints/{bp_id}/events")
        assert resp.status_code == 404
        assert "Blueprint not found" in resp.json()["detail"]

    app.dependency_overrides.pop(get_current_user_flexible, None)
