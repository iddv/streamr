-- 🚀 StreamrP2P Database Performance Indexes
-- These indexes support the optimized payout calculation queries
-- Run this after fixing payout_service.py performance issues

-- Primary index for probe_results filtering (most critical)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_probe_results_performance 
ON probe_results (stream_id, node_id, probe_type, probe_timestamp, success);

-- Composite index for time-based queries (supports cutoff_time filtering)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_probe_results_time_stream
ON probe_results (probe_timestamp DESC, stream_id);

-- Index for node-specific earnings queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_probe_results_node_time
ON probe_results (node_id, probe_timestamp DESC, probe_type);

-- Index for stream status filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_streams_status
ON streams (status) WHERE status = 'active';

-- Index for node-stream relationships
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_nodes_stream_created
ON nodes (stream_id, created_at DESC);

-- Partial index for successful stats polls (most common query pattern)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_probe_results_successful_stats
ON probe_results (stream_id, node_id, probe_timestamp DESC)
WHERE probe_type = 'stats_poll' AND success = true;

-- Partial index for failed spot checks (fraud detection)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_probe_results_failed_spots
ON probe_results (stream_id, node_id, probe_timestamp DESC)
WHERE probe_type = 'spot_check' AND success = false;

-- Analyze tables to update statistics
ANALYZE probe_results;
ANALYZE streams;
ANALYZE nodes;

-- Query to check index usage (run after some load testing)
/*
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes 
WHERE tablename IN ('probe_results', 'streams', 'nodes')
ORDER BY idx_scan DESC;
*/ 