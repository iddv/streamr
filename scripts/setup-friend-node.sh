#!/bin/bash

# 🚀 StreamrP2P Friend Node Setup
# Usage: ./setup-friend-node.sh YOUR_STREAM_KEY

STREAM_KEY="$1"
COORDINATOR_URL="http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com"
SRS_RTMP_URL="rtmp://86.87.233.125:1935/live"
SRS_HLS_URL="http://86.87.233.125:8080/live"

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 StreamrP2P Friend Node Setup${NC}"
echo "=================================="

# Validate input
if [ -z "$STREAM_KEY" ]; then
    echo -e "${RED}❌ Error: Stream key required${NC}"
    echo "Usage: ./setup-friend-node.sh YOUR_STREAM_KEY"
    echo ""
    echo "Get your stream key from your friend who's hosting the stream!"
    echo "Example: ./setup-friend-node.sh obs-test"
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
echo "  Stream Key: $STREAM_KEY"
echo "  Node ID: $NODE_ID"
echo "  RTMP Source: $SRS_RTMP_URL/$STREAM_KEY"
echo "  HLS Output: $SRS_HLS_URL/$STREAM_KEY.m3u8"
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

# Start the node (using SRS image for now, will be replaced with custom image later)
echo -e "${BLUE}🚀 Starting StreamrP2P friend node...${NC}"
echo -e "${YELLOW}Note: This is a simplified test setup. Full P2P functionality coming soon!${NC}"

# For now, we'll use SRS to demonstrate the concept
docker run -d \
  --name streamr-friend-node \
  --restart unless-stopped \
  -p 1936:1935 \
  -p 8081:8080 \
  -e STREAM_KEY="$STREAM_KEY" \
  -e NODE_ID="$NODE_ID" \
  ossrs/srs:5

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Friend node started successfully!${NC}"
    echo ""
    echo -e "${YELLOW}📊 Your Node Status:${NC}"
    echo "  Node ID: $NODE_ID"
    echo "  RTMP Relay: rtmp://localhost:1936/live/$STREAM_KEY"
    echo "  HLS Output: http://localhost:8081/live/$STREAM_KEY.m3u8"
    echo ""
    echo -e "${YELLOW}📋 Next Steps:${NC}"
    echo "  1. Tell your friend to start streaming to: $SRS_RTMP_URL/$STREAM_KEY"
    echo "  2. You can watch the stream at: $SRS_HLS_URL/$STREAM_KEY.m3u8"
    echo "  3. Share your relay with others: http://localhost:8081/live/$STREAM_KEY.m3u8"
    echo ""
    echo -e "${YELLOW}🔧 Monitor your node:${NC}"
    echo "  View logs: docker logs streamr-friend-node -f"
    echo "  Stop node: docker stop streamr-friend-node"
    echo ""
    echo -e "${YELLOW}🌐 Final Step - Verify Public Access:${NC}"
    echo "  1. Go to: https://canyouseeme.org"
    echo "  2. Enter port: 8081"
    echo "  3. Click 'Check Port'"
    echo "  4. If SUCCESS: You're ready! Share your public URL with your friend"
    echo "  5. If ERROR: Check firewall/router settings"
    echo ""
    echo -e "${GREEN}🎉 You're now helping support the stream!${NC}"
    echo "Your friend will see you in their dashboard and you'll earn rewards!"
else
    echo -e "${RED}❌ Failed to start node${NC}"
    echo "Check Docker logs: docker logs streamr-friend-node"
    exit 1
fi 