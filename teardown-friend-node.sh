#!/bin/bash

# 🧹 StreamrP2P Friend Node Teardown
# Usage: ./teardown-friend-node.sh

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹 StreamrP2P Friend Node Teardown${NC}"
echo "===================================="

# Stop and remove container
echo -e "${YELLOW}🛑 Stopping friend node...${NC}"
if docker stop streamr-friend-node 2>/dev/null; then
    echo -e "${GREEN}✅ Container stopped${NC}"
else
    echo -e "${YELLOW}⚠️  Container was not running${NC}"
fi

echo -e "${YELLOW}🗑️  Removing container...${NC}"
if docker rm streamr-friend-node 2>/dev/null; then
    echo -e "${GREEN}✅ Container removed${NC}"
else
    echo -e "${YELLOW}⚠️  Container was already removed${NC}"
fi

# Ask about removing Docker image
echo ""
echo -e "${YELLOW}🤔 Do you want to remove the Docker image too? (saves ~500MB disk space)${NC}"
echo "This will require re-downloading if you set up another node later."
read -p "Remove Docker image? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🗑️  Removing Docker image...${NC}"
    if docker rmi ossrs/srs:5 2>/dev/null; then
        echo -e "${GREEN}✅ Docker image removed${NC}"
    else
        echo -e "${YELLOW}⚠️  Docker image was already removed or in use${NC}"
    fi
else
    echo -e "${BLUE}ℹ️  Docker image kept (can be removed later with: docker rmi ossrs/srs:5)${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Friend node teardown complete!${NC}"
echo ""
echo -e "${YELLOW}📋 What was cleaned up:${NC}"
echo "  ✅ Stopped streamr-friend-node container"
echo "  ✅ Removed streamr-friend-node container"
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "  ✅ Removed SRS Docker image"
else
    echo "  ⏸️  Kept SRS Docker image"
fi
echo ""
echo -e "${BLUE}ℹ️  To help again later, just run: ./setup-friend-node.sh YOUR_STREAM_KEY${NC}"
echo ""
echo "Thanks for helping test StreamrP2P! 🚀" 