#!/bin/bash

# 🚀 StreamrP2P Friend Node Setup
# Usage: ./setup-friend-node.sh YOUR_API_KEY

API_KEY="$1"
COORDINATOR_URL="http://86.87.233.125:8000"
STREAM_ID="test_stream_001"

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 StreamrP2P Friend Node Setup${NC}"
echo "=================================="

# Validate input
if [ -z "$API_KEY" ]; then
    echo -e "${RED}❌ Error: API key required${NC}"
    echo "Usage: ./setup-friend-node.sh YOUR_API_KEY"
    echo ""
    echo "Get your API key from your friend who's hosting the stream!"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found${NC}"
    echo "Please install Docker first:"
    echo "  Linux: sudo apt install docker.io"
    echo "  macOS: brew install docker"
    echo "  Windows: Download Docker Desktop"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker not running${NC}"
    echo "Please start Docker first"
    exit 1
fi

# Generate unique node ID
NODE_ID="friend_$(whoami)_$(date +%s)"

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  Coordinator: $COORDINATOR_URL"
echo "  Stream ID: $STREAM_ID"
echo "  Node ID: $NODE_ID"
echo "  API Key: ${API_KEY:0:12}..."
echo ""

# Test connection to coordinator
echo -e "${BLUE}🔍 Testing connection to coordinator...${NC}"
if curl -s --max-time 10 "$COORDINATOR_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ Connection successful${NC}"
else
    echo -e "${RED}❌ Cannot reach coordinator${NC}"
    echo "Please check:"
    echo "  1. Your internet connection"
    echo "  2. The coordinator is running"
    echo "  3. Firewall settings"
    exit 1
fi

# Stop any existing node
echo -e "${BLUE}🧹 Cleaning up existing node...${NC}"
docker stop streamr-friend-node 2>/dev/null || true
docker rm streamr-friend-node 2>/dev/null || true

# Pull latest image
echo -e "${BLUE}📦 Pulling latest node client...${NC}"
docker pull streamr/node-client:latest || {
    echo -e "${RED}❌ Failed to pull Docker image${NC}"
    echo "Using local image if available..."
}

# Start the node
echo -e "${BLUE}🚀 Starting StreamrP2P node...${NC}"
docker run -d \
  --name streamr-friend-node \
  --restart unless-stopped \
  -p 8080:8080 \
  -e COORDINATOR_URL="$COORDINATOR_URL" \
  -e STREAM_ID="$STREAM_ID" \
  -e API_KEY="$API_KEY" \
  -e NODE_ID="$NODE_ID" \
  streamr/node-client:latest

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Node started successfully!${NC}"
    echo ""
    echo -e "${YELLOW}📊 Monitor your node:${NC}"
    echo "  View logs: docker logs streamr-friend-node -f"
    echo "  Check status: curl http://localhost:8080/stats"
    echo "  Stop node: docker stop streamr-friend-node"
    echo ""
    echo -e "${GREEN}🎉 You're now helping support the stream!${NC}"
    echo "Your friend will see you in their dashboard and you'll earn rewards!"
else
    echo -e "${RED}❌ Failed to start node${NC}"
    echo "Check Docker logs: docker logs streamr-friend-node"
    exit 1
fi 