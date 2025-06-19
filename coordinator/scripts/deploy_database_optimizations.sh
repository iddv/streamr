#!/bin/bash

# 🗄️ StreamrP2P Database Index Management
# Optional utility to apply performance indexes to existing database
# Note: These are planned for Phase 3 scaling, not required for Phase 2D

set -e  # Exit on any error

echo "🗄️ StreamrP2P Database Index Management Utility"
echo "==============================================="
echo "⚠️  Note: Indexes are optional for Phase 2D friends testing"
echo "    Required for Phase 3 scaling (100+ users)"
echo ""

# Configuration
DB_HOST="${DB_HOST:-streamr-beta-db.cveqjzc1v2ze.eu-west-1.rds.amazonaws.com}"
DB_NAME="${DB_NAME:-streamr}"
DB_USER="${DB_USER:-streamr}"

# Check if we're in the right directory
if [ ! -f "../database_performance_indexes.sql" ]; then
    echo "❌ Error: database_performance_indexes.sql not found"
    echo "   Please run this script from coordinator/scripts/ directory"
    exit 1
fi

echo "📋 Pre-deployment checks..."

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "❌ Error: psql command not found"
    echo "   Please install PostgreSQL client tools"
    exit 1
fi

# Test database connection
echo "🔗 Testing database connection..."
if ! PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT version();" > /dev/null 2>&1; then
    echo "❌ Error: Cannot connect to database"
    echo "   Please ensure DB_PASSWORD environment variable is set"
    echo "   and database is accessible"
    exit 1
fi

echo "✅ Database connection successful"

# Show current table sizes before optimization
echo ""
echo "📊 Current database stats (before optimization):"
PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" << 'EOF'
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_total_relation_size(schemaname||'.'||tablename) as bytes
FROM pg_tables 
WHERE schemaname NOT IN ('information_schema','pg_catalog')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
EOF

# Apply performance indexes
echo ""
echo "🔧 Applying performance indexes..."
echo "   This may take a few minutes for large tables..."

PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" -f "../database_performance_indexes.sql"

if [ $? -eq 0 ]; then
    echo "✅ Performance indexes applied successfully"
else
    echo "❌ Error applying performance indexes"
    exit 1
fi

# Verify indexes were created
echo ""
echo "📋 Verifying indexes were created:"
PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" << 'EOF'
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename IN ('probe_results', 'streams', 'nodes')
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
EOF

# Show updated database stats
echo ""
echo "📊 Database stats after optimization:"
PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" << 'EOF'
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname NOT IN ('information_schema','pg_catalog')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
EOF

echo ""
echo "🎉 Database optimization deployment complete!"
echo ""
echo "📈 Expected performance improvements:"
echo "   - Payout calculations: 99%+ faster (from 8-12s to <1s)"
echo "   - Database CPU usage: Reduced from 80-95% to <20%"
echo "   - Concurrent user capacity: Ready for 100+ friend nodes"
echo ""
echo "🔍 To monitor performance:"
echo "   1. Check application logs for query timing improvements"
echo "   2. Monitor RDS CloudWatch metrics for CPU reduction"
echo "   3. Test /payouts API endpoint response times"
echo ""
echo "📚 For more details, see: docs/analysis/DATABASE_SCALING_STRATEGY.md" 