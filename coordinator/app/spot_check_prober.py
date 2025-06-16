import asyncio
import random
import logging
import subprocess
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from . import models, database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpotCheckProber:
    def __init__(self, check_interval_min: int = 5, check_interval_max: int = 15):
        self.check_interval_min = check_interval_min * 60  # Convert to seconds
        self.check_interval_max = check_interval_max * 60
    
    async def run_spot_checks(self):
        """Main spot check loop with random intervals"""
        logger.info("Starting Spot-Check Prober")
        
        while True:
            try:
                await self._perform_spot_check()
                
                # Random interval between checks to make it unpredictable
                interval = random.randint(self.check_interval_min, self.check_interval_max)
                logger.info(f"Next spot check in {interval//60} minutes")
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in spot check: {e}")
                await asyncio.sleep(60)  # Short retry delay
    
    async def _perform_spot_check(self):
        """Perform one spot check on a randomly selected healthy node"""
        db = database.SessionLocal()
        try:
            # Get nodes that have been reporting as healthy recently
            recent_time = datetime.utcnow() - timedelta(minutes=5)
            
            healthy_nodes = db.query(models.Node).join(models.ProbeResult).filter(
                and_(
                    models.Node.status == "active",
                    models.ProbeResult.probe_type == "stats_poll",
                    models.ProbeResult.success == True,
                    models.ProbeResult.probe_timestamp > recent_time
                )
            ).distinct().all()
            
            if not healthy_nodes:
                logger.info("No healthy nodes found for spot checking")
                return
            
            # Randomly select a node to test
            target_node = random.choice(healthy_nodes)
            logger.info(f"Performing spot check on node {target_node.node_id}")
            
            # Perform the actual RTMP connection test
            success, error_message = await self._test_rtmp_connection(target_node)
            
            # Store the spot check result
            probe_result = models.ProbeResult(
                stream_id=target_node.stream_id,
                node_id=target_node.node_id,
                probe_type="spot_check",
                success=success,
                error_message=error_message,
                probe_timestamp=datetime.utcnow()
            )
            db.add(probe_result)
            
            # If spot check failed but node was reporting healthy, flag it
            if not success:
                logger.warning(f"🚨 FRAUD DETECTED: Node {target_node.node_id} failed spot check!")
                target_node.status = "flagged"
                
                # Additional logging for investigation
                logger.error(f"Node {target_node.node_id} details:")
                logger.error(f"  Stream ID: {target_node.stream_id}")
                logger.error(f"  Stats URL: {target_node.stats_url}")
                logger.error(f"  Error: {error_message}")
            else:
                logger.info(f"✓ Node {target_node.node_id} passed spot check")
            
            db.commit()
            
        finally:
            db.close()
    
    async def _test_rtmp_connection(self, node: models.Node) -> tuple[bool, str]:
        """
        Test actual RTMP connection to the node.
        Returns (success, error_message)
        """
        try:
            # Construct RTMP URL based on node's expected configuration
            # Assuming nodes expose RTMP on port 1935 with stream path /live/{stream_id}
            node_ip = self._extract_ip_from_stats_url(node.stats_url)
            rtmp_url = f"rtmp://{node_ip}:1935/live/{node.stream_id}"
            
            logger.debug(f"Testing RTMP connection to: {rtmp_url}")
            
            # Use ffprobe to test the RTMP stream
            # This will attempt to connect and read stream metadata
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-timeout", "10000000",  # 10 second timeout in microseconds
                rtmp_url
            ]
            
            # Run ffprobe with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15.0)
                
                if process.returncode == 0:
                    # Successfully connected and got stream info
                    try:
                        stream_info = json.loads(stdout.decode())
                        streams = stream_info.get("streams", [])
                        if streams:
                            logger.debug(f"Successfully connected to {rtmp_url}, found {len(streams)} streams")
                            return True, None
                        else:
                            return False, "No streams found in RTMP connection"
                    except json.JSONDecodeError:
                        return False, "Invalid JSON response from ffprobe"
                else:
                    error_msg = stderr.decode().strip()
                    return False, f"ffprobe failed (code {process.returncode}): {error_msg}"
                    
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return False, "Connection timeout"
                
        except Exception as e:
            return False, f"Spot check error: {str(e)}"
    
    def _extract_ip_from_stats_url(self, stats_url: str) -> str:
        """Extract IP address from stats URL like http://192.168.1.100:8080/stats.json"""
        try:
            # Remove protocol and path
            url_part = stats_url.replace("http://", "").replace("https://", "")
            ip_port = url_part.split("/")[0]
            ip = ip_port.split(":")[0]
            return ip
        except Exception:
            # Fallback - return the original URL and let the connection fail gracefully
            return stats_url
    
    async def flag_inactive_nodes(self):
        """Flag nodes that haven't sent heartbeats recently"""
        db = database.SessionLocal()
        try:
            # Flag nodes that haven't sent heartbeat in last 5 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)
            
            inactive_nodes = db.query(models.Node).filter(
                and_(
                    models.Node.status == "active",
                    models.Node.last_heartbeat < cutoff_time
                )
            ).all()
            
            for node in inactive_nodes:
                logger.info(f"Flagging inactive node: {node.node_id}")
                node.status = "inactive"
            
            if inactive_nodes:
                db.commit()
                logger.info(f"Flagged {len(inactive_nodes)} inactive nodes")
                
        finally:
            db.close()

# Background task runner
async def run_spot_check_prober():
    """Entry point for running the spot check prober as a background service"""
    prober = SpotCheckProber(check_interval_min=5, check_interval_max=15)
    
    # Run inactive node cleanup every 2 minutes
    async def cleanup_inactive_nodes():
        while True:
            await asyncio.sleep(120)  # 2 minutes
            await prober.flag_inactive_nodes()
    
    # Run both tasks concurrently
    await asyncio.gather(
        prober.run_spot_checks(),
        cleanup_inactive_nodes()
    )

if __name__ == "__main__":
    asyncio.run(run_spot_check_prober()) 