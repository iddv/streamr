import pytest
import httpx
from typing import List, Dict, Any

@pytest.mark.asyncio
async def test_production_health_check(production_client: httpx.AsyncClient):
    """Test that production coordinator is responding."""
    response = await production_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

@pytest.mark.asyncio
async def test_production_streams_endpoint(production_client: httpx.AsyncClient):
    """Test that /streams endpoint is working in production."""
    response = await production_client.get("/streams")
    assert response.status_code == 200
    streams = response.json()
    assert isinstance(streams, list)
    
    # Validate stream structure if any exist
    if streams:
        stream = streams[0]
        required_fields = ["stream_id", "status", "created_at"]
        for field in required_fields:
            assert field in stream
            
        # Check which system is deployed
        if stream["status"] in ["READY", "TESTING", "LIVE", "OFFLINE", "STALE", "ARCHIVED"]:
            print("✅ Stream Lifecycle System detected in production")
        else:
            print("⚠️  Old system detected - Stream Lifecycle System not yet deployed")

@pytest.mark.asyncio  
async def test_production_live_streams_endpoint(production_client: httpx.AsyncClient):
    """Test the /streams/live endpoint if it exists (Stream Lifecycle System)."""
    response = await production_client.get("/streams/live")
    
    if response.status_code == 405:
        # Old system - /streams/live doesn't exist yet
        print("⚠️  /streams/live endpoint not deployed yet (expected for old system)")
        return
    
    # New system - should work correctly
    assert response.status_code == 200
    live_streams = response.json()
    assert isinstance(live_streams, list)
    
    # All returned streams should have LIVE status
    for stream in live_streams:
        assert stream["status"] == "LIVE"

@pytest.mark.asyncio
async def test_production_status_filtering(production_client: httpx.AsyncClient):
    """Test status filtering works in production (if Stream Lifecycle System is deployed)."""
    # First check what system is deployed
    response = await production_client.get("/streams")
    assert response.status_code == 200
    streams = response.json()
    
    if not streams:
        print("⚠️  No streams in production to test filtering")
        return
        
    # Check if new system is deployed
    sample_stream = streams[0]
    has_lifecycle = sample_stream["status"] in ["READY", "TESTING", "LIVE", "OFFLINE", "STALE", "ARCHIVED"]
    
    if not has_lifecycle:
        print("⚠️  Status filtering test skipped - Stream Lifecycle System not deployed yet")
        return
    
    # Test new lifecycle status filters
    statuses = ["ALL", "READY", "TESTING", "LIVE", "OFFLINE", "STALE", "ARCHIVED"]
    
    for status in statuses:
        response = await production_client.get(f"/streams?status={status}")
        assert response.status_code == 200
        filtered_streams = response.json()
        assert isinstance(filtered_streams, list)
        
        # If not ALL, verify all returned streams have correct status  
        if status != "ALL" and filtered_streams:
            for stream in filtered_streams:
                assert stream["status"] == status

@pytest.mark.asyncio
async def test_production_api_performance(production_client: httpx.AsyncClient):
    """Basic performance test - endpoints should respond quickly."""
    import time
    
    # Core endpoints that should always exist
    endpoints = ["/", "/streams"]
    
    for endpoint in endpoints:
        start_time = time.time()
        response = await production_client.get(endpoint)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 2.0, f"{endpoint} took {response_time:.2f}s (too slow)"
    
    # Test /streams/live if it exists (Stream Lifecycle System)
    start_time = time.time()
    response = await production_client.get("/streams/live")
    end_time = time.time()
    
    if response.status_code == 200:
        # New system - should be fast
        response_time = end_time - start_time
        assert response_time < 2.0, f"/streams/live took {response_time:.2f}s (too slow)"
        print("✅ /streams/live endpoint performance OK")
    else:
        print("⚠️  /streams/live endpoint not available (Stream Lifecycle System not deployed)")

@pytest.mark.asyncio
async def test_production_dashboard_endpoint(production_client: httpx.AsyncClient):
    """Test that dashboard endpoint works and returns expected format."""
    # Test basic dashboard
    response = await production_client.get("/dashboard")
    assert response.status_code == 200
    dashboard_data = response.json()
    assert "streams" in dashboard_data
    streams_list = dashboard_data["streams"]
    assert isinstance(streams_list, list)
    print("✅ Dashboard endpoint responding")
    
    # Test pagination parameter
    response = await production_client.get("/dashboard?limit=5")
    assert response.status_code == 200
    limited_data = response.json()["streams"]
    assert isinstance(limited_data, list)
    assert len(limited_data) <= 5
    print("✅ Dashboard pagination working")
    
    # Test node status filtering 
    response = await production_client.get("/dashboard?node_statuses=active")
    assert response.status_code == 200
    filtered_data = response.json()["streams"]
    assert isinstance(filtered_data, list)
    print("✅ Dashboard node filtering working")
    
    # Validate response structure if any streams exist
    if streams_list:
        stream = streams_list[0]
        required_fields = ["stream_id", "status", "node_count", "nodes"]
        for field in required_fields:
            assert field in stream, f"Missing dashboard field: {field}"
        
        # Ensure we're using new field name, not old one
        assert "active_nodes" not in stream, "Dashboard still using old 'active_nodes' field!"
        print("✅ Dashboard response schema validation passed")

@pytest.mark.asyncio
async def test_production_api_schema_validation(production_client: httpx.AsyncClient):
    """Validate that production API returns expected data structures."""
    # Test stream schema
    response = await production_client.get("/streams")
    assert response.status_code == 200
    streams = response.json()
    
    if streams:
        stream = streams[0]
        # Core fields that should always exist
        core_fields = ["stream_id", "status", "created_at"]
        for field in core_fields:
            assert field in stream, f"Missing core field: {field}"
        
        # Check if Stream Lifecycle System is deployed
        if stream["status"] in ["READY", "TESTING", "LIVE", "OFFLINE", "STALE", "ARCHIVED"]:
            # Validate new lifecycle fields exist
            lifecycle_fields = [
                "live_started_at", "offline_at", "testing_started_at", 
                "stale_at", "archived_at"
            ]
            for field in lifecycle_fields:
                assert field in stream, f"Missing lifecycle field: {field}"
            print("✅ Stream Lifecycle System schema validation passed")
        else:
            # Old system - validate basic fields
            assert stream["status"] in ["active", "inactive"], f"Unexpected old system status: {stream['status']}"
            print("⚠️  Old system schema detected - Stream Lifecycle System not deployed yet") 