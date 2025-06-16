#!/bin/bash
# 🏗️ StreamrP2P Host Setup Script
# Sets up your PC as the coordinator and ingest server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏗️ StreamrP2P Host Setup${NC}"
echo "Setting up your PC as the coordinator and ingest server..."
echo

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker first and try again"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo "Please install Docker Compose first and try again"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose found${NC}"

# Check if networking setup is needed
echo -e "${BLUE}🌐 Checking networking configuration...${NC}"
if [[ -f "scripts/test-networking.sh" ]]; then
    echo "Running networking test..."
    if ! bash scripts/test-networking.sh --coordinator-only >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Networking issues detected${NC}"
        echo ""
        echo -e "${BLUE}🔧 Platform-specific networking setup available:${NC}"
        
        # Detect platform and suggest appropriate setup
        if [[ "$OSTYPE" == "linux-gnu"* ]] && grep -qi microsoft /proc/version 2>/dev/null; then
            echo "  Windows WSL detected"
            echo "  Run: scripts/setup-host-networking-wsl.ps1 (as Administrator in PowerShell)"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            echo "  macOS detected"  
            echo "  Run: scripts/setup-host-networking-macos.sh"
        else
            echo "  Manual router configuration may be needed"
        fi
        
        echo ""
        echo -e "${YELLOW}Continue anyway? (y/n)${NC}"
        read -r CONTINUE
        if [[ "$CONTINUE" != "y" && "$CONTINUE" != "Y" ]]; then
            echo "Setup cancelled. Run networking setup first."
            exit 1
        fi
    fi
fi

# Get public IP
echo -e "${BLUE}🔍 Discovering your public IP...${NC}"
PUBLIC_IP=$(curl -s https://api.ipify.org)
if [ -z "$PUBLIC_IP" ]; then
    echo -e "${YELLOW}⚠️  Could not determine public IP, using localhost${NC}"
    PUBLIC_IP="localhost"
fi
echo -e "${GREEN}✅ Public IP: $PUBLIC_IP${NC}"

# Start coordinator
echo -e "${BLUE}🚀 Starting coordinator server...${NC}"
cd coordinator
docker-compose up -d

# Wait for coordinator to start
echo -e "${BLUE}⏳ Waiting for coordinator to start...${NC}"
sleep 5

# Check if coordinator is running
if curl -s http://localhost:8000/health >/dev/null; then
    echo -e "${GREEN}✅ Coordinator is running${NC}"
else
    echo -e "${RED}❌ Coordinator failed to start${NC}"
    echo "Check logs with: docker-compose logs"
    exit 1
fi

cd ..

# Setup ingest server
echo -e "${BLUE}📡 Setting up ingest server...${NC}"
mkdir -p ingest-server
cd ingest-server

# Create ingest config
cat > ingest_config.yaml << 'EOF'
servers:
  - endpoints:
      - addresses: ["0.0.0.0:1935"]
        type: "host"
        direction: "input"
        applicationName: "live"
        video: true
        audio: true
      - addresses: ["0.0.0.0:1936"]
        type: "host" 
        direction: "output"
        applicationName: "live"
        video: true
        audio: true
statusPage:
  address: "0.0.0.0:8081"
log:
  level: 2
EOF

# Stop any existing ingest server
docker stop streamr-ingest >/dev/null 2>&1 || true
docker rm streamr-ingest >/dev/null 2>&1 || true

# Start ingest server
echo -e "${BLUE}🚀 Starting ingest server...${NC}"
docker run -d \
  --name streamr-ingest \
  -p 1935:1935 \
  -p 1936:1936 \
  -p 8081:8081 \
  -v $(pwd)/ingest_config.yaml:/config.yaml \
  ubuntu:22.04 bash -c "
    apt-get update >/dev/null 2>&1 && 
    apt-get install -y git build-essential cmake libyaml-dev >/dev/null 2>&1 && 
    git clone https://github.com/elnormous/rtmp_relay.git >/dev/null 2>&1 && 
    cd rtmp_relay && 
    git submodule update --init >/dev/null 2>&1 && 
    make >/dev/null 2>&1 && 
    ./bin/rtmp_relay --config /config.yaml
  "

# Wait for ingest to start
echo -e "${BLUE}⏳ Waiting for ingest server to start...${NC}"
sleep 10

# Check if ingest is running
if curl -s http://localhost:8081/stats.json >/dev/null; then
    echo -e "${GREEN}✅ Ingest server is running${NC}"
else
    echo -e "${YELLOW}⚠️  Ingest server may still be starting...${NC}"
fi

cd ..

# Register test stream
echo -e "${BLUE}📝 Registering test stream...${NC}"
curl -X POST "http://localhost:8000/streams" \
  -H "Content-Type: application/json" \
  -d "{
    \"stream_id\": \"test_stream_001\",
    \"sponsor_address\": \"0x1234567890abcdef\",
    \"token_balance\": 1000.0,
    \"rtmp_url\": \"rtmp://$PUBLIC_IP:1936/live/test_stream_001\"
  }" >/dev/null 2>&1

echo -e "${GREEN}✅ Test stream registered${NC}"

# Show status
echo
echo -e "${GREEN}🎉 Host setup complete!${NC}"
echo
echo -e "${YELLOW}📊 Your StreamrP2P Host Information:${NC}"
echo "  Public IP: $PUBLIC_IP"
echo "  Coordinator: http://localhost:8000"
echo "  Dashboard: http://localhost:8000/dashboard"
echo "  Ingest Server: rtmp://localhost:1935/live"
echo "  Ingest Stats: http://localhost:8081/stats.json"
echo
echo -e "${YELLOW}🎥 OBS Setup:${NC}"
echo "  1. Open OBS Studio"
echo "  2. Go to Settings → Stream"
echo "  3. Service: Custom"
echo "  4. Server: rtmp://localhost:1935/live"
echo "  5. Stream Key: test_stream_001"
echo "  6. Click OK and Start Streaming"
echo
echo -e "${YELLOW}👥 For Your Friends:${NC}"
echo "  Send them this command to join:"
  echo "  ${BLUE}curl -sSL https://raw.githubusercontent.com/iddv/streamr/main/setup-node.sh | bash -s http://$PUBLIC_IP:8000 test_stream_001${NC}"
echo
echo "  Or share this file: ${BLUE}FRIEND_SETUP.md${NC}"
echo
echo -e "${YELLOW}🔍 Monitoring Commands:${NC}"
echo "  Dashboard:     curl http://localhost:8000/dashboard | jq"
echo "  Active nodes:  curl http://localhost:8000/streams | jq"
echo "  Leaderboard:   curl http://localhost:8000/leaderboard | jq"
echo "  Payouts:       curl http://localhost:8000/payouts | jq"
echo
echo -e "${YELLOW}📝 View Logs:${NC}"
echo "  Coordinator:   docker-compose -f coordinator/docker-compose.yml logs -f coordinator"
echo "  Worker:        docker-compose -f coordinator/docker-compose.yml logs -f worker"
echo "  Ingest:        docker logs streamr-ingest -f"
echo
echo -e "${YELLOW}🧪 Test Your Setup:${NC}"
echo "  Full test:     scripts/test-networking.sh"
echo "  Quick test:    curl http://localhost:8000/health"
echo
echo -e "${GREEN}🚀 Ready for testing! Start OBS and invite your friends!${NC}" 