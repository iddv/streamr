#!/bin/bash

# 🧪 Test Economic Validation Migration Locally
# Tests the migration script before applying to production

set -e

echo "🧪 Testing Economic Validation Migration Locally"
echo "================================================="

# Local database connection (adjust if needed)
DATABASE_URL="${DATABASE_URL:-postgresql://streamr:streamr@localhost:5432/streamr_poc}"

# Check if migration file exists
MIGRATION_FILE="coordinator/economic_validation_migration.sql"
if [ ! -f "$MIGRATION_FILE" ]; then
    echo "❌ Migration file not found: $MIGRATION_FILE"
    echo "   Please run this script from the project root directory."
    exit 1
fi

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "❌ Error: psql command not found"
    echo "   Please install PostgreSQL client tools"
    exit 1
fi

# Test database connection
echo "🔗 Testing local database connection..."
if ! psql "$DATABASE_URL" -c "SELECT version();" > /dev/null 2>&1; then
    echo "❌ Error: Cannot connect to local database"
    echo "   Please ensure local coordinator is running or update DATABASE_URL"
    exit 1
fi

echo "✅ Local database connection successful"

# Show current table structure before migration
echo ""
echo "📊 Current tables before migration:"
psql "$DATABASE_URL" -c "\dt"

# Run the migration
echo ""
echo "🚀 Running economic validation migration..."
psql "$DATABASE_URL" -f "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Migration completed successfully!"
else
    echo "❌ Migration failed!"
    exit 1
fi

# Show results
echo ""
echo "📊 Tables after migration:"
psql "$DATABASE_URL" -c "\dt"

echo ""
echo "🎉 Local migration test completed successfully!"
echo "   Ready to run on production using: ./scripts/run-migration-fixed.sh beta" 