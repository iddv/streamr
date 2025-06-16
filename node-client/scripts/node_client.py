#!/usr/bin/env python3
"""
StreamrP2P Node Client

This script manages an RTMP relay node for the "restreaming as support" PoC.
It starts an rtmp_relay server and sends periodic heartbeats to the Coordinator.
"""

import asyncio
import aiohttp
import json
import logging
import os
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeClient:
    def __init__(self):
        # Configuration from environment variables
        self.coordinator_url = os.getenv('COORDINATOR_URL', 'http://localhost:8000')
        self.stream_id = os.getenv('STREAM_ID')
        self.node_id = os.getenv('NODE_ID', f"node_{uuid.uuid4().hex[:8]}")
        self.rtmp_port = int(os.getenv('RTMP_PORT', '1935'))
        self.stats_port = int(os.getenv('STATS_PORT', '8080'))
        self.heartbeat_interval = int(os.getenv('HEARTBEAT_INTERVAL', '30'))
        
        # Internal state
        self.running = True
        self.relay_process = None
        self.public_ip = None
        
        # Validate required configuration
        if not self.stream_id:
            logger.error("STREAM_ID environment variable is required")
            sys.exit(1)
        
        logger.info(f"Node Client initialized:")
        logger.info(f"  Node ID: {self.node_id}")
        logger.info(f"  Stream ID: {self.stream_id}")
        logger.info(f"  Coordinator: {self.coordinator_url}")
        logger.info(f"  RTMP Port: {self.rtmp_port}")
        logger.info(f"  Stats Port: {self.stats_port}")
    
    async def start(self):
        """Main entry point - start the node client"""
        logger.info("Starting StreamrP2P Node Client")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            # Discover public IP
            await self._discover_public_ip()
            
            # Fetch stream information from coordinator
            stream_info = await self._fetch_stream_info()
            if not stream_info:
                logger.error("Failed to fetch stream information")
                return
            
            # Start the RTMP relay
            await self._start_rtmp_relay(stream_info['rtmp_url'])
            
            # Start heartbeat loop
            await self._heartbeat_loop()
            
        except Exception as e:
            logger.error(f"Error in node client: {e}")
        finally:
            await self._cleanup()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def _discover_public_ip(self):
        """Discover the public IP address of this node"""
        try:
            async with aiohttp.ClientSession() as session:
                # Try multiple IP discovery services
                services = [
                    'https://api.ipify.org',
                    'https://ifconfig.me/ip',
                    'https://icanhazip.com'
                ]
                
                for service in services:
                    try:
                        async with session.get(service, timeout=5) as response:
                            if response.status == 200:
                                self.public_ip = (await response.text()).strip()
                                logger.info(f"Discovered public IP: {self.public_ip}")
                                return
                    except Exception as e:
                        logger.debug(f"Failed to get IP from {service}: {e}")
                
                # Fallback to localhost if all services fail
                self.public_ip = "127.0.0.1"
                logger.warning("Could not discover public IP, using localhost")
                
        except Exception as e:
            logger.error(f"Error discovering public IP: {e}")
            self.public_ip = "127.0.0.1"
    
    async def _fetch_stream_info(self):
        """Fetch stream information from the coordinator"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.coordinator_url}/streams"
                async with session.get(url) as response:
                    if response.status == 200:
                        streams = await response.json()
                        
                        # Find our stream
                        for stream in streams:
                            if stream['stream_id'] == self.stream_id:
                                logger.info(f"Found stream: {stream['stream_id']}")
                                return stream
                        
                        logger.error(f"Stream {self.stream_id} not found in coordinator")
                        return None
                    else:
                        logger.error(f"Failed to fetch streams: HTTP {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error fetching stream info: {e}")
            return None
    
    async def _start_rtmp_relay(self, source_rtmp_url):
        """Start the RTMP relay server"""
        logger.info(f"Starting RTMP relay from {source_rtmp_url}")
        
        # Create rtmp_relay configuration
        config = {
            "servers": [{
                "endpoints": [
                    {
                        "addresses": [source_rtmp_url],
                        "type": "client",
                        "direction": "input",
                        "applicationName": "live",
                        "streamName": self.stream_id,
                        "video": True,
                        "audio": True,
                        "reconnectInterval": 5.0,
                        "reconnectCount": 0  # Reconnect forever
                    },
                    {
                        "addresses": [f"0.0.0.0:{self.rtmp_port}"],
                        "type": "host",
                        "direction": "output",
                        "applicationName": "live",
                        "streamName": self.stream_id,
                        "video": True,
                        "audio": True
                    }
                ]
            }],
            "statusPage": {
                "address": f"0.0.0.0:{self.stats_port}"
            },
            "log": {
                "level": 2
            }
        }
        
        # Write config file
        config_path = "/tmp/rtmp_relay_config.yaml"
        with open(config_path, 'w') as f:
            import yaml
            yaml.dump(config, f)
        
        # Start rtmp_relay process
        try:
            cmd = ["rtmp_relay", "--config", config_path]
            self.relay_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            logger.info(f"RTMP relay started with PID {self.relay_process.pid}")
            
            # Give it a moment to start
            await asyncio.sleep(2)
            
            # Check if process is still running
            if self.relay_process.poll() is not None:
                stdout, stderr = self.relay_process.communicate()
                logger.error(f"RTMP relay failed to start:")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                raise Exception("RTMP relay process died immediately")
            
            logger.info("RTMP relay is running successfully")
            
        except Exception as e:
            logger.error(f"Failed to start RTMP relay: {e}")
            raise
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to the coordinator"""
        logger.info("Starting heartbeat loop")
        
        while self.running:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)  # Short retry delay
    
    async def _send_heartbeat(self):
        """Send a single heartbeat to the coordinator"""
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
                        logger.debug("Heartbeat sent successfully")
                    else:
                        logger.warning(f"Heartbeat failed: HTTP {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
    
    async def _cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up...")
        
        if self.relay_process:
            logger.info("Stopping RTMP relay")
            self.relay_process.terminate()
            
            # Wait for graceful shutdown
            try:
                self.relay_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("RTMP relay didn't stop gracefully, killing it")
                self.relay_process.kill()
                self.relay_process.wait()
            
            logger.info("RTMP relay stopped")

async def main():
    """Main entry point"""
    client = NodeClient()
    await client.start()

if __name__ == "__main__":
    try:
        # Install required packages if not available
        try:
            import yaml
            import aiohttp
        except ImportError:
            logger.info("Installing required packages...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "aiohttp"])
            import yaml
            import aiohttp
        
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Node client interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Node client failed: {e}")
        sys.exit(1) 