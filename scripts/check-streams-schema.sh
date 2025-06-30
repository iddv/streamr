#!/bin/bash

# 🔍 Check Streams Table Schema
# This script checks what columns exist in the streams table

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🔍 Checking streams table schema...${NC}"

# Get database configuration from Secrets Manager
echo "📡 Fetching database credentials..."
DB_SECRET=$(aws secretsmanager get-secret-value --region eu-west-1 --secret-id "streamr-p2p-beta-db-credentials" --query SecretString --output text)
DB_ENDPOINT=$(echo $DB_SECRET | jq -r '.host')
DB_USERNAME=$(echo $DB_SECRET | jq -r '.username')
DB_PASSWORD=$(echo $DB_SECRET | jq -r '.password')
DB_NAME=$(echo $DB_SECRET | jq -r '.dbname')

echo "🏗️ Using database: $DB_ENDPOINT"

# Create SQL query to check table schema
SQL_QUERY="
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'streams' 
ORDER BY ordinal_position;
"

echo -e "${YELLOW}📋 Streams table columns:${NC}"

# Execute query using bastion approach
CONTAINER_NAME="temp-postgres-check-$(date +%s)"

docker run --rm --name "$CONTAINER_NAME" \
  -e PGPASSWORD="$DB_PASSWORD" \
  postgres:15 \
  psql -h "$DB_ENDPOINT" -U "$DB_USERNAME" -d "$DB_NAME" \
  -c "$SQL_QUERY"

echo -e "${GREEN}✅ Schema check complete${NC}" 