#!/bin/bash
# 🎥 SRS Streaming Test Script

echo "🎥 Testing RTMP Streaming to SRS Server"
echo "======================================="

# Check if ffmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ ffmpeg is not installed"
    exit 1
fi

echo "✅ ffmpeg is available"

# Test RTMP connection with a test pattern
echo "🚀 Starting test stream to rtmp://localhost:1935/live/test_stream_001"
echo "This will stream for 10 seconds..."
echo ""

# Generate a test pattern and stream it (shorter duration for testing)
ffmpeg -f lavfi -i testsrc2=duration=10:size=640x480:rate=30 \
       -f lavfi -i sine=frequency=1000:duration=10 \
       -c:v libx264 -preset ultrafast -tune zerolatency \
       -c:a aac -ar 44100 -ac 2 \
       -f flv rtmp://localhost:1935/live/test_stream_001

echo ""
echo "✅ Test stream completed"
echo "Check SRS stats: curl http://localhost:8081/api/v1/streams/" 