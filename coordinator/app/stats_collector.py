import asyncio
import httpx
import json
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, Any

from . import models, database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StatsCollector:
    def __init__(self, poll_interval: int = 60):
        self.poll_interval = poll_interval
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def collect_stats(self):
        """Main collection loop"""
        logger.info("Starting Stats Collector")
        
        while True:
            try:
                await self._collect_round()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in stats collection: {e}")
                await asyncio.sleep(5)  # Short retry delay
    
    async def _collect_round(self):
        """Perform one round of stats collection"""
        db = database.SessionLocal()
        try:
            # Get all active nodes
            active_nodes = db.query(models.Node).filter(
                models.Node.status == "active"
            ).all()
            
            logger.info(f"Collecting stats from {len(active_nodes)} active nodes")
            
            # Collect stats from all nodes concurrently
            tasks = [self._collect_node_stats(node, db) for node in active_nodes]
            await asyncio.gather(*tasks, return_exceptions=True)
            
        finally:
            db.close()
    
    async def _collect_node_stats(self, node: models.Node, db: Session):
        """Collect stats from a single node"""
        try:
            # Make request to node's stats endpoint
            response = await self.client.get(node.stats_url)
            
            if response.status_code == 200:
                stats_data = response.json()
                success = self._validate_stats_data(stats_data, node.stream_id)
                
                # Store successful probe result
                probe_result = models.ProbeResult(
                    stream_id=node.stream_id,
                    node_id=node.node_id,
                    probe_type="stats_poll",
                    success=success,
                    response_data=json.dumps(stats_data),
                    probe_timestamp=datetime.utcnow()
                )
                
                if success:
                    logger.debug(f"✓ Node {node.node_id} stats collected successfully")
                else:
                    logger.warning(f"⚠ Node {node.node_id} stats invalid - no active stream found")
                    
            else:
                # Store failed probe result
                probe_result = models.ProbeResult(
                    stream_id=node.stream_id,
                    node_id=node.node_id,
                    probe_type="stats_poll",
                    success=False,
                    error_message=f"HTTP {response.status_code}: {response.text}",
                    probe_timestamp=datetime.utcnow()
                )
                logger.warning(f"✗ Node {node.node_id} stats collection failed: HTTP {response.status_code}")
                
        except Exception as e:
            # Store error probe result
            probe_result = models.ProbeResult(
                stream_id=node.stream_id,
                node_id=node.node_id,
                probe_type="stats_poll",
                success=False,
                error_message=str(e),
                probe_timestamp=datetime.utcnow()
            )
            logger.error(f"✗ Node {node.node_id} stats collection error: {e}")
        
        # Save probe result to database
        db.add(probe_result)
        db.commit()
    
    def _validate_stats_data(self, stats_data: Dict[Any, Any], expected_stream_id: str) -> bool:
        """
        Validate that the stats data shows the node is actively relaying the expected stream.
        Based on our research of elnormous/rtmp_relay stats.json structure.
        """
        try:
            # Check if there are active streams
            streams = stats_data.get("streams", [])
            if not streams:
                return False
            
            # Look for our stream in the active streams
            for stream in streams:
                stream_name = stream.get("stream_name", "")
                connections = stream.get("connections", [])
                
                # Check if this matches our expected stream and has active connections
                if expected_stream_id in stream_name and len(connections) > 0:
                    # Check if any connection is in a healthy state
                    for conn in connections:
                        state = conn.get("state", "").lower()
                        if state in ["publishing", "streaming", "connected"]:
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating stats data: {e}")
            return False
    
    async def cleanup_old_results(self, days_to_keep: int = 7):
        """Clean up old probe results to prevent database bloat"""
        db = database.SessionLocal()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            deleted = db.query(models.ProbeResult).filter(
                models.ProbeResult.probe_timestamp < cutoff_date
            ).delete()
            db.commit()
            logger.info(f"Cleaned up {deleted} old probe results")
        finally:
            db.close()

# Background task runner
async def run_stats_collector():
    """Entry point for running the stats collector as a background service"""
    collector = StatsCollector(poll_interval=60)  # Poll every 60 seconds
    
    # Run cleanup once per day
    async def daily_cleanup():
        while True:
            await asyncio.sleep(24 * 60 * 60)  # 24 hours
            await collector.cleanup_old_results()
    
    # Run both tasks concurrently
    await asyncio.gather(
        collector.collect_stats(),
        daily_cleanup()
    )

if __name__ == "__main__":
    asyncio.run(run_stats_collector()) 