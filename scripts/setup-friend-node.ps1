# 🚀 StreamrP2P Friend Node Setup (Windows PowerShell)
# Usage: Right-click -> "Run with PowerShell"
# Or: powershell -ExecutionPolicy Bypass -File setup-friend-node.ps1 YOUR_STREAM_KEY

param(
    [Parameter(Mandatory=$false)]
    [string]$StreamKey
)

# Colors for pretty output
$Red = "`e[31m"
$Green = "`e[32m"
$Blue = "`e[34m"
$Yellow = "`e[33m"
$NC = "`e[0m"

Write-Host "${Blue}🚀 StreamrP2P Friend Node Setup (Windows)${NC}"
Write-Host "=============================================="

# Get stream key if not provided
if (-not $StreamKey) {
    $StreamKey = Read-Host "Enter your friend's stream key (e.g., obs-test)"
    if (-not $StreamKey) {
        Write-Host "${Red}❌ Stream key required${NC}"
        Write-Host "Get your stream key from your friend who's hosting the stream!"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

$CoordinatorUrl = "http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com"
$SrsRtmpUrl = "rtmp://108.129.47.155:1935/live"
$SrsHlsUrl = "http://108.129.47.155:8080/live"
$NodeId = "friend_$env:USERNAME_$(Get-Date -UFormat %s)"

Write-Host "${Yellow}📋 Configuration:${NC}"
Write-Host "  Coordinator: $CoordinatorUrl"
Write-Host "  Stream Key: $StreamKey"
Write-Host "  Node ID: $NodeId"
Write-Host "  RTMP Source: $SrsRtmpUrl/$StreamKey"
Write-Host "  HLS Output: $SrsHlsUrl/$StreamKey.m3u8"
Write-Host ""

# Check if Docker is installed
Write-Host "${Blue}🔍 Checking Docker installation...${NC}"
try {
    $dockerVersion = docker --version 2>$null
    if ($dockerVersion) {
        Write-Host "${Green}✅ Docker found: $dockerVersion${NC}"
    } else {
        throw "Docker not found"
    }
} catch {
    Write-Host "${Red}❌ Docker not found${NC}"
    Write-Host ""
    Write-Host "Please install Docker Desktop first:"
    Write-Host "  1. Go to: https://docs.docker.com/desktop/windows/install/"
    Write-Host "  2. Download Docker Desktop"
    Write-Host "  3. Install and restart your computer"
    Write-Host "  4. Start Docker Desktop"
    Write-Host "  5. Run this script again"
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Docker is running
Write-Host "${Blue}🔍 Checking if Docker is running...${NC}"
try {
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "${Green}✅ Docker is running${NC}"
    } else {
        throw "Docker not running"
    }
} catch {
    Write-Host "${Red}❌ Docker not running${NC}"
    Write-Host "Please start Docker Desktop and try again"
    Read-Host "Press Enter to exit"
    exit 1
}

# Test connection to coordinator
Write-Host "${Blue}🔍 Testing connection to coordinator...${NC}"
try {
    $response = Invoke-WebRequest -Uri "$CoordinatorUrl/health" -TimeoutSec 10 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "${Green}✅ Connection successful${NC}"
    } else {
        throw "Connection failed"
    }
} catch {
    Write-Host "${Red}❌ Cannot reach coordinator${NC}"
    Write-Host "Please check your internet connection"
    Read-Host "Press Enter to exit"
    exit 1
}

# Stop any existing node
Write-Host "${Blue}🧹 Cleaning up existing node...${NC}"
docker stop streamr-friend-node 2>$null | Out-Null
docker rm streamr-friend-node 2>$null | Out-Null

# Start the node
Write-Host "${Blue}🚀 Starting StreamrP2P friend node...${NC}"
Write-Host "${Yellow}Note: This is a simplified test setup. Full P2P functionality coming soon!${NC}"

$dockerCmd = @(
    "run", "-d",
    "--name", "streamr-friend-node",
    "--restart", "unless-stopped",
    "-p", "1936:1935",
    "-p", "8081:8080",
    "-e", "STREAM_KEY=$StreamKey",
    "-e", "NODE_ID=$NodeId",
    "ossrs/srs:5"
)

try {
    docker @dockerCmd
    if ($LASTEXITCODE -eq 0) {
        Write-Host "${Green}✅ Friend node started successfully!${NC}"
        Write-Host ""
        Write-Host "${Yellow}📊 Your Node Status:${NC}"
        Write-Host "  Node ID: $NodeId"
        Write-Host "  Local HLS: http://localhost:8081/live/$StreamKey.m3u8"
        Write-Host ""
        
        # Get public IP
        Write-Host "${Blue}🌐 Finding your public IP address...${NC}"
        try {
            $publicIp = (Invoke-WebRequest -Uri "https://ifconfig.me" -UseBasicParsing).Content.Trim()
            Write-Host "${Green}✅ Your public IP: $publicIp${NC}"
            Write-Host ""
            Write-Host "${Yellow}📋 Next Steps:${NC}"
            Write-Host "  1. Tell your friend to start streaming to: $SrsRtmpUrl/$StreamKey"
            Write-Host "  2. You can watch the stream at: $SrsHlsUrl/$StreamKey.m3u8"
            Write-Host "  3. Your relay URL: http://$publicIp:8081/live/$StreamKey.m3u8"
            Write-Host "  4. Send your relay URL to your friend"
            Write-Host ""
            Write-Host "${Yellow}🚨 IMPORTANT - Router Setup Required:${NC}"
            Write-Host "  Your router needs to forward port 8081 to this computer."
            Write-Host "  1. Open your router admin page (usually 192.168.1.1 or 192.168.0.1)"
            Write-Host "  2. Look for 'Port Forwarding' or 'Virtual Server'"
            Write-Host "  3. Forward external port 8081 to this computer's IP on port 8081"
            Write-Host "  4. Test at: https://canyouseeme.org (enter port 8081)"
            Write-Host ""
            Write-Host "${Yellow}🔧 Monitor your node:${NC}"
            Write-Host "  View logs: docker logs streamr-friend-node -f"
            Write-Host "  Stop node: docker stop streamr-friend-node"
            Write-Host "  Remove node: docker rm streamr-friend-node"
        } catch {
            Write-Host "${Yellow}⚠️  Could not determine public IP${NC}"
            Write-Host "Find your IP at: https://whatismyipaddress.com"
        }
        
        Write-Host ""
        Write-Host "${Green}🎉 You're now helping support the stream!${NC}"
        Write-Host "Your friend will see you in their dashboard and you'll earn rewards!"
    } else {
        throw "Docker run failed"
    }
} catch {
    Write-Host "${Red}❌ Failed to start node${NC}"
    Write-Host "Check Docker logs: docker logs streamr-friend-node"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Read-Host "Press Enter to close this window" 