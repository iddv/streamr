import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Dict, List

from . import models, database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PayoutService:
    def __init__(self):
        pass
    
    def calculate_payouts(self, hours_back: int = 1) -> Dict[str, Dict]:
        """
        Calculate payouts for the last N hours based on probe results.
        Returns a dictionary of {stream_id: {node_id: payout_info}}
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
                
                # Get all nodes that participated in this stream
                participating_nodes = db.query(models.Node.node_id).filter(
                    and_(
                        models.Node.stream_id == stream.stream_id,
                        models.Node.created_at <= datetime.utcnow()
                    )
                ).distinct().all()
                
                node_payouts = {}
                total_pool = stream.token_balance
                
                if not participating_nodes:
                    logger.info(f"No participating nodes for stream {stream.stream_id}")
                    continue
                
                for (node_id,) in participating_nodes:
                    # Calculate uptime percentage based on successful stats polls
                    total_polls = db.query(models.ProbeResult).filter(
                        and_(
                            models.ProbeResult.stream_id == stream.stream_id,
                            models.ProbeResult.node_id == node_id,
                            models.ProbeResult.probe_type == "stats_poll",
                            models.ProbeResult.probe_timestamp > cutoff_time
                        )
                    ).count()
                    
                    successful_polls = db.query(models.ProbeResult).filter(
                        and_(
                            models.ProbeResult.stream_id == stream.stream_id,
                            models.ProbeResult.node_id == node_id,
                            models.ProbeResult.probe_type == "stats_poll",
                            models.ProbeResult.success == True,
                            models.ProbeResult.probe_timestamp > cutoff_time
                        )
                    ).count()
                    
                    # Check for fraud (failed spot checks)
                    failed_spot_checks = db.query(models.ProbeResult).filter(
                        and_(
                            models.ProbeResult.stream_id == stream.stream_id,
                            models.ProbeResult.node_id == node_id,
                            models.ProbeResult.probe_type == "spot_check",
                            models.ProbeResult.success == False,
                            models.ProbeResult.probe_timestamp > cutoff_time
                        )
                    ).count()
                    
                    # Calculate metrics
                    uptime_percentage = (successful_polls / total_polls) if total_polls > 0 else 0
                    is_flagged = failed_spot_checks > 0
                    
                    # Calculate base payout (equal share of pool based on uptime)
                    base_payout = (total_pool / len(participating_nodes)) * uptime_percentage
                    
                    # Apply fraud penalty (zero payout if flagged)
                    final_payout = 0 if is_flagged else base_payout
                    
                    node_payouts[node_id] = {
                        "base_payout": base_payout,
                        "final_payout": final_payout,
                        "uptime_percentage": uptime_percentage,
                        "total_polls": total_polls,
                        "successful_polls": successful_polls,
                        "failed_spot_checks": failed_spot_checks,
                        "is_flagged": is_flagged,
                        "penalty_reason": "Failed spot check" if is_flagged else None
                    }
                    
                    logger.info(f"Node {node_id}: {uptime_percentage:.1%} uptime, "
                              f"{final_payout:.2f} tokens" + 
                              (f" (FLAGGED)" if is_flagged else ""))
                
                payout_data[stream.stream_id] = {
                    "stream_info": {
                        "stream_id": stream.stream_id,
                        "sponsor": stream.sponsor_address,
                        "total_pool": total_pool,
                        "calculation_period": f"Last {hours_back} hour(s)"
                    },
                    "node_payouts": node_payouts
                }
            
            return payout_data
            
        finally:
            db.close()
    
    def get_node_earnings_summary(self, node_id: str, days_back: int = 7) -> Dict:
        """Get earnings summary for a specific node"""
        db = database.SessionLocal()
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days_back)
            
            # Get all streams this node participated in
            participated_streams = db.query(models.Node.stream_id).filter(
                and_(
                    models.Node.node_id == node_id,
                    models.Node.created_at > cutoff_time
                )
            ).distinct().all()
            
            total_earnings = 0
            stream_details = []
            
            for (stream_id,) in participated_streams:
                # Calculate earnings for this stream (simplified)
                stream = db.query(models.Stream).filter(
                    models.Stream.stream_id == stream_id
                ).first()
                
                if not stream:
                    continue
                
                # Get performance metrics
                total_polls = db.query(models.ProbeResult).filter(
                    and_(
                        models.ProbeResult.stream_id == stream_id,
                        models.ProbeResult.node_id == node_id,
                        models.ProbeResult.probe_type == "stats_poll",
                        models.ProbeResult.probe_timestamp > cutoff_time
                    )
                ).count()
                
                successful_polls = db.query(models.ProbeResult).filter(
                    and_(
                        models.ProbeResult.stream_id == stream_id,
                        models.ProbeResult.node_id == node_id,
                        models.ProbeResult.probe_type == "stats_poll",
                        models.ProbeResult.success == True,
                        models.ProbeResult.probe_timestamp > cutoff_time
                    )
                ).count()
                
                uptime = (successful_polls / total_polls) if total_polls > 0 else 0
                
                # Simplified earnings calculation
                estimated_earnings = (stream.token_balance * 0.1) * uptime  # 10% of pool * uptime
                total_earnings += estimated_earnings
                
                stream_details.append({
                    "stream_id": stream_id,
                    "uptime_percentage": uptime,
                    "estimated_earnings": estimated_earnings,
                    "total_polls": total_polls,
                    "successful_polls": successful_polls
                })
            
            return {
                "node_id": node_id,
                "period": f"Last {days_back} days",
                "total_estimated_earnings": total_earnings,
                "streams_participated": len(participated_streams),
                "stream_details": stream_details
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