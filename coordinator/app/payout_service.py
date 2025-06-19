import logging
import time
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, case
from typing import Dict, List

from . import models, database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Performance monitoring decorator
def monitor_query_performance(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        logger.info(f"Query {func.__name__} took {duration:.3f}s")
        return result
    return wrapper

class PayoutService:
    def __init__(self):
        # Configurable penalty factor (0.5 = 50% penalty per failure)
        self.PENALTY_FACTOR = 0.5
    
    @monitor_query_performance
    def calculate_payouts(self, hours_back: int = 1) -> Dict[str, Dict]:
        """
        Calculate payouts for the last N hours based on probe results.
        Uses contribution-weighted model with graduated penalties.
        OPTIMIZED: Single query instead of N+1 queries per stream.
        """
        db = database.SessionLocal()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Get all active streams
            active_streams = db.query(models.Stream).filter(
                models.Stream.status == "active"
            ).all()
            
            payout_data = {}
            
            for stream in active_streams:
                logger.info(f"Calculating payouts for stream: {stream.stream_id}")
                
                # OPTIMIZED: Single query to get all node stats for this stream
                # This replaces the N+1 query pattern with one efficient query
                node_stats = db.query(
                    models.ProbeResult.node_id,
                    func.count(
                        case([(models.ProbeResult.probe_type == 'stats_poll', 1)], else_=None)
                    ).label('total_polls'),
                    func.count(
                        case([
                            (and_(
                                models.ProbeResult.probe_type == 'stats_poll',
                                models.ProbeResult.success == True
                            ), 1)
                        ], else_=None)
                    ).label('successful_polls'),
                    func.count(
                        case([
                            (and_(
                                models.ProbeResult.probe_type == 'spot_check',
                                models.ProbeResult.success == False
                            ), 1)
                        ], else_=None)
                    ).label('failed_spot_checks')
                ).filter(
                    models.ProbeResult.stream_id == stream.stream_id,
                    models.ProbeResult.probe_timestamp > cutoff_time
                ).group_by(models.ProbeResult.node_id).all()
                
                if not node_stats:
                    logger.info(f"No participating node stats for stream {stream.stream_id}")
                    continue
                
                # Calculate total successful probes across all nodes (for contribution weighting)
                total_successful_probes = sum(stats.successful_polls for stats in node_stats)
                
                if total_successful_probes == 0:
                    logger.info(f"No successful probes for stream {stream.stream_id}")
                    continue
                
                node_payouts = {}
                total_pool = stream.token_balance
                
                for stats in node_stats:
                    # Contribution-weighted payout model
                    contribution_percentage = stats.successful_polls / total_successful_probes
                    base_payout = total_pool * contribution_percentage
                    
                    # Graduated penalty model (more fair than zero-tolerance)
                    penalty_multiplier = (1 - self.PENALTY_FACTOR) ** stats.failed_spot_checks
                    final_payout = base_payout * penalty_multiplier
                    
                    # Calculate uptime percentage for display
                    uptime_percentage = (stats.successful_polls / stats.total_polls) if stats.total_polls > 0 else 0
                    
                    node_payouts[stats.node_id] = {
                        "base_payout": base_payout,
                        "final_payout": final_payout,
                        "contribution_percentage": contribution_percentage,
                        "uptime_percentage": uptime_percentage,
                        "total_polls": stats.total_polls,
                        "successful_polls": stats.successful_polls,
                        "failed_spot_checks": stats.failed_spot_checks,
                        "penalty_multiplier": penalty_multiplier,
                        "is_flagged": stats.failed_spot_checks > 0,
                        "penalty_reason": f"{stats.failed_spot_checks} failed spot checks" if stats.failed_spot_checks > 0 else None
                    }
                    
                    logger.info(f"Node {stats.node_id}: {contribution_percentage:.1%} contribution, "
                              f"{uptime_percentage:.1%} uptime, {final_payout:.2f} tokens" + 
                              (f" (penalty: {penalty_multiplier:.2f})" if stats.failed_spot_checks > 0 else ""))
                
                payout_data[stream.stream_id] = {
                    "stream_info": {
                        "stream_id": stream.stream_id,
                        "sponsor": stream.sponsor_address,
                        "total_pool": total_pool,
                        "total_successful_probes": total_successful_probes,
                        "active_nodes": len(node_stats),
                        "calculation_period": f"Last {hours_back} hour(s)",
                        "payout_model": "contribution-weighted"
                    },
                    "node_payouts": node_payouts
                }
            
            return payout_data
            
        finally:
            db.close()
    
    @monitor_query_performance 
    def get_node_earnings_summary(self, node_id: str, days_back: int = 7) -> Dict:
        """Get earnings summary for a specific node - OPTIMIZED VERSION"""
        db = database.SessionLocal()
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days_back)
            
            # OPTIMIZED: Single query to get all node performance across streams
            stream_stats = db.query(
                models.ProbeResult.stream_id,
                func.count(
                    case([(models.ProbeResult.probe_type == 'stats_poll', 1)], else_=None)
                ).label('total_polls'),
                func.count(
                    case([
                        (and_(
                            models.ProbeResult.probe_type == 'stats_poll',
                            models.ProbeResult.success == True
                        ), 1)
                    ], else_=None)
                ).label('successful_polls'),
                func.count(
                    case([
                        (and_(
                            models.ProbeResult.probe_type == 'spot_check',
                            models.ProbeResult.success == False
                        ), 1)
                    ], else_=None)
                ).label('failed_spot_checks')
            ).filter(
                models.ProbeResult.node_id == node_id,
                models.ProbeResult.probe_timestamp > cutoff_time
            ).group_by(models.ProbeResult.stream_id).all()
            
            total_earnings = 0
            stream_details = []
            
            for stats in stream_stats:
                # Get stream info
                stream = db.query(models.Stream).filter(
                    models.Stream.stream_id == stats.stream_id
                ).first()
                
                if not stream:
                    continue
                
                uptime = (stats.successful_polls / stats.total_polls) if stats.total_polls > 0 else 0
                
                # Simplified earnings calculation for summary
                penalty_multiplier = (1 - self.PENALTY_FACTOR) ** stats.failed_spot_checks
                estimated_earnings = (stream.token_balance * 0.1) * uptime * penalty_multiplier
                total_earnings += estimated_earnings
                
                stream_details.append({
                    "stream_id": stats.stream_id,
                    "uptime_percentage": uptime,
                    "estimated_earnings": estimated_earnings,
                    "total_polls": stats.total_polls,
                    "successful_polls": stats.successful_polls,
                    "failed_spot_checks": stats.failed_spot_checks,
                    "penalty_multiplier": penalty_multiplier
                })
            
            return {
                "node_id": node_id,
                "period": f"Last {days_back} days",
                "total_estimated_earnings": total_earnings,
                "streams_participated": len(stream_stats),
                "stream_details": stream_details,
                "payout_model": "contribution-weighted"
            }
            
        finally:
            db.close()
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top performing nodes by estimated earnings"""
        db = database.SessionLocal()
        try:
            # Get nodes with their performance metrics
            cutoff_time = datetime.utcnow() - timedelta(days=7)
            
            # This is a simplified leaderboard - in production you'd want more sophisticated metrics
            node_stats = db.query(
                models.Node.node_id,
                func.count(models.ProbeResult.id).label('total_probes'),
                func.sum(models.ProbeResult.success.cast(db.bind.dialect.INTEGER)).label('successful_probes')
            ).join(models.ProbeResult).filter(
                and_(
                    models.ProbeResult.probe_type == "stats_poll",
                    models.ProbeResult.probe_timestamp > cutoff_time
                )
            ).group_by(models.Node.node_id).order_by(
                func.sum(models.ProbeResult.success.cast(db.bind.dialect.INTEGER)).desc()
            ).limit(limit).all()
            
            leaderboard = []
            for node_id, total_probes, successful_probes in node_stats:
                uptime = (successful_probes / total_probes) if total_probes > 0 else 0
                
                leaderboard.append({
                    "node_id": node_id,
                    "uptime_percentage": uptime,
                    "total_probes": total_probes,
                    "successful_probes": successful_probes,
                    "estimated_score": successful_probes  # Simple scoring
                })
            
            return leaderboard
            
        finally:
            db.close()

# Utility function for manual payout calculation
def calculate_and_display_payouts(hours_back: int = 1):
    """Utility function to calculate and display payouts"""
    payout_service = PayoutService()
    payouts = payout_service.calculate_payouts(hours_back)
    
    print(f"\n=== PAYOUT CALCULATION (Last {hours_back} hour(s)) ===")
    
    for stream_id, stream_data in payouts.items():
        print(f"\nStream: {stream_id}")
        print(f"Sponsor: {stream_data['stream_info']['sponsor']}")
        print(f"Total Pool: {stream_data['stream_info']['total_pool']} tokens")
        print("Node Payouts:")
        
        for node_id, payout_info in stream_data['node_payouts'].items():
            status = "🚨 FLAGGED" if payout_info['is_flagged'] else "✓"
            print(f"  {node_id}: {payout_info['final_payout']:.2f} tokens "
                  f"({payout_info['uptime_percentage']:.1%} uptime) {status}")

if __name__ == "__main__":
    calculate_and_display_payouts() 