#!/bin/bash
# 🎥 Simple Streaming Test Script

echo "🎥 Testing RTMP Streaming to StreamrP2P"
echo "======================================="

# Check if ffmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ ffmpeg is not installed"
    echo "Run: sudo apt install ffmpeg"
    exit 1
fi

echo "✅ ffmpeg is available"

# Test RTMP connection with a test pattern
echo "🚀 Starting test stream to rtmp://localhost:1935/live/test_stream_001"
echo "Press Ctrl+C to stop the test stream"
echo ""

# Generate a test pattern and stream it
ffmpeg -f lavfi -i testsrc2=duration=30:size=640x480:rate=30 \
       -f lavfi -i sine=frequency=1000:duration=30 \
       -c:v libx264 -preset ultrafast -tune zerolatency \
       -c:a aac -ar 44100 -ac 2 \
       -f flv rtmp://localhost:1935/live/test_stream_001

echo ""
echo "✅ Test stream completed"
echo "Check the dashboard: curl http://localhost:8000/dashboard | jq" 