#!/bin/bash

# StreamrP2P Application Deployment Script
# Deploys the coordinator application to the live AWS infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="streamr-p2p-beta-ireland-application"
REGION="eu-west-1"
KEY_NAME="streamr-beta-key"
EC2_USER="ec2-user"

echo -e "${BLUE}🚀 StreamrP2P Application Deployment${NC}"
echo "=================================="

# Get EC2 instance IP from CloudFormation
echo -e "${YELLOW}📡 Getting EC2 instance details...${NC}"
INSTANCE_IP=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`InstancePublicIP`].OutputValue' \
    --output text)

if [ -z "$INSTANCE_IP" ] || [ "$INSTANCE_IP" = "None" ]; then
    echo -e "${RED}❌ Failed to get EC2 instance IP from CloudFormation${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Instance IP: $INSTANCE_IP${NC}"

# Get database and cache endpoints
echo -e "${YELLOW}🗄️ Getting database and cache endpoints...${NC}"
DB_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name streamr-p2p-beta-ireland-foundation \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' \
    --output text)

CACHE_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name streamr-p2p-beta-ireland-foundation \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`CacheEndpoint`].OutputValue' \
    --output text)

echo -e "${GREEN}✅ Database: $DB_ENDPOINT${NC}"
echo -e "${GREEN}✅ Cache: $CACHE_ENDPOINT${NC}"

# Check SSH connectivity
echo -e "${YELLOW}🔐 Testing SSH connectivity...${NC}"
if ! ssh -i ~/.ssh/$KEY_NAME.pem -o ConnectTimeout=10 -o StrictHostKeyChecking=no $EC2_USER@$INSTANCE_IP "echo 'SSH connection successful'"; then
    echo -e "${RED}❌ SSH connection failed. Please check your key and security groups.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ SSH connectivity confirmed${NC}"

# Create deployment directory
echo -e "${YELLOW}📁 Preparing deployment directory...${NC}"
ssh -i ~/.ssh/$KEY_NAME.pem -o StrictHostKeyChecking=no $EC2_USER@$INSTANCE_IP << 'EOF'
sudo mkdir -p /opt/streamr-coordinator
sudo chown ec2-user:ec2-user /opt/streamr-coordinator
EOF

# Copy application files
echo -e "${YELLOW}📦 Copying application files...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../../coordinator"
tar czf - app/ requirements.txt Dockerfile | ssh -i ~/.ssh/$KEY_NAME.pem -o StrictHostKeyChecking=no $EC2_USER@$INSTANCE_IP "cd /opt/streamr-coordinator && tar xzf -"

# Create environment configuration
echo -e "${YELLOW}⚙️ Creating environment configuration...${NC}"
ssh -i ~/.ssh/$KEY_NAME.pem -o StrictHostKeyChecking=no $EC2_USER@$INSTANCE_IP << EOF
cd /opt/streamr-coordinator

# Create .env file with AWS endpoints
cat > .env << ENVEOF
# Database Configuration
DATABASE_URL=postgresql://streamr_user:streamr_password@$DB_ENDPOINT:5432/streamr_db

# Redis Configuration  
REDIS_URL=redis://$CACHE_ENDPOINT:6379/0

# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
WORKERS=2

# Security
SECRET_KEY=\$(openssl rand -hex 32)
ENVEOF

echo "Environment configuration created"
EOF

# Install Docker if not present
echo -e "${YELLOW}🐳 Setting up Docker...${NC}"
ssh -i ~/.ssh/$KEY_NAME.pem -o StrictHostKeyChecking=no $EC2_USER@$INSTANCE_IP << 'EOF'
# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    sudo yum update -y
    sudo yum install -y docker
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -a -G docker ec2-user
    echo "Docker installed and started"
else
    echo "Docker already installed"
    sudo systemctl start docker
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose installed"
else
    echo "Docker Compose already installed"
fi
EOF

# Create docker-compose.yml for the application
echo -e "${YELLOW}📝 Creating Docker Compose configuration...${NC}"
ssh -i ~/.ssh/$KEY_NAME.pem -o StrictHostKeyChecking=no $EC2_USER@$INSTANCE_IP << 'EOF'
cd /opt/streamr-coordinator

cat > docker-compose.yml << 'COMPOSEEOF'
version: '3.8'

services:
  coordinator:
    build: .
    container_name: streamr-coordinator
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - streamr-network

  # SRS streaming server
  srs:
    image: ossrs/srs:5
    container_name: streamr-srs
    ports:
      - "1935:1935"  # RTMP
      - "8080:8080"  # HTTP API  
      - "8085:8080"  # HTTP server for HLS/DASH (external 8085 -> internal 8080)
    volumes:
      - ./srs.conf:/usr/local/srs/conf/srs.conf
    restart: unless-stopped
    networks:
      - streamr-network

networks:
  streamr-network:
    driver: bridge
COMPOSEEOF

echo "Docker Compose configuration created"
EOF

# Create SRS configuration
echo -e "${YELLOW}📺 Creating SRS streaming configuration...${NC}"
ssh -i ~/.ssh/$KEY_NAME.pem -o StrictHostKeyChecking=no $EC2_USER@$INSTANCE_IP << 'EOF'
cd /opt/streamr-coordinator

cat > srs.conf << 'SRSEOF'
# SRS configuration for StreamrP2P
listen              1935;
max_connections     1000;
srs_log_tank        file;
srs_log_file        ./objs/srs.log;

http_api {
    enabled         on;
    listen          8080;
    crossdomain     on;
}

http_server {
    enabled         on;
    listen          8085;
    dir             ./objs/nginx/html;
}

vhost __defaultVhost__ {
    # Enable HLS for web playback
    hls {
        enabled         on;
        hls_path        ./objs/nginx/html;
        hls_fragment    10;
        hls_window      60;
    }
    
    # Enable HTTP-FLV for low-latency
    http_remux {
        enabled     on;
        mount       [vhost]/[app]/[stream].flv;
    }
    
    # Enable DVR for recording
    dvr {
        enabled      off;
    }
}
SRSEOF

echo "SRS configuration created"
EOF

# Build and start the application
echo -e "${YELLOW}🏗️ Building and starting the application...${NC}"
ssh -i ~/.ssh/$KEY_NAME.pem -o StrictHostKeyChecking=no $EC2_USER@$INSTANCE_IP << 'EOF'
cd /opt/streamr-coordinator

# Stop any existing containers
docker-compose down 2>/dev/null || true

# Build and start the services
echo "Building application..."
docker-compose build

echo "Starting services..."
docker-compose up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 30

# Check service status
echo "Checking service status..."
docker-compose ps
EOF

# Test the deployment
echo -e "${YELLOW}🧪 Testing deployment...${NC}"
sleep 10

# Test coordinator health
if curl -s -f "http://$INSTANCE_IP:8000/health" > /dev/null; then
    echo -e "${GREEN}✅ Coordinator health check passed${NC}"
else
    echo -e "${RED}❌ Coordinator health check failed${NC}"
fi

# Test coordinator root endpoint
if curl -s -f "http://$INSTANCE_IP:8000/" | grep -q "StreamrP2P"; then
    echo -e "${GREEN}✅ Coordinator API responding${NC}"
else
    echo -e "${RED}❌ Coordinator API not responding${NC}"
fi

# Test SRS API
if curl -s -f "http://$INSTANCE_IP:8080/api/v1/versions" > /dev/null; then
    echo -e "${GREEN}✅ SRS streaming server responding${NC}"
else
    echo -e "${RED}❌ SRS streaming server not responding${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Application Deployment Complete!${NC}"
echo "=================================="
echo -e "${BLUE}📊 Service Endpoints:${NC}"
echo "• Coordinator API: http://$INSTANCE_IP:8000"
echo "• Dashboard: http://$INSTANCE_IP:8000/dashboard"
echo "• Health Check: http://$INSTANCE_IP:8000/health"
echo "• SRS API: http://$INSTANCE_IP:8080/api/v1/"
echo "• RTMP Ingest: rtmp://$INSTANCE_IP:1935/live/"
echo "• HLS Playback: http://$INSTANCE_IP:8085/live/{stream_key}.m3u8"
echo ""
echo -e "${YELLOW}💡 Next Steps:${NC}"
echo "1. Test streaming: ffmpeg -re -i test.mp4 -c copy -f flv rtmp://$INSTANCE_IP:1935/live/test"
echo "2. View dashboard: curl http://$INSTANCE_IP:8000/dashboard"
echo "3. Run friend testing with provided endpoints"
echo ""
echo -e "${BLUE}🔧 Debugging:${NC}"
echo "• SSH: ssh -i ~/.ssh/$KEY_NAME.pem $EC2_USER@$INSTANCE_IP"
echo "• Logs: docker-compose logs -f coordinator"
echo "• SRS Logs: docker-compose logs -f srs" 