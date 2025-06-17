#!/usr/bin/env python3
"""
Simple Local Node Client for Testing
"""

import asyncio
import aiohttp
import json
import logging
import uuid
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleNodeClient:
    def __init__(self):
        self.coordinator_url = "http://localhost:8000"
        self.stream_id = "test_stream_001"  
        self.node_id = f"local_test_node_{uuid.uuid4().hex[:8]}"
        self.public_ip = "127.0.0.1"
        self.stats_port = 8080
        
        logger.info(f"Simple Node Client initialized:")
        logger.info(f"  Node ID: {self.node_id}")
        logger.info(f"  Stream ID: {self.stream_id}")
        logger.info(f"  Coordinator: {self.coordinator_url}")
    
    async def send_heartbeat(self):
        """Send a heartbeat to the coordinator"""
        try:
            stats_url = f"http://{self.public_ip}:{self.stats_port}/stats.json"
            
            heartbeat_data = {
                "node_id": self.node_id,
                "stream_id": self.stream_id,
                "stats_url": stats_url,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.coordinator_url}/nodes/heartbeat"
                async with session.post(url, json=heartbeat_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Heartbeat sent successfully: {result}")
                        return True
                    else:
                        logger.error(f"❌ Heartbeat failed: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            return False
    
    async def test_coordinator_connection(self):
        """Test connection to coordinator"""
        try:
            async with aiohttp.ClientSession() as session:
                # Test health endpoint
                async with session.get(f"{self.coordinator_url}/health") as response:
                    if response.status == 200:
                        logger.info("✅ Coordinator health check passed")
                    else:
                        logger.error(f"❌ Coordinator health check failed: {response.status}")
                        return False
                
                # Test streams endpoint
                async with session.get(f"{self.coordinator_url}/streams") as response:
                    if response.status == 200:
                        streams = await response.json()
                        logger.info(f"✅ Found {len(streams)} streams")
                        for stream in streams:
                            logger.info(f"  - {stream['stream_id']}")
                        return True
                    else:
                        logger.error(f"❌ Streams endpoint failed: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error testing coordinator: {e}")
            return False
    
    async def run_test(self):
        """Run a complete test"""
        logger.info("🧪 Starting local node client test")
        
        # Test coordinator connection
        if not await self.test_coordinator_connection():
            logger.error("❌ Coordinator connection test failed")
            return False
        
        # Send a test heartbeat
        if not await self.send_heartbeat():
            logger.error("❌ Heartbeat test failed")
            return False
        
        logger.info("🎉 Local node client test completed successfully!")
        return True

async def main():
    client = SimpleNodeClient()
    success = await client.run_test()
    
    if success:
        logger.info("\n🎯 Next steps:")
        logger.info("1. Check dashboard: curl http://localhost:8000/dashboard | jq")
        logger.info("2. Start OBS and stream to rtmp://localhost:1935/live with key: test_stream_001")
        logger.info("3. Verify streaming works!")
    
    return success

if __name__ == "__main__":
    try:
        import aiohttp
    except ImportError:
        print("Installing aiohttp...")
        import subprocess
        subprocess.check_call(["pip", "install", "aiohttp"])
        import aiohttp
    
    result = asyncio.run(main())
    exit(0 if result else 1) 