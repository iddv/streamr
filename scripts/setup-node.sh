#!/bin/bash
# 🚀 StreamrP2P Node Setup Script
# One-command setup for joining the test network

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_COORDINATOR_URL="http://localhost:8000"
DEFAULT_STREAM_ID="test_stream_001"
DEFAULT_NODE_ID="node_$(whoami)_$(date +%s)"

echo -e "${BLUE}🚀 StreamrP2P Node Setup${NC}"
echo "Setting up your node to join the restreaming network..."
echo

# Parse command line arguments
COORDINATOR_URL="${1:-$DEFAULT_COORDINATOR_URL}"
STREAM_ID="${2:-$DEFAULT_STREAM_ID}"
NODE_ID="${3:-$DEFAULT_NODE_ID}"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Coordinator: $COORDINATOR_URL"
echo "  Stream ID: $STREAM_ID"
echo "  Node ID: $NODE_ID"
echo

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker first:"
    echo "  - Ubuntu/Debian: sudo apt update && sudo apt install docker.io"
    echo "  - macOS: Download Docker Desktop from docker.com"
    echo "  - Windows: Download Docker Desktop from docker.com"
    exit 1
fi

echo -e "${GREEN}✅ Docker found${NC}"

# Check if ports are available
check_port() {
    local port=$1
    if netstat -ln 2>/dev/null | grep -q ":$port "; then
        echo -e "${YELLOW}⚠️  Port $port is in use, trying alternative...${NC}"
        return 1
    fi
    return 0
}

# Find available ports
RTMP_PORT=1935
STATS_PORT=8080

if ! check_port $RTMP_PORT; then
    RTMP_PORT=1937
fi

if ! check_port $STATS_PORT; then
    STATS_PORT=8082
fi

echo -e "${GREEN}✅ Using ports: RTMP=$RTMP_PORT, Stats=$STATS_PORT${NC}"

# Stop any existing node
if docker ps -q -f name=streamr-node | grep -q .; then
    echo -e "${YELLOW}🔄 Stopping existing node...${NC}"
    docker stop streamr-node >/dev/null 2>&1 || true
    docker rm streamr-node >/dev/null 2>&1 || true
fi

# Test coordinator connectivity
echo -e "${BLUE}🔍 Testing coordinator connectivity...${NC}"
if curl -s --connect-timeout 5 "$COORDINATOR_URL/health" >/dev/null; then
    echo -e "${GREEN}✅ Coordinator is reachable${NC}"
else
    echo -e "${RED}❌ Cannot reach coordinator at $COORDINATOR_URL${NC}"
    echo "Please check:"
    echo "  1. The coordinator URL is correct"
    echo "  2. The coordinator is running"
    echo "  3. Your firewall allows outbound connections"
    exit 1
fi

# Check if stream exists
echo -e "${BLUE}🔍 Checking if stream exists...${NC}"
if curl -s "$COORDINATOR_URL/streams" | grep -q "\"stream_id\":\"$STREAM_ID\""; then
    echo -e "${GREEN}✅ Stream '$STREAM_ID' found${NC}"
else
    echo -e "${YELLOW}⚠️  Stream '$STREAM_ID' not found in coordinator${NC}"
    echo "Available streams:"
    curl -s "$COORDINATOR_URL/streams" | grep -o '"stream_id":"[^"]*"' | sed 's/"stream_id":"//g' | sed 's/"//g' | sed 's/^/  - /'
    echo
    echo "Continuing anyway (stream might be added later)..."
fi

# Build the node client if we're in the repo
if [ -f "node-client/Dockerfile" ]; then
    echo -e "${BLUE}🔨 Building node client from source...${NC}"
    cd node-client
    docker build -t streamr-node-local . >/dev/null 2>&1
    IMAGE="streamr-node-local"
    cd ..
else
    echo -e "${BLUE}📦 Using pre-built image...${NC}"
    IMAGE="streamr/node-client:latest"
    
    # Try to pull the image
    if ! docker pull $IMAGE >/dev/null 2>&1; then
        echo -e "${RED}❌ Cannot pull image $IMAGE${NC}"
        echo "Please ensure you have internet connectivity or build from source"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Image ready${NC}"

# Start the node
echo -e "${BLUE}🚀 Starting StreamrP2P node...${NC}"

docker run -d \
    --name streamr-node \
    -p $RTMP_PORT:1935 \
    -p $STATS_PORT:8080 \
    -e STREAM_ID="$STREAM_ID" \
    -e COORDINATOR_URL="$COORDINATOR_URL" \
    -e NODE_ID="$NODE_ID" \
    -e RTMP_PORT=1935 \
    -e STATS_PORT=8080 \
    --restart unless-stopped \
    $IMAGE

# Wait a moment for startup
echo -e "${BLUE}⏳ Waiting for node to start...${NC}"
sleep 3

# Check if container is running
if docker ps -q -f name=streamr-node | grep -q .; then
    echo -e "${GREEN}✅ Node started successfully!${NC}"
    echo
    echo -e "${YELLOW}📊 Node Information:${NC}"
    echo "  Node ID: $NODE_ID"
    echo "  RTMP Port: $RTMP_PORT"
    echo "  Stats Port: $STATS_PORT"
    echo "  Stats URL: http://localhost:$STATS_PORT/stats.json"
    echo
    echo -e "${YELLOW}📋 Useful Commands:${NC}"
    echo "  View logs:     docker logs streamr-node -f"
    echo "  Stop node:     docker stop streamr-node"
    echo "  Restart node:  docker restart streamr-node"
    echo "  Remove node:   docker stop streamr-node && docker rm streamr-node"
    echo
    echo -e "${YELLOW}🔍 Monitoring:${NC}"
    echo "  Local stats:   curl http://localhost:$STATS_PORT/stats.json"
    echo "  Dashboard:     $COORDINATOR_URL/dashboard"
    echo "  Earnings:      $COORDINATOR_URL/nodes/$NODE_ID/earnings"
    echo "  Leaderboard:   $COORDINATOR_URL/leaderboard"
    echo
    echo -e "${GREEN}🎉 Your node is now part of the StreamrP2P network!${NC}"
    echo -e "${BLUE}💰 You'll start earning rewards based on your uptime and performance.${NC}"
    
    # Show initial logs
    echo
    echo -e "${YELLOW}📝 Initial logs (press Ctrl+C to exit):${NC}"
    docker logs streamr-node -f
    
else
    echo -e "${RED}❌ Node failed to start${NC}"
    echo "Checking logs..."
    docker logs streamr-node
    exit 1
fi 