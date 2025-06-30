import pytest
import pytest_asyncio
import asyncio
import httpx
import os
from typing import AsyncGenerator

# Flexible coordinator URL configuration for different environments
COORDINATOR_URL = os.getenv("COORDINATOR_URL", "http://localhost:8000")
TEST_TARGET = os.getenv("TEST_TARGET", "local")  # local, production, or any custom URL

# URL mapping for different test targets
URL_MAP = {
    "local": "http://localhost:8000",
    "production": "http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com",
    "beta": "http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com"
}

def get_coordinator_url() -> str:
    """Get coordinator URL based on TEST_TARGET or COORDINATOR_URL environment variables."""
    # Direct URL override takes precedence
    if "COORDINATOR_URL" in os.environ:
        return os.environ["COORDINATOR_URL"]
    
    # Use predefined target mapping
    target = os.getenv("TEST_TARGET", "local")
    if target in URL_MAP:
        return URL_MAP[target]
    
    # Assume TEST_TARGET is a direct URL if not in mapping
    if target.startswith("http"):
        return target
    
    # Fallback to local
    return URL_MAP["local"]

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def coordinator_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client for coordinator API testing against configured target."""
    url = get_coordinator_url()
    timeout = httpx.Timeout(10.0, connect=5.0)
    
    print(f"🎯 Testing against: {url}")
    
    async with httpx.AsyncClient(
        base_url=url,
        timeout=timeout,
        headers={"Content-Type": "application/json"}
    ) as client:
        yield client

# Alias for backward compatibility with existing tests
@pytest_asyncio.fixture
async def production_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Alias for coordinator_client for backward compatibility."""
    url = get_coordinator_url()
    timeout = httpx.Timeout(10.0, connect=5.0)
    
    print(f"🎯 Testing against: {url}")
    
    async with httpx.AsyncClient(
        base_url=url,
        timeout=timeout,
        headers={"Content-Type": "application/json"}
    ) as client:
        yield client

@pytest.fixture
def test_stream_data():
    """Test data for stream creation."""
    return {
        "stream_id": "integration-test-stream",
        "sponsor_address": "test_sponsor",
        "token_balance": 1000.0,
        "rtmp_url": "rtmp://test.example.com/live/integration-test-stream"
    }

@pytest_asyncio.fixture
async def cleanup_test_streams():
    """Cleanup fixture to remove test streams after tests."""
    created_streams = []
    
    def track_stream(stream_id: str):
        created_streams.append(stream_id)
    
    yield track_stream
    
    # Cleanup after test - create our own client for cleanup
    url = get_coordinator_url()
    timeout = httpx.Timeout(10.0, connect=5.0)
    
    async with httpx.AsyncClient(
        base_url=url,
        timeout=timeout,
        headers={"Content-Type": "application/json"}
    ) as client:
        for stream_id in created_streams:
            try:
                await client.delete(f"/streams/{stream_id}")
            except:
                pass  # Ignore cleanup failures 