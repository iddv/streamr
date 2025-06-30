#!/bin/bash

# 🚀 Quick SRS Setup for Friend Testing
# Deploys SRS locally for immediate streaming

echo "🎬 Setting up local SRS streaming server..."

# Stop any existing SRS
docker stop srs-server 2>/dev/null || true
docker rm srs-server 2>/dev/null || true

# Start SRS with proper configuration
docker run -d \
  --name srs-server \
  --restart unless-stopped \
  -p 1935:1935 \
  -p 8080:8080 \
  -p 1985:1985 \
  ossrs/srs:5

echo "⏳ Waiting for SRS to start..."
sleep 5

# Test if SRS is responding
if curl -s http://localhost:8080/ | grep -q "SRS"; then
    echo "✅ SRS is running!"
    echo ""
    echo "📋 Your streaming URLs:"
    echo "  RTMP (for OBS): rtmp://$(curl -s ifconfig.me):1935/live/"
    echo "  HLS (for viewing): http://$(curl -s ifconfig.me):8080/live/{stream}.m3u8"
    echo ""
    echo "🎯 For friend testing:"
    echo "  1. Start streaming in OBS to: rtmp://$(curl -s ifconfig.me):1935/live/obs-test"
    echo "  2. Friends can watch at: http://$(curl -s ifconfig.me):8080/live/obs-test.m3u8"
    echo ""
    echo "🔧 Monitor: docker logs srs-server -f"
else
    echo "❌ SRS failed to start. Check: docker logs srs-server"
fi 