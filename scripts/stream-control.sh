#!/bin/bash

# 🔄 StreamrP2P Stream Lifecycle Control Script
# Manually control stream status for friends testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COORDINATOR_URL="${COORDINATOR_URL:-http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com}"
STREAM_ID="${STREAM_ID:-iddv-stream}"

# Function to display usage
usage() {
    echo "🔄 StreamrP2P Stream Control"
    echo
    echo "Usage: $0 [COMMAND] [STREAM_ID] [COORDINATOR_URL]"
    echo
    echo "Commands:"
    echo "  start     - Transition stream to LIVE (ready for supporters)"
    echo "  stop      - Transition stream to OFFLINE (end support)"
    echo "  test      - Transition stream to TESTING (private mode)"
    echo "  reset     - Transition stream to READY (initial state)"
    echo "  status    - Show current stream status"
    echo "  live      - List all LIVE streams"
    echo "  all       - List all streams with status"
    echo
    echo "Examples:"
    echo "  $0 start                    # Start your default stream"
    echo "  $0 start my-stream         # Start specific stream"
    echo "  $0 status                  # Check stream status"
    echo "  $0 live                    # See what streams supporters can join"
    echo
    echo "Environment Variables:"
    echo "  COORDINATOR_URL=$COORDINATOR_URL"
    echo "  STREAM_ID=$STREAM_ID"
}

# Function to update stream status
update_stream_status() {
    local stream_id="$1"
    local new_status="$2"
    local coordinator_url="$3"
    
    echo -e "${BLUE}🔄 Updating stream '$stream_id' to $new_status...${NC}"
    
    response=$(curl -s -X PATCH "$coordinator_url/streams/$stream_id/status" \
        -H "Content-Type: application/json" \
        -d "{\"status\": \"$new_status\"}" \
        -w "%{http_code}")
    
    http_code="${response: -3}"
    body="${response%???}"
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ Stream status updated successfully${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    else
        echo -e "${RED}❌ Failed to update stream status (HTTP $http_code)${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        return 1
    fi
}

# Function to get stream status
get_stream_status() {
    local stream_id="$1"
    local coordinator_url="$2"
    
    echo -e "${BLUE}🔍 Checking status of stream '$stream_id'...${NC}"
    
    response=$(curl -s "$coordinator_url/streams" -w "%{http_code}")
    http_code="${response: -3}"
    body="${response%???}"
    
    if [ "$http_code" = "200" ]; then
        # Extract stream info using basic text processing
        stream_info=$(echo "$body" | grep -A 10 "\"stream_id\":\"$stream_id\"" | head -20)
        
        if [ -n "$stream_info" ]; then
            status=$(echo "$stream_info" | grep -o '"status":"[^"]*"' | sed 's/"status":"//g' | sed 's/"//g')
            created=$(echo "$stream_info" | grep -o '"created_at":"[^"]*"' | sed 's/"created_at":"//g' | sed 's/"//g')
            live_at=$(echo "$stream_info" | grep -o '"live_started_at":"[^"]*"' | sed 's/"live_started_at":"//g' | sed 's/"//g')
            offline_at=$(echo "$stream_info" | grep -o '"offline_at":"[^"]*"' | sed 's/"offline_at":"//g' | sed 's/"//g')
            
            echo -e "${GREEN}✅ Stream found${NC}"
            echo "  Stream ID: $stream_id"
            echo "  Status: $status"
            echo "  Created: $created"
            [ -n "$live_at" ] && echo "  Live started: $live_at"
            [ -n "$offline_at" ] && echo "  Offline at: $offline_at"
            
            case $status in
                "LIVE")
                    echo -e "${GREEN}🟢 Stream is LIVE - supporters can join!${NC}"
                    ;;
                "READY")
                    echo -e "${YELLOW}🟡 Stream is READY - use 'start' to go live${NC}"
                    ;;
                "TESTING")
                    echo -e "${BLUE}🔵 Stream is TESTING - private mode${NC}"
                    ;;
                "OFFLINE")
                    echo -e "${RED}🔴 Stream is OFFLINE - no supporters active${NC}"
                    ;;
                *)
                    echo -e "${YELLOW}❓ Unknown status: $status${NC}"
                    ;;
            esac
        else
            echo -e "${RED}❌ Stream '$stream_id' not found${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Failed to fetch streams (HTTP $http_code)${NC}"
        return 1
    fi
}

# Function to list live streams
list_live_streams() {
    local coordinator_url="$1"
    
    echo -e "${BLUE}🔍 Checking LIVE streams (available for supporters)...${NC}"
    
    response=$(curl -s "$coordinator_url/streams/live" -w "%{http_code}")
    http_code="${response: -3}"
    body="${response%???}"
    
    if [ "$http_code" = "200" ]; then
        stream_count=$(echo "$body" | grep -o '"stream_id":' | wc -l)
        
        if [ "$stream_count" -gt 0 ]; then
            echo -e "${GREEN}✅ Found $stream_count LIVE stream(s)${NC}"
            echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        else
            echo -e "${YELLOW}⚠️  No streams currently LIVE${NC}"
            echo "Supporters won't find any streams to join right now."
        fi
    else
        echo -e "${RED}❌ Failed to fetch live streams (HTTP $http_code)${NC}"
        return 1
    fi
}

# Function to list all streams
list_all_streams() {
    local coordinator_url="$1"
    
    echo -e "${BLUE}🔍 Fetching all streams...${NC}"
    
    response=$(curl -s "$coordinator_url/streams" -w "%{http_code}")
    http_code="${response: -3}"
    body="${response%???}"
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ All streams:${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    else
        echo -e "${RED}❌ Failed to fetch streams (HTTP $http_code)${NC}"
        return 1
    fi
}

# Parse command line arguments
COMMAND="${1:-status}"
STREAM_ID="${2:-$STREAM_ID}"
COORDINATOR_URL="${3:-$COORDINATOR_URL}"

# Validate inputs
if [ -z "$STREAM_ID" ]; then
    echo -e "${RED}❌ STREAM_ID is required${NC}"
    usage
    exit 1
fi

if [ -z "$COORDINATOR_URL" ]; then
    echo -e "${RED}❌ COORDINATOR_URL is required${NC}"
    usage
    exit 1
fi

# Execute command
case $COMMAND in
    "start")
        update_stream_status "$STREAM_ID" "LIVE" "$COORDINATOR_URL"
        echo
        echo -e "${GREEN}🎉 Stream is now LIVE! Your supporters can join by running:${NC}"
        echo -e "${BLUE}./scripts/setup-node.sh${NC}"
        ;;
    "stop")
        update_stream_status "$STREAM_ID" "OFFLINE" "$COORDINATOR_URL"
        echo
        echo -e "${YELLOW}📱 Stream is now OFFLINE. Supporters will stop earning.${NC}"
        ;;
    "test")
        update_stream_status "$STREAM_ID" "TESTING" "$COORDINATOR_URL"
        echo
        echo -e "${BLUE}🔧 Stream is now in TESTING mode (private).${NC}"
        ;;
    "reset")
        update_stream_status "$STREAM_ID" "READY" "$COORDINATOR_URL"
        echo
        echo -e "${YELLOW}🔄 Stream reset to READY state.${NC}"
        ;;
    "status")
        get_stream_status "$STREAM_ID" "$COORDINATOR_URL"
        ;;
    "live")
        list_live_streams "$COORDINATOR_URL"
        ;;
    "all")
        list_all_streams "$COORDINATOR_URL"
        ;;
    "help"|"-h"|"--help")
        usage
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $COMMAND${NC}"
        echo
        usage
        exit 1
        ;;
esac 