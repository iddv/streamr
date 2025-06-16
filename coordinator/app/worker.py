#!/usr/bin/env python3
"""
Background worker for running Stats Collector and Spot-Check Prober services.
This should be run as a separate process alongside the main FastAPI server.
"""

import asyncio
import logging
import signal
import sys

from .stats_collector import run_stats_collector
from .spot_check_prober import run_spot_check_prober

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkerManager:
    def __init__(self):
        self.running = True
        self.tasks = []
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
        # Cancel all running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
    
    async def run(self):
        """Run all background services"""
        logger.info("Starting StreamrP2P Background Worker")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # Create tasks for both services
            stats_task = asyncio.create_task(run_stats_collector())
            prober_task = asyncio.create_task(run_spot_check_prober())
            
            self.tasks = [stats_task, prober_task]
            
            logger.info("All background services started")
            
            # Wait for all tasks to complete or be cancelled
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error in worker manager: {e}")
        finally:
            logger.info("Background worker shutdown complete")

async def main():
    """Main entry point"""
    worker = WorkerManager()
    await worker.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1) 