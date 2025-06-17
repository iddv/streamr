# 🔧 Fix WSL2 External Access

## 🚨 **Issue Detected**
- ✅ Local service works: `curl localhost:8000/health` 
- ❌ External access fails: `curl 86.87.233.125:8000/health`

## 🔍 **Root Cause: WSL2 Networking**
WSL2 uses NAT networking, so services bound to WSL2 aren't automatically accessible from external networks.

## 🚀 **Solution Options (Pick One)**

### Option 1: PowerShell Port Forwarding (Recommended)
**Run as Administrator in Windows PowerShell:**
```powershell
# Forward external traffic to WSL2
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=8000 connectaddress=172.21.197.138 connectport=8000
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=1935 connectaddress=172.21.197.138 connectport=1935
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=8081 connectaddress=172.21.197.138 connectport=8081

# Verify port forwarding
netsh interface portproxy show all

# Allow through Windows Firewall
netsh advfirewall firewall add rule name="StreamrP2P-8000" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="StreamrP2P-1935" dir=in action=allow protocol=TCP localport=1935
netsh advfirewall firewall add rule name="StreamrP2P-8081" dir=in action=allow protocol=TCP localport=8081
```

### Option 2: Quick Cloud Test (If PowerShell Fails)
**Deploy to DigitalOcean for $6/month:**
```bash
# Simple cloud deployment
docker save coordinator_coordinator:latest | gzip > coordinator.tar.gz
scp coordinator.tar.gz user@your-droplet:/tmp/
ssh user@your-droplet "cd /tmp && docker load < coordinator.tar.gz && docker run -d -p 8000:8000 coordinator_coordinator:latest"
```

## ✅ **Test External Access**
```bash
# After applying fix, test from WSL2
curl -s --max-time 10 http://86.87.233.125:8000/health

# Should return: {"status":"healthy","service":"coordinator"}
```

## 🎯 **Router Port Forwarding**
**Still need to configure your router to forward these ports:**
- Router admin panel (usually `192.168.1.1` or `192.168.0.1`)
- Forward external port 8000 → internal IP 192.168.X.X:8000 (your Windows machine IP)
- Forward external port 1935 → internal IP 192.168.X.X:1935  
- Forward external port 8081 → internal IP 192.168.X.X:8081

**Find your Windows machine IP:**
```cmd
ipconfig | findstr "IPv4"
```

## 🔄 **After Fix - Ready for Friends!**
Once external access works, friends can connect using:
```bash
curl http://86.87.233.125:8000/health
```

If that succeeds, you're ready for Phase 2A friend testing! 🚀 