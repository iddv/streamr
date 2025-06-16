#!/bin/bash
# 🎥 StreamrP2P Ingest Server - Accept streams from OBS and provide them to nodes

set -e

echo "🎥 Starting StreamrP2P Ingest Server..."
echo "This will accept OBS streams on port 1935 and provide them on port 1936"
echo

# Stop any existing ingest server
if docker ps -q -f name=streamr-ingest | grep -q .; then
    echo "🔄 Stopping existing ingest server..."
    docker stop streamr-ingest >/dev/null 2>&1 || true
    docker rm streamr-ingest >/dev/null 2>&1 || true
fi

# Check if ports are available
check_port() {
    if netstat -an 2>/dev/null | grep -q ":$1.*LISTEN" || netstat -an 2>/dev/null | grep -q "0.0.0.0:$1"; then
        echo "⚠️  Port $1 is in use!"
        return 1
    fi
    return 0
}

if ! check_port 1935; then
    echo "❌ Port 1935 (OBS input) is already in use"
    echo "Please stop the service using port 1935 or change OBS settings"
    exit 1
fi

if ! check_port 1936; then
    echo "⚠️  Port 1936 (node output) is in use, but continuing..."
fi

echo "✅ Starting ingest server..."

# Start the ingest server
docker run -d \
    --name streamr-ingest \
    -p 1935:1935 \
    -p 1936:1936 \
    -p 8081:8081 \
    -v "$(pwd)/ingest_config.yaml:/config.yaml" \
    --restart unless-stopped \
    ubuntu:22.04 bash -c "
        apt-get update -qq && 
        apt-get install -y -qq git build-essential cmake libyaml-dev curl && 
        git clone -q https://github.com/elnormous/rtmp_relay.git /tmp/rtmp_relay && 
        cd /tmp/rtmp_relay && 
        git submodule update --init --quiet && 
        make -s && 
        echo 'RTMP Relay built successfully' &&
        ./bin/rtmp_relay --config /config.yaml
    "

# Wait for startup
echo "⏳ Waiting for ingest server to start..."
sleep 3

# Check if it's running
if docker ps -q -f name=streamr-ingest | grep -q .; then
    echo "✅ Ingest server started successfully!"
    echo
    echo "📋 Connection Details:"
    echo "  OBS Server:     rtmp://localhost:1935/live"
    echo "  OBS Stream Key: test_stream_001  (or test_stream_002)"
    echo "  Stats Page:     http://localhost:8081/stats.json"
    echo
    echo "🎯 Next Steps:"
    echo "  1. Open OBS Studio"
    echo "  2. Go to Settings → Stream"
    echo "  3. Set Server: rtmp://localhost:1935/live"
    echo "  4. Set Stream Key: test_stream_001"
    echo "  5. Click 'Start Streaming'"
    echo
    echo "📊 Monitor with:"
    echo "  docker logs streamr-ingest -f"
    echo "  curl http://localhost:8081/stats.json"
    echo
else
    echo "❌ Ingest server failed to start"
    echo "Checking logs..."
    docker logs streamr-ingest
    exit 1
fi 