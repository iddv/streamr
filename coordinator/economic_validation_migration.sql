-- 💰 Economic Validation Database Migration
-- Adds economic tracking capabilities to existing database
-- Uses same safe pattern as database_migration_lifecycle.sql

-- 1. Create bandwidth_ledger table for immutable audit trail
CREATE TABLE IF NOT EXISTS bandwidth_ledger (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL, -- References streams.stream_id
    reporting_node_id VARCHAR(255) NOT NULL,
    bytes_transferred BIGINT NOT NULL CHECK (bytes_transferred >= 0),
    report_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    start_interval TIMESTAMPTZ NOT NULL,
    end_interval TIMESTAMPTZ NOT NULL,
    source_bitrate_kbps INTEGER, -- Known stream bitrate for verification
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    trust_score DECIMAL(3,2), -- 0.00-1.00 trust rating
    verification_notes TEXT
);

-- 2. Create user_accounts table for aggregated financials
CREATE TABLE IF NOT EXISTS user_accounts (
    user_id VARCHAR(255) PRIMARY KEY, -- node_id from nodes table
    balance_usd DECIMAL(10, 4) NOT NULL DEFAULT 0.00,
    total_gb_relayed DECIMAL(12, 4) NOT NULL DEFAULT 0.00,
    earnings_last_30d DECIMAL(10, 4) NOT NULL DEFAULT 0.00,
    trust_score DECIMAL(3,2) NOT NULL DEFAULT 1.00,
    flags TEXT[], -- ['suspicious_reporting', 'high_variance']
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Add economic tracking columns to existing streams table (safe ADD COLUMN)
ALTER TABLE streams ADD COLUMN IF NOT EXISTS total_gb_delivered DECIMAL(12, 4) DEFAULT 0.00;
ALTER TABLE streams ADD COLUMN IF NOT EXISTS total_cost_usd DECIMAL(10, 4) DEFAULT 0.00;
ALTER TABLE streams ADD COLUMN IF NOT EXISTS platform_fee_usd DECIMAL(10, 4) DEFAULT 0.00;
ALTER TABLE streams ADD COLUMN IF NOT EXISTS creator_payout_usd DECIMAL(10, 4) DEFAULT 0.00;

-- 4. Create performance indexes
CREATE INDEX IF NOT EXISTS idx_ledger_session_node ON bandwidth_ledger(session_id, reporting_node_id);
CREATE INDEX IF NOT EXISTS idx_ledger_timestamp ON bandwidth_ledger(report_timestamp);
CREATE INDEX IF NOT EXISTS idx_ledger_verification ON bandwidth_ledger(is_verified, report_timestamp);

-- 5. Add foreign key references (after tables exist)
-- Note: Using session_id as VARCHAR to match streams.stream_id type
-- Foreign key validation happens at query time, not schema level for flexibility

-- 6. Add comments for documentation
COMMENT ON TABLE bandwidth_ledger IS 'Immutable audit trail of bandwidth usage reports from nodes';
COMMENT ON TABLE user_accounts IS 'Aggregated financial data and trust scores for node operators';
COMMENT ON COLUMN streams.total_gb_delivered IS 'Total gigabytes delivered via P2P for this stream';
COMMENT ON COLUMN streams.total_cost_usd IS 'Total platform costs for this stream session';
COMMENT ON COLUMN streams.platform_fee_usd IS 'Platform commission earned from this stream';
COMMENT ON COLUMN streams.creator_payout_usd IS 'Amount paid to stream creator';

-- 7. Show current table structure after migration
\d+ bandwidth_ledger;
\d+ user_accounts;
\d+ streams;

-- 8. Verify migration success
SELECT 'Economic validation migration completed successfully!' as migration_status; 