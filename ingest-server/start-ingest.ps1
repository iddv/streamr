# 🎥 StreamrP2P Ingest Server - Accept streams from OBS and provide them to nodes
# PowerShell version for Windows users

Write-Host "🎥 Starting StreamrP2P Ingest Server..." -ForegroundColor Blue
Write-Host "This will accept OBS streams on port 1935 and provide them on port 1936"
Write-Host

# Stop any existing ingest server
$existing = docker ps -q -f name=streamr-ingest
if ($existing) {
    Write-Host "🔄 Stopping existing ingest server..." -ForegroundColor Yellow
    docker stop streamr-ingest | Out-Null
    docker rm streamr-ingest | Out-Null
}

# Check if ports are available
function Test-Port {
    param([int]$Port)
    $listener = $null
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    }
    catch {
        return $false
    }
    finally {
        if ($listener) { $listener.Stop() }
    }
}

if (-not (Test-Port 1935)) {
    Write-Host "❌ Port 1935 (OBS input) is already in use" -ForegroundColor Red
    Write-Host "Please stop the service using port 1935 or change OBS settings"
    exit 1
}

if (-not (Test-Port 1936)) {
    Write-Host "⚠️  Port 1936 (node output) is in use, but continuing..." -ForegroundColor Yellow
}

Write-Host "✅ Starting ingest server..." -ForegroundColor Green

# Get the current directory for mounting the config file
$currentDir = Get-Location

# Start the ingest server
$dockerCmd = @"
docker run -d \
--name streamr-ingest \
-p 1935:1935 \
-p 1936:1936 \
-p 8081:8081 \
-v "$currentDir/ingest_config.yaml:/config.yaml" \
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
"@

Invoke-Expression $dockerCmd | Out-Null

# Wait for startup
Write-Host "⏳ Waiting for ingest server to start..." -ForegroundColor Blue
Start-Sleep -Seconds 3

# Check if it's running
$running = docker ps -q -f name=streamr-ingest
if ($running) {
    Write-Host "✅ Ingest server started successfully!" -ForegroundColor Green
    Write-Host
    Write-Host "📋 Connection Details:" -ForegroundColor Yellow
    Write-Host "  OBS Server:     rtmp://localhost:1935/live"
    Write-Host "  OBS Stream Key: test_stream_001  (or test_stream_002)"
    Write-Host "  Stats Page:     http://localhost:8081/stats.json"
    Write-Host
    Write-Host "🎯 Next Steps:" -ForegroundColor Cyan
    Write-Host "  1. Open OBS Studio"
    Write-Host "  2. Go to Settings → Stream"
    Write-Host "  3. Set Server: rtmp://localhost:1935/live"
    Write-Host "  4. Set Stream Key: test_stream_001"
    Write-Host "  5. Click 'Start Streaming'"
    Write-Host
    Write-Host "📊 Monitor with:" -ForegroundColor Magenta
    Write-Host "  docker logs streamr-ingest -f"
    Write-Host "  curl http://localhost:8081/stats.json"
    Write-Host
} else {
    Write-Host "❌ Ingest server failed to start" -ForegroundColor Red
    Write-Host "Checking logs..."
    docker logs streamr-ingest
    exit 1
} 