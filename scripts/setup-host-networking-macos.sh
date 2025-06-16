#!/bin/bash
# 🌐 StreamrP2P Host Networking Setup - macOS
# Automatically configures macOS networking for StreamrP2P host

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    echo -e "${BLUE}🌐 StreamrP2P Host Networking Setup for macOS${NC}"
    echo ""
    echo "This script configures macOS networking to allow StreamrP2P testing:"
    echo "  - Configures macOS firewall if enabled"
    echo "  - Detects network configuration"
    echo "  - Provides router configuration guidance"
    echo ""
    echo "Usage:"
    echo "  ./setup-host-networking-macos.sh          # Setup networking"
    echo "  ./setup-host-networking-macos.sh uninstall  # Remove firewall rules"
    echo "  ./setup-host-networking-macos.sh help     # Show this help"
    echo ""
    echo "Ports configured: 8000 (coordinator), 1936 (RTMP stream)"
    exit 0
}

uninstall_config() {
    echo -e "${YELLOW}🧹 Removing StreamrP2P networking configuration...${NC}"
    echo ""
    
    # Remove Docker from firewall allowlist (if it was added)
    echo "Removing Docker from firewall allowlist..."
    sudo /usr/libexec/ApplicationFirewall/socketfilterfw --remove /usr/local/bin/docker 2>/dev/null || true
    sudo /usr/libexec/ApplicationFirewall/socketfilterfw --remove /Applications/Docker.app/Contents/MacOS/Docker 2>/dev/null || true
    
    echo ""
    echo -e "${GREEN}✅ StreamrP2P networking configuration removed${NC}"
    echo "Note: You'll need to manually remove router port forwarding rules"
    exit 0
}

# Handle command line arguments
case "${1:-}" in
    help|--help|-h)
        show_help
        ;;
    uninstall|--uninstall)
        uninstall_config
        ;;
esac

echo -e "${BLUE}🌐 StreamrP2P Host Networking Setup for macOS${NC}"
echo "============================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker Desktop for Mac first:"
    echo "  1. Download from: https://www.docker.com/products/docker-desktop"
    echo "  2. Install and start Docker Desktop"
    echo "  3. Re-run this script"
    exit 1
fi

echo -e "${GREEN}✅ Docker found${NC}"

# Get network information
echo -e "${BLUE}🔍 Detecting network configuration...${NC}"

# Get local IP address
LOCAL_IP=$(route -n get default 2>/dev/null | grep interface | awk '{print $2}' | xargs ifconfig 2>/dev/null | grep inet | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
if [[ -z "$LOCAL_IP" ]]; then
    # Alternative method
    LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
fi

# Get router IP
ROUTER_IP=$(route -n get default 2>/dev/null | grep gateway | awk '{print $2}')
if [[ -z "$ROUTER_IP" ]]; then
    ROUTER_IP="Unable to detect"
fi

if [[ -n "$LOCAL_IP" ]]; then
    echo -e "${GREEN}✅ Local IP detected: $LOCAL_IP${NC}"
else
    echo -e "${YELLOW}⚠️  Could not detect local IP address${NC}"
    LOCAL_IP="Unable to detect"
fi

echo -e "${GREEN}✅ Router IP detected: $ROUTER_IP${NC}"

# Check firewall status
echo -e "${BLUE}🔥 Checking macOS firewall...${NC}"
FIREWALL_STATUS=$(sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null || echo "Error")

if [[ "$FIREWALL_STATUS" == *"enabled"* ]]; then
    echo -e "${YELLOW}⚠️  macOS firewall is enabled${NC}"
    echo "Configuring firewall to allow Docker..."
    
    # Find Docker binary paths
    DOCKER_PATHS=(
        "/usr/local/bin/docker"
        "/Applications/Docker.app/Contents/MacOS/Docker"
        "/opt/homebrew/bin/docker"
    )
    
    DOCKER_CONFIGURED=false
    for DOCKER_PATH in "${DOCKER_PATHS[@]}"; do
        if [[ -f "$DOCKER_PATH" ]]; then
            echo "  Adding $DOCKER_PATH to firewall allowlist..."
            sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add "$DOCKER_PATH" 2>/dev/null || true
            sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblock "$DOCKER_PATH" 2>/dev/null || true
            DOCKER_CONFIGURED=true
        fi
    done
    
    if [[ "$DOCKER_CONFIGURED" == true ]]; then
        echo -e "${GREEN}   ✅ Docker configured in firewall${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Could not find Docker binary to configure${NC}"
        echo "   Docker containers should still work, but you may see firewall prompts"
    fi
    
elif [[ "$FIREWALL_STATUS" == *"disabled"* ]]; then
    echo -e "${GREEN}✅ macOS firewall is disabled (no configuration needed)${NC}"
else
    echo -e "${YELLOW}⚠️  Could not determine firewall status${NC}"
    echo "If you see firewall prompts when testing, allow Docker access"
fi

# Test port availability
echo -e "${BLUE}🔍 Checking port availability...${NC}"
check_port() {
    local port=$1
    if lsof -i :$port &> /dev/null; then
        echo -e "${YELLOW}   ⚠️  Port $port is in use${NC}"
        return 1
    else
        echo -e "${GREEN}   ✅ Port $port is available${NC}"
        return 0
    fi
}

check_port 8000
check_port 1936

# Get public IP
echo -e "${BLUE}🌍 Getting public IP address...${NC}"
PUBLIC_IP=$(curl -s --connect-timeout 10 https://api.ipify.org 2>/dev/null || echo "Unable to detect")

if [[ "$PUBLIC_IP" != "Unable to detect" ]]; then
    echo -e "${GREEN}✅ Public IP: $PUBLIC_IP${NC}"
else
    echo -e "${YELLOW}⚠️  Could not determine public IP${NC}"
    echo "Visit https://whatismyipaddress.com/ to find your public IP"
fi

echo ""
echo -e "${GREEN}🎉 macOS networking check complete!${NC}"
echo ""

# Show configuration summary
echo -e "${BLUE}📊 Configuration Summary:${NC}"
echo "========================"
echo "Local IP Address:    $LOCAL_IP"
echo "Router IP Address:   $ROUTER_IP"
echo "Public IP Address:   $PUBLIC_IP"
echo "Ports Required:      8000 (coordinator), 1936 (RTMP)"
echo ""

# Router configuration instructions
echo -e "${YELLOW}🔧 ROUTER CONFIGURATION REQUIRED:${NC}"
echo "================================="
echo "You need to configure your router for external access:"
echo ""
echo "1. Open your router admin panel:"
if [[ "$ROUTER_IP" != "Unable to detect" ]]; then
    echo "   Navigate to: http://$ROUTER_IP"
else
    echo "   Navigate to your router's IP (usually 192.168.1.1 or 192.168.0.1)"
fi
echo "   (Login details usually on router label)"
echo ""
echo "2. Find 'Port Forwarding' or 'Virtual Server' section"
echo ""
echo "3. Add these port forwarding rules:"
if [[ "$LOCAL_IP" != "Unable to detect" ]]; then
    echo "   External Port 8000  → Internal IP $LOCAL_IP Port 8000  (TCP)"
    echo "   External Port 1936  → Internal IP $LOCAL_IP Port 1936  (TCP)"
else
    echo "   External Port 8000  → Internal IP YOUR_MAC_IP Port 8000  (TCP)"
    echo "   External Port 1936  → Internal IP YOUR_MAC_IP Port 1936  (TCP)"
    echo "   (Find your Mac's IP in System Preferences → Network)"
fi
echo ""

# Share information for friends
if [[ "$PUBLIC_IP" != "Unable to detect" ]]; then
    echo "4. Your public IP for sharing with friends:"
    echo -e "   ${GREEN}Share this: http://$PUBLIC_IP:8000${NC}"
    echo ""
fi

echo -e "${BLUE}🧪 Testing Commands:${NC}"
echo "==================="
echo "After router configuration, test with:"
echo "  # Test coordinator access (from another computer):"
if [[ "$PUBLIC_IP" != "Unable to detect" ]]; then
    echo "  curl http://$PUBLIC_IP:8000/health"
else
    echo "  curl http://YOUR_PUBLIC_IP:8000/health"
fi
echo ""
echo "  # Test local access:"
echo "  curl http://localhost:8000/health  # (after starting coordinator)"
echo ""

# Local network testing option
echo -e "${BLUE}🏠 Local Network Testing (No Router Config):${NC}"
echo "=============================================="
echo "For testing without router configuration (local network only):"
if [[ "$LOCAL_IP" != "Unable to detect" ]]; then
    echo "  Friends on same network can use: http://$LOCAL_IP:8000"
else
    echo "  Friends on same network can use: http://YOUR_LOCAL_IP:8000"
    echo "  (Find your local IP in System Preferences → Network)"
fi
echo ""

# Alternative tools
echo -e "${BLUE}🛠️ Alternative: Use ngrok (No Router Config Needed):${NC}"
echo "==================================================="
echo "For easier testing without router configuration:"
echo "  1. Install ngrok: brew install ngrok"
echo "  2. After starting coordinator: ngrok http 8000"
echo "  3. Share the ngrok URL with friends"
echo ""

# Cleanup instructions
echo -e "${BLUE}🧹 To Remove This Configuration:${NC}"
echo "================================"
echo "Run: ./setup-host-networking-macos.sh uninstall"
echo ""

echo -e "${GREEN}✅ Setup complete! Start your coordinator and configure your router.${NC}" 