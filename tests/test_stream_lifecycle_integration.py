import pytest
import httpx
import uuid
from typing import Dict, Any


@pytest.mark.asyncio
async def test_stream_lifecycle_state_machine(
    coordinator_client: httpx.AsyncClient,
    test_stream_data: Dict[str, Any],
    auth_headers: dict,
    cleanup_test_streams,
):
    """
    Test the complete stream lifecycle state machine:
    READY → TESTING → LIVE → OFFLINE → STALE → ARCHIVED
    """
    stream_id = f"test-lifecycle-{uuid.uuid4().hex[:8]}"
    stream_data = {**test_stream_data, "stream_id": stream_id}
    cleanup_test_streams(stream_id)

    # 1. Create stream (should start in READY state)
    response = await coordinator_client.post(
        "/streams", json=stream_data, headers=auth_headers
    )
    assert response.status_code == 200
    created_stream = response.json()
    assert created_stream["status"] == "READY"
    assert created_stream["stream_id"] == stream_id

    # 2. READY → TESTING
    response = await coordinator_client.patch(
        f"/streams/{stream_id}/status",
        json={"status": "TESTING"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["new_state"] == "TESTING"

    # 3. TESTING → LIVE
    response = await coordinator_client.patch(
        f"/streams/{stream_id}/status",
        json={"status": "LIVE"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["new_state"] == "LIVE"

    # 4. Verify stream appears in /streams/live
    response = await coordinator_client.get("/streams/live")
    assert response.status_code == 200
    live_ids = [s["stream_id"] for s in response.json()]
    assert stream_id in live_ids

    # 5. LIVE → OFFLINE
    response = await coordinator_client.patch(
        f"/streams/{stream_id}/status",
        json={"status": "OFFLINE"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["new_state"] == "OFFLINE"

    # 6. Verify stream no longer in /streams/live
    response = await coordinator_client.get("/streams/live")
    assert response.status_code == 200
    live_ids = [s["stream_id"] for s in response.json()]
    assert stream_id not in live_ids

    # 7. OFFLINE → STALE
    response = await coordinator_client.patch(
        f"/streams/{stream_id}/status",
        json={"status": "STALE"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["new_state"] == "STALE"

    # 8. STALE → ARCHIVED (terminal)
    response = await coordinator_client.patch(
        f"/streams/{stream_id}/status",
        json={"status": "ARCHIVED"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["new_state"] == "ARCHIVED"


@pytest.mark.asyncio
async def test_invalid_state_transitions(
    coordinator_client: httpx.AsyncClient,
    test_stream_data: Dict[str, Any],
    auth_headers: dict,
    cleanup_test_streams,
):
    """Test that invalid state transitions are rejected."""
    stream_id = f"test-invalid-{uuid.uuid4().hex[:8]}"
    stream_data = {**test_stream_data, "stream_id": stream_id}
    cleanup_test_streams(stream_id)

    response = await coordinator_client.post(
        "/streams", json=stream_data, headers=auth_headers
    )
    assert response.status_code == 200

    # READY → OFFLINE is not a valid transition
    response = await coordinator_client.patch(
        f"/streams/{stream_id}/status",
        json={"status": "OFFLINE"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "invalid transition" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_stream_status_filtering(
    coordinator_client: httpx.AsyncClient,
    test_stream_data: Dict[str, Any],
    auth_headers: dict,
    cleanup_test_streams,
):
    """Test the status filtering on /streams endpoint."""
    stream_id = f"test-filter-{uuid.uuid4().hex[:8]}"
    stream_data = {**test_stream_data, "stream_id": stream_id}
    cleanup_test_streams(stream_id)

    await coordinator_client.post(
        "/streams", json=stream_data, headers=auth_headers
    )
    await coordinator_client.patch(
        f"/streams/{stream_id}/status",
        json={"status": "TESTING"},
        headers=auth_headers,
    )

    # Should appear in TESTING filter
    response = await coordinator_client.get("/streams?status=TESTING")
    assert response.status_code == 200
    testing_ids = [s["stream_id"] for s in response.json()]
    assert stream_id in testing_ids

    # Should NOT appear in READY filter
    response = await coordinator_client.get("/streams?status=READY")
    assert response.status_code == 200
    ready_ids = [s["stream_id"] for s in response.json()]
    assert stream_id not in ready_ids


@pytest.mark.asyncio
async def test_timestamp_tracking(
    coordinator_client: httpx.AsyncClient,
    test_stream_data: Dict[str, Any],
    auth_headers: dict,
    cleanup_test_streams,
):
    """Test that lifecycle timestamps are properly tracked."""
    stream_id = f"test-timestamps-{uuid.uuid4().hex[:8]}"
    stream_data = {**test_stream_data, "stream_id": stream_id}
    cleanup_test_streams(stream_id)

    await coordinator_client.post(
        "/streams", json=stream_data, headers=auth_headers
    )
    await coordinator_client.patch(
        f"/streams/{stream_id}/status",
        json={"status": "LIVE"},
        headers=auth_headers,
    )

    response = await coordinator_client.get("/streams")
    assert response.status_code == 200
    streams = response.json()

    test_stream = next((s for s in streams if s["stream_id"] == stream_id), None)
    assert test_stream is not None
    assert test_stream["live_started_at"] is not None
    assert test_stream["offline_at"] is None
