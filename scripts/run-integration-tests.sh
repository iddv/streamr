#!/bin/bash

# 🧪 StreamrP2P Integration Test Runner
# Parameterized integration tests for any coordinator endpoint

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TEST_TARGET="${1:-local}"
TEST_SUITE="${2:-smoke}"  # smoke, lifecycle, or all

# Set environment for tests
export TEST_TARGET="$TEST_TARGET"

echo -e "${BLUE}🧪 StreamrP2P Integration Tests${NC}"
echo -e "${BLUE}Target: ${TEST_TARGET} | Suite: ${TEST_SUITE}${NC}"
echo

# Function to get coordinator URL for a target
get_coordinator_url() {
    local target=$1
    case "$target" in
        "local")
            echo "http://localhost:8000"
            ;;
        "production"|"prod"|"beta")
            echo "http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com"
            ;;
        http*)
            echo "$target"  # Direct URL
            ;;
        *)
            echo "http://localhost:8000"  # Default fallback
            ;;
    esac
}

# Function to check if coordinator is running
check_coordinator() {
    local url=$(get_coordinator_url "$TEST_TARGET")
    echo -e "${BLUE}🔍 Checking coordinator at $url...${NC}"
    
    if curl -s "$url" > /dev/null; then
        echo -e "${GREEN}✅ Coordinator is running${NC}"
        return 0
    else
        echo -e "${RED}❌ Coordinator is not accessible at $url${NC}"
        return 1
    fi
}

# Install test dependencies if needed
install_deps() {
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}📦 Installing test dependencies...${NC}"
        pip install -r requirements-test.txt
    fi
}

# Run integration tests
run_tests() {
    local url=$(get_coordinator_url "$TEST_TARGET")
    
    if ! check_coordinator; then
        if [[ "$TEST_TARGET" == "local" ]]; then
            echo -e "${YELLOW}💡 Start local coordinator: cd coordinator && python -m uvicorn app.main:app --reload${NC}"
        fi
        exit 1
    fi
    
    # Select test suite to run
    case "$TEST_SUITE" in
        "smoke")
            echo -e "${BLUE}🌐 Running Smoke Tests against $url${NC}"
            pytest tests/test_production_smoke.py -v -s
            ;;
        "lifecycle")
            echo -e "${BLUE}🔄 Running Stream Lifecycle Tests against $url${NC}"
            pytest tests/test_stream_lifecycle_integration.py -v -s
            ;;
        "all")
            echo -e "${BLUE}🔬 Running All Integration Tests against $url${NC}"
            pytest tests/ -v -s
            ;;
        *)
            echo -e "${YELLOW}Unknown test suite: $TEST_SUITE${NC}"
            echo -e "${YELLOW}Available suites: smoke, lifecycle, all${NC}"
            exit 1
            ;;
    esac
}

# Display usage if help is requested
if [[ "$TEST_TARGET" == "help" || "$TEST_TARGET" == "-h" || "$TEST_TARGET" == "--help" ]]; then
    echo -e "${YELLOW}Usage: $0 [TARGET] [SUITE]${NC}"
    echo
    echo -e "${YELLOW}TARGETS:${NC}"
    echo -e "${YELLOW}  local         - Test against local coordinator (http://localhost:8000)${NC}"
    echo -e "${YELLOW}  production    - Test against production coordinator${NC}"
    echo -e "${YELLOW}  beta          - Test against beta coordinator (alias for production)${NC}"
    echo -e "${YELLOW}  http://...    - Test against custom coordinator URL${NC}"
    echo
    echo -e "${YELLOW}SUITES:${NC}"
    echo -e "${YELLOW}  smoke         - Basic health and compatibility tests (default)${NC}"
    echo -e "${YELLOW}  lifecycle     - Full stream lifecycle state machine tests${NC}"
    echo -e "${YELLOW}  all           - All integration tests${NC}"
    echo
    echo -e "${YELLOW}EXAMPLES:${NC}"
    echo -e "${YELLOW}  $0 local smoke                    # Local smoke tests${NC}"
    echo -e "${YELLOW}  $0 production all                 # All production tests${NC}"
    echo -e "${YELLOW}  $0 http://my-env.com lifecycle    # Custom URL lifecycle tests${NC}"
    exit 0
fi

# Main execution
install_deps
run_tests

echo
echo -e "${GREEN}✅ Integration tests completed successfully!${NC}" 