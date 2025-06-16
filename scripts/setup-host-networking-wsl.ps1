# 🌐 StreamrP2P Host Networking Setup - Windows WSL
# Automatically configures Windows networking for StreamrP2P host

param(
    [switch]$Help,
    [switch]$Uninstall
)

if ($Help) {
    Write-Host "🌐 StreamrP2P Host Networking Setup for Windows WSL" -ForegroundColor Blue
    Write-Host ""
    Write-Host "This script configures Windows networking to allow StreamrP2P testing:"
    Write-Host "  - Sets up port forwarding from Windows to WSL"
    Write-Host "  - Configures Windows Firewall rules"
    Write-Host "  - Provides router configuration guidance"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\setup-host-networking-wsl.ps1          # Setup networking"
    Write-Host "  .\setup-host-networking-wsl.ps1 -Uninstall  # Remove all changes"
    Write-Host "  .\setup-host-networking-wsl.ps1 -Help    # Show this help"
    Write-Host ""
    Write-Host "Ports configured: 8000 (coordinator), 1936 (RTMP stream)"
    exit 0
}

Write-Host "🌐 StreamrP2P Host Networking Setup for Windows WSL" -ForegroundColor Blue
Write-Host "=================================================="
Write-Host ""

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ This script must be run as Administrator" -ForegroundColor Red
    Write-Host ""
    Write-Host "Right-click PowerShell and select 'Run as Administrator'"
    Write-Host "Then navigate back to this directory and run the script again."
    exit 1
}

# Get WSL IP address
Write-Host "🔍 Detecting WSL IP address..." -ForegroundColor Yellow
try {
    $WSL_IP = (wsl hostname -I).Trim()
    if ([string]::IsNullOrEmpty($WSL_IP)) {
        throw "Empty WSL IP"
    }
    Write-Host "✅ WSL IP detected: $WSL_IP" -ForegroundColor Green
} catch {
    Write-Host "❌ Could not detect WSL IP address" -ForegroundColor Red
    Write-Host "Make sure WSL is installed and running."
    Write-Host "Try: wsl --install (requires reboot)"
    exit 1
}

if ($Uninstall) {
    Write-Host "🧹 Removing StreamrP2P networking configuration..." -ForegroundColor Yellow
    Write-Host ""
    
    # Remove port forwarding rules
    Write-Host "Removing port forwarding rules..."
    netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0 2>$null
    netsh interface portproxy delete v4tov4 listenport=1936 listenaddress=0.0.0.0 2>$null
    
    # Remove firewall rules
    Write-Host "Removing firewall rules..."
    Remove-NetFirewallRule -DisplayName "StreamrP2P Coordinator" -ErrorAction SilentlyContinue
    Remove-NetFirewallRule -DisplayName "StreamrP2P RTMP" -ErrorAction SilentlyContinue
    
    Write-Host ""
    Write-Host "✅ StreamrP2P networking configuration removed" -ForegroundColor Green
    Write-Host "Note: You'll need to manually remove router port forwarding rules"
    exit 0
}

Write-Host "⚙️ Configuring networking..." -ForegroundColor Yellow
Write-Host ""

# Setup port forwarding from Windows to WSL
Write-Host "1. Setting up port forwarding from Windows to WSL..."
try {
    # Remove any existing rules first
    netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0 2>$null
    netsh interface portproxy delete v4tov4 listenport=1936 listenaddress=0.0.0.0 2>$null
    
    # Add new forwarding rules
    netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=$WSL_IP
    netsh interface portproxy add v4tov4 listenport=1936 listenaddress=0.0.0.0 connectport=1936 connectaddress=$WSL_IP
    
    Write-Host "   ✅ Port forwarding configured" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Failed to configure port forwarding: $_" -ForegroundColor Red
    exit 1
}

# Configure Windows Firewall
Write-Host "2. Configuring Windows Firewall..."
try {
    # Remove any existing rules first
    Remove-NetFirewallRule -DisplayName "StreamrP2P Coordinator" -ErrorAction SilentlyContinue
    Remove-NetFirewallRule -DisplayName "StreamrP2P RTMP" -ErrorAction SilentlyContinue
    
    # Add new firewall rules
    New-NetFirewallRule -DisplayName "StreamrP2P Coordinator" -Direction Inbound -Port 8000 -Protocol TCP -Action Allow | Out-Null
    New-NetFirewallRule -DisplayName "StreamrP2P RTMP" -Direction Inbound -Port 1936 -Protocol TCP -Action Allow | Out-Null
    
    Write-Host "   ✅ Firewall rules configured" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Failed to configure firewall: $_" -ForegroundColor Red
    exit 1
}

# Get Windows IP address for router configuration
Write-Host "3. Detecting network configuration..." -ForegroundColor Yellow
try {
    $WINDOWS_IP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Ethernet*", "Wi-Fi*" | Where-Object {$_.IPAddress -match "^192\.168\.|^10\.|^172\."} | Select-Object -First 1).IPAddress
    $GATEWAY = (Get-NetRoute -DestinationPrefix "0.0.0.0/0" | Get-NetIPConfiguration | Select-Object -First 1).IPv4DefaultGateway.NextHop
    
    if ([string]::IsNullOrEmpty($WINDOWS_IP)) {
        $WINDOWS_IP = "Unable to detect"
    }
    if ([string]::IsNullOrEmpty($GATEWAY)) {
        $GATEWAY = "Unable to detect"
    }
    
    Write-Host "   ✅ Network information gathered" -ForegroundColor Green
} catch {
    $WINDOWS_IP = "Unable to detect"
    $GATEWAY = "Unable to detect"
    Write-Host "   ⚠️ Could not detect all network information" -ForegroundColor Yellow
}

# Test port forwarding
Write-Host "4. Testing port forwarding configuration..."
Start-Sleep 2
$PORT_FORWARD_RULES = netsh interface portproxy show all
if ($PORT_FORWARD_RULES -match "8000" -and $PORT_FORWARD_RULES -match "1936") {
    Write-Host "   ✅ Port forwarding rules verified" -ForegroundColor Green
} else {
    Write-Host "   ⚠️ Port forwarding rules may not be active" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Windows networking configuration complete!" -ForegroundColor Green
Write-Host ""

# Show configuration summary
Write-Host "📊 Configuration Summary:" -ForegroundColor Blue
Write-Host "========================"
Write-Host "WSL IP Address:      $WSL_IP"
Write-Host "Windows IP Address:  $WINDOWS_IP"
Write-Host "Router IP Address:   $GATEWAY"
Write-Host "Ports Configured:    8000 (coordinator), 1936 (RTMP)"
Write-Host ""

# Router configuration instructions
Write-Host "🔧 ROUTER CONFIGURATION REQUIRED:" -ForegroundColor Yellow
Write-Host "================================="
Write-Host "You still need to configure your router for external access:"
Write-Host ""
Write-Host "1. Open your router admin panel:"
Write-Host "   Navigate to: http://$GATEWAY"
Write-Host "   (Login details usually on router label)"
Write-Host ""
Write-Host "2. Find 'Port Forwarding' or 'Virtual Server' section"
Write-Host ""
Write-Host "3. Add these port forwarding rules:"
Write-Host "   External Port 8000  → Internal IP $WINDOWS_IP Port 8000  (TCP)"
Write-Host "   External Port 1936  → Internal IP $WINDOWS_IP Port 1936  (TCP)"
Write-Host ""

# Get public IP
Write-Host "4. Your public IP for sharing with friends:"
try {
    $PUBLIC_IP = Invoke-RestMethod -Uri "https://api.ipify.org" -TimeoutSec 10
    Write-Host "   Public IP: $PUBLIC_IP" -ForegroundColor Green
    Write-Host ""
    Write-Host "   Share this with friends: http://$PUBLIC_IP:8000"
} catch {
    Write-Host "   Could not determine public IP automatically"
    Write-Host "   Visit https://whatismyipaddress.com/ to find your public IP"
}

Write-Host ""
Write-Host "🧪 Testing Commands:" -ForegroundColor Blue
Write-Host "==================="
Write-Host "After router configuration, test with:"
Write-Host "  # Test coordinator access (from another computer):"
Write-Host "  curl http://YOUR_PUBLIC_IP:8000/health"
Write-Host ""
Write-Host "  # Test local port forwarding:"
Write-Host "  curl http://localhost:8000/health  # (after starting coordinator)"
Write-Host ""

# Cleanup instructions
Write-Host "🧹 To Remove This Configuration:" -ForegroundColor Blue
Write-Host "================================"
Write-Host "Run: .\setup-host-networking-wsl.ps1 -Uninstall"
Write-Host ""

Write-Host "✅ Setup complete! Start your coordinator and configure your router." -ForegroundColor Green 