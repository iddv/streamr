#!/bin/bash
# 🧪 StreamrP2P Networking Test Script
# Tests if networking is configured correctly for StreamrP2P

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    echo -e "${BLUE}🧪 StreamrP2P Networking Test Script${NC}"
    echo ""
    echo "Tests networking configuration for StreamrP2P host setup."
    echo ""
    echo "Usage:"
    echo "  ./test-networking.sh                    # Run all tests"
    echo "  ./test-networking.sh --coordinator-only # Test only coordinator connectivity"
    echo "  ./test-networking.sh --external-only    # Test only external connectivity"
    echo "  ./test-networking.sh --help             # Show this help"
    echo ""
    echo "Tests performed:"
    echo "  - Port availability check"
    echo "  - Coordinator service connectivity"
    echo "  - External access validation"
    echo "  - Network configuration summary"
    exit 0
}

# Parse arguments
COORDINATOR_ONLY=false
EXTERNAL_ONLY=false

case "${1:-}" in
    --help|-h|help)
        show_help
        ;;
    --coordinator-only)
        COORDINATOR_ONLY=true
        ;;
    --external-only)
        EXTERNAL_ONLY=true
        ;;
esac

echo -e "${BLUE}🧪 StreamrP2P Networking Test${NC}"
echo "============================"
echo ""

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNING=0

pass_test() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

fail_test() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
}

warn_test() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((TESTS_WARNING++))
}

# Test 1: Port Availability
if [[ "$EXTERNAL_ONLY" != true ]]; then
    echo -e "${BLUE}🔍 Test 1: Port Availability${NC}"
    echo "=========================="
    
    check_port() {
        local port=$1
        local service=$2
        
        if command -v lsof >/dev/null 2>&1; then
            if lsof -i :$port >/dev/null 2>&1; then
                warn_test "Port $port ($service) is in use"
                echo "    Process using port: $(lsof -i :$port | tail -1 | awk '{print $1}')"
            else
                pass_test "Port $port ($service) is available"
            fi
        elif command -v netstat >/dev/null 2>&1; then
            if netstat -ln 2>/dev/null | grep -q ":$port "; then
                warn_test "Port $port ($service) appears to be in use"
            else
                pass_test "Port $port ($service) appears available"
            fi
        else
            warn_test "Cannot check port $port ($service) - no lsof or netstat"
        fi
    }
    
    check_port 8000 "Coordinator"
    check_port 1935 "RTMP Input"
    check_port 1936 "RTMP Output"
    check_port 8081 "Ingest Stats"
    echo ""
fi

# Test 2: Docker Availability
if [[ "$EXTERNAL_ONLY" != true ]]; then
    echo -e "${BLUE}🐳 Test 2: Docker Availability${NC}"
    echo "============================="
    
    if command -v docker >/dev/null 2>&1; then
        if docker info >/dev/null 2>&1; then
            pass_test "Docker is installed and running"
        else
            fail_test "Docker is installed but not running"
            echo "    Try: docker version"
        fi
    else
        fail_test "Docker is not installed"
        echo "    Install Docker from: https://docs.docker.com/get-docker/"
    fi
    
    if command -v docker-compose >/dev/null 2>&1; then
        pass_test "Docker Compose is available"
    else
        warn_test "Docker Compose not found (may not be needed)"
    fi
    echo ""
fi

# Test 3: Coordinator Service Connectivity
if [[ "$EXTERNAL_ONLY" != true ]]; then
    echo -e "${BLUE}🏗️ Test 3: Coordinator Service${NC}"
    echo "=============================="
    
    # Check if coordinator is running
    if curl -s --connect-timeout 5 http://localhost:8000/health >/dev/null 2>&1; then
        pass_test "Coordinator is running and accessible on localhost:8000"
        
        # Test API endpoints
        if curl -s --connect-timeout 5 http://localhost:8000/streams >/dev/null 2>&1; then
            pass_test "Coordinator API endpoints are responding"
        else
            warn_test "Coordinator health check passed but API endpoints may not be ready"
        fi
        
    else
        warn_test "Coordinator is not running on localhost:8000"
        echo "    Start coordinator with: ./start-host.sh"
        echo "    Or manually: cd coordinator && docker-compose up -d"
    fi
    echo ""
fi

# Test 4: Network Configuration Detection
echo -e "${BLUE}🌐 Test 4: Network Configuration${NC}"
echo "=============================="

# Get local IP
if command -v ip >/dev/null 2>&1; then
    # Linux/WSL
    LOCAL_IP=$(ip route get 8.8.8.8 2>/dev/null | sed -n '/src/{s/.*src *\([^ ]*\).*/\1/p;q}')
elif command -v route >/dev/null 2>&1; then
    # macOS
    LOCAL_IP=$(route -n get default 2>/dev/null | grep interface | awk '{print $2}' | xargs ifconfig 2>/dev/null | grep inet | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
else
    # Fallback
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "")
fi

if [[ -n "$LOCAL_IP" ]]; then
    pass_test "Local IP detected: $LOCAL_IP"
else
    warn_test "Could not detect local IP address"
fi

# Get router IP
if command -v ip >/dev/null 2>&1; then
    # Linux/WSL
    ROUTER_IP=$(ip route | grep default | awk '{print $3}' | head -1)
elif command -v route >/dev/null 2>&1; then
    # macOS
    ROUTER_IP=$(route -n get default 2>/dev/null | grep gateway | awk '{print $2}')
fi

if [[ -n "$ROUTER_IP" ]]; then
    pass_test "Router IP detected: $ROUTER_IP"
else
    warn_test "Could not detect router IP address"
fi

# Get public IP
if [[ "$COORDINATOR_ONLY" != true ]]; then
    echo -e "${BLUE}🌍 Test 5: External Connectivity${NC}"
    echo "=============================="
    
    PUBLIC_IP=$(curl -s --connect-timeout 10 https://api.ipify.org 2>/dev/null || echo "")
    if [[ -n "$PUBLIC_IP" ]]; then
        pass_test "Public IP detected: $PUBLIC_IP"
    else
        warn_test "Could not detect public IP (may be network issue)"
    fi
    
    # Test if external services can reach coordinator (if running)
    if curl -s --connect-timeout 5 http://localhost:8000/health >/dev/null 2>&1; then
        echo "Testing external coordinator access..."
        echo "NOTE: This test requires router port forwarding to be configured"
        
        if [[ -n "$PUBLIC_IP" ]]; then
            # Try to test external access (this will likely fail without port forwarding)
            if curl -s --connect-timeout 10 http://$PUBLIC_IP:8000/health >/dev/null 2>&1; then
                pass_test "External coordinator access working!"
            else
                warn_test "External coordinator access not working"
                echo "    This is expected if router port forwarding is not configured"
                echo "    Configure router to forward port 8000 to $LOCAL_IP:8000"
            fi
        fi
    fi
    echo ""
fi

# Platform-specific checks
echo -e "${BLUE}🖥️ Platform-Specific Checks${NC}"
echo "==========================="

# Detect platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if grep -qi microsoft /proc/version 2>/dev/null; then
        PLATFORM="WSL"
        echo "Platform: Windows WSL"
        
        # Check WSL-specific networking
        if command -v netsh.exe >/dev/null 2>&1; then
            echo "Checking Windows port forwarding..."
            PORT_FORWARD_RULES=$(netsh.exe interface portproxy show all 2>/dev/null || echo "")
            if echo "$PORT_FORWARD_RULES" | grep -q "8000"; then
                pass_test "Windows port forwarding configured for port 8000"
            else
                warn_test "Windows port forwarding not configured"
                echo "    Run: scripts/setup-host-networking-wsl.ps1 (as Administrator)"
            fi
        fi
    else
        PLATFORM="Linux"
        echo "Platform: Linux"
        pass_test "No additional platform configuration needed"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macOS"
    echo "Platform: macOS"
    
    # Check macOS firewall
    FIREWALL_STATUS=$(sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null || echo "Error")
    if [[ "$FIREWALL_STATUS" == *"enabled"* ]]; then
        warn_test "macOS firewall is enabled"
        echo "    Run: scripts/setup-host-networking-macos.sh"
    else
        pass_test "macOS firewall is disabled (no configuration needed)"
    fi
else
    PLATFORM="Unknown"
    warn_test "Unknown platform: $OSTYPE"
fi

echo ""

# Summary
echo -e "${BLUE}📊 Test Summary${NC}"
echo "==============="
echo -e "✅ Passed:   $TESTS_PASSED"
echo -e "❌ Failed:   $TESTS_FAILED"
echo -e "⚠️  Warnings: $TESTS_WARNING"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    if [[ $TESTS_WARNING -eq 0 ]]; then
        echo -e "${GREEN}🎉 All tests passed! Your networking setup looks good.${NC}"
    else
        echo -e "${YELLOW}⚠️  Some warnings found. Review the warnings above.${NC}"
    fi
else
    echo -e "${RED}❌ Some tests failed. Please fix the issues above.${NC}"
fi

echo ""
echo -e "${BLUE}🚀 Next Steps:${NC}"
echo "============="
if [[ "$PLATFORM" == "WSL" ]]; then
    echo "1. Run networking setup: scripts/setup-host-networking-wsl.ps1 (as Administrator)"
elif [[ "$PLATFORM" == "macOS" ]]; then
    echo "1. Run networking setup: scripts/setup-host-networking-macos.sh"
fi
echo "2. Configure router port forwarding (see setup script output)"
echo "3. Start coordinator: ./start-host.sh"
echo "4. Test again: ./scripts/test-networking.sh"
echo "5. Share with friends: http://$PUBLIC_IP:8000 (after router config)"

exit 0 