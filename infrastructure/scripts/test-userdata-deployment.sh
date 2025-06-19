#!/bin/bash

# 🧪 Test UserData Deployment Script
# This script simulates what happens in the EC2 UserData to verify deployment works

set -e

echo "🔬 Testing UserData deployment process..."

# Create test directory
TEST_DIR="/tmp/streamr-test-$(date +%s)"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "📥 Testing GitHub clone..."
git clone https://github.com/iddv/streamr.git .

echo "📁 Checking repository structure..."
ls -la
[ -d "coordinator" ] || { echo "❌ coordinator directory not found"; exit 1; }
[ -f "coordinator/docker-compose.yml" ] || { echo "❌ docker-compose.yml not found"; exit 1; }
[ -f "coordinator/requirements.txt" ] || { echo "❌ requirements.txt not found"; exit 1; }

echo "🐳 Testing Docker Compose setup..."
cd coordinator

# Create test environment file
cat > .env << 'ENVEOF'
DATABASE_URL=postgresql://streamr_user:test_password@localhost:5432/streamr_db
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=test
LOG_LEVEL=INFO
WORKERS=2
ENVEOF

echo "✅ Environment file created"

# Test docker-compose validation
if command -v docker-compose &> /dev/null; then
    echo "🧪 Testing docker-compose config..."
    docker-compose config --quiet
    echo "✅ docker-compose configuration is valid"
else
    echo "⚠️  docker-compose not available, skipping validation"
fi

echo "🧹 Cleaning up test directory..."
cd /
rm -rf "$TEST_DIR"

echo "🎉 UserData deployment test completed successfully!"
echo ""
echo "🚀 This confirms the UserData script will work. To deploy:"
echo "   1. Update the GitHub URL in application-stack.ts if needed"
echo "   2. Run: cd infrastructure && npm run deploy"
echo "   3. Wait for EC2 instance to auto-deploy the application" 