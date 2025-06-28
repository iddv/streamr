-- 🔄 Stream Lifecycle Database Migration
-- Adds enterprise-grade lifecycle management to existing streams table

-- 1. Add lifecycle timestamp fields to existing streams table
ALTER TABLE streams ADD COLUMN IF NOT EXISTS live_started_at TIMESTAMP;
ALTER TABLE streams ADD COLUMN IF NOT EXISTS offline_at TIMESTAMP;
ALTER TABLE streams ADD COLUMN IF NOT EXISTS testing_started_at TIMESTAMP;

-- 2. Update status field to use new lifecycle values  
-- Current status values: "active", "paused", "completed"
-- New status values: "READY", "TESTING", "LIVE", "OFFLINE", "STALE", "ARCHIVED"

-- Map existing status values to new lifecycle system
UPDATE streams SET status = 'OFFLINE' WHERE status = 'completed';
UPDATE streams SET status = 'OFFLINE' WHERE status = 'paused';
UPDATE streams SET status = 'READY' WHERE status = 'active';

-- 3. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_streams_status_discovery ON streams(status, live_started_at);
CREATE INDEX IF NOT EXISTS idx_streams_lifecycle ON streams(status, created_at);

-- 4. Clean up stale data (streams older than 1 day without proper lifecycle)
UPDATE streams 
SET status = 'OFFLINE', offline_at = NOW() 
WHERE stream_id = 'obs-test' AND created_at < NOW() - INTERVAL '1 day';

-- 5. Add comments for documentation
COMMENT ON COLUMN streams.status IS 'Stream lifecycle status: READY, TESTING, LIVE, OFFLINE, STALE, ARCHIVED';
COMMENT ON COLUMN streams.live_started_at IS 'Timestamp when stream transitioned to LIVE status';
COMMENT ON COLUMN streams.offline_at IS 'Timestamp when stream went OFFLINE';
COMMENT ON COLUMN streams.testing_started_at IS 'Timestamp when stream started TESTING phase';

-- 6. Show current stream statuses after migration
SELECT stream_id, status, created_at, live_started_at, offline_at 
FROM streams 
ORDER BY created_at DESC; 