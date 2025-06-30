#!/bin/bash

# 🔧 Fix Missing Streams Table Columns
# Add the economic validation columns that failed to be added in the previous migration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🔧 Adding missing economic columns to streams table...${NC}"

# Get database configuration from Secrets Manager
echo "📡 Fetching database credentials..."
DB_SECRET=$(aws secretsmanager get-secret-value --region eu-west-1 --secret-id "streamr-p2p-beta-db-credentials" --query SecretString --output text)
DB_ENDPOINT=$(echo $DB_SECRET | jq -r '.host')
DB_USERNAME=$(echo $DB_SECRET | jq -r '.username')
DB_PASSWORD=$(echo $DB_SECRET | jq -r '.password')
DB_NAME=$(echo $DB_SECRET | jq -r '.dbname')

echo "🏗️ Using database: $DB_ENDPOINT"

# SQL to add the missing columns
SQL_SCRIPT="
-- Add economic tracking columns to streams table
ALTER TABLE streams 
ADD COLUMN IF NOT EXISTS total_gb_delivered DECIMAL(12, 4) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS total_cost_usd DECIMAL(10, 4) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS platform_fee_usd DECIMAL(10, 4) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS creator_payout_usd DECIMAL(10, 4) DEFAULT 0.00;

-- Verify the columns were added
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'streams' 
AND column_name IN ('total_gb_delivered', 'total_cost_usd', 'platform_fee_usd', 'creator_payout_usd')
ORDER BY column_name;
"

echo -e "${YELLOW}📝 Adding missing columns...${NC}"

# Execute using Docker container in VPC
CONTAINER_NAME="fix-streams-columns-$(date +%s)"

docker run --rm --name "$CONTAINER_NAME" \
  -e PGPASSWORD="$DB_PASSWORD" \
  postgres:15 \
  psql -h "$DB_ENDPOINT" -U "$DB_USERNAME" -d "$DB_NAME" \
  -c "$SQL_SCRIPT"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Successfully added missing economic columns to streams table${NC}"
    echo -e "${GREEN}🚀 The application should now work properly${NC}"
else
    echo -e "${RED}❌ Failed to add columns${NC}"
    exit 1
fi 