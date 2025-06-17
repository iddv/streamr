# 🔧 Troubleshoot WSL2 External Access

## 🚨 **Current Status Analysis**
✅ **WSL2 Service**: Running (`curl localhost:8000/health` works)  
✅ **Port Forwarding**: Commands executed without error  
❌ **External Access**: `curl http://86.87.233.125:8000/health` fails  

## 📊 **Your Network Configuration**
```
WSL2 Instance: 172.21.197.138 (your services)
Windows Host:  172.21.192.1 (WSL adapter) 
               192.168.2.2 (main ethernet - THIS is what router sees)
Router:        192.168.2.254
Public IP:     86.87.233.125
```

## 🔥 **Solution Steps (Do All Three)**

### Step 1: Complete Windows Firewall Rules
**Run in PowerShell as Administrator:**
```powershell
# Allow inbound connections to these ports
netsh advfirewall firewall add rule name="StreamrP2P-8000" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="StreamrP2P-1935" dir=in action=allow protocol=TCP localport=1935
netsh advfirewall firewall add rule name="StreamrP2P-8081" dir=in action=allow protocol=TCP localport=8081

# Verify firewall rules were added
netsh advfirewall firewall show rule name="StreamrP2P-8000"
```

### Step 2: Configure Router Port Forwarding
**Access your router admin panel:**
1. **Open browser**: `http://192.168.2.254` (your gateway)
2. **Login** with admin credentials
3. **Find Port Forwarding** section (usually under "Advanced" or "NAT")
4. **Add these rules:**

| External Port | Internal IP | Internal Port | Description |
|---------------|-------------|---------------|-------------|
| 8000          | 192.168.2.2 | 8000         | StreamrP2P API |
| 1935          | 192.168.2.2 | 1935         | RTMP Stream |
| 8081          | 192.168.2.2 | 8081         | SRS Stats |

⚠️ **CRITICAL**: Use `192.168.2.2` (your Windows machine IP), NOT the WSL2 IP!

### Step 3: Test the Full Chain
**From Windows PowerShell:**
```powershell
# Test 1: Windows machine can reach WSL2 service
curl http://172.21.197.138:8000/health

# Test 2: Windows machine can reach itself via port forwarding  
curl http://192.168.2.2:8000/health

# Test 3: External access (this should work after router config)
curl http://86.87.233.125:8000/health
```

## 🔍 **If Still Not Working**

### Check Port Forwarding Status
```powershell
# Verify your port forwarding rules exist
netsh interface portproxy show all

# Should show:
# Listen on ipv4:             Connect to ipv4:
# Address         Port        Address         Port
# --------------- ----------  --------------- ----------
# 0.0.0.0         8000        172.21.197.138  8000
# 0.0.0.0         1935        172.21.197.138  1935
```

### Alternative: Use Windows Host Interface
**If router config is too complex, try this simpler approach:**
```powershell
# Delete existing rules
netsh interface portproxy delete v4tov4 listenport=8000
netsh interface portproxy delete v4tov4 listenport=1935

# Forward to Windows host interface instead of WSL2 directly
netsh interface portproxy add v4tov4 listenaddress=192.168.2.2 listenport=8000 connectaddress=172.21.197.138 connectport=8000
netsh interface portproxy add v4tov4 listenaddress=192.168.2.2 listenport=1935 connectaddress=172.21.197.138 connectport=1935
```

## 🌐 **Quick Cloud Alternative**

**If Windows networking is too complex, deploy to DigitalOcean ($6/month):**

1. **Create Droplet** (Ubuntu 22.04, $6/month basic)
2. **Upload Docker Compose**:
```bash
scp -r coordinator/ root@your-droplet:/root/streamr/
ssh root@your-droplet "cd /root/streamr && docker-compose up -d"
```
3. **Test**: `curl http://your-droplet-ip:8000/health`
4. **Update friend script** with new IP

## ✅ **Verification Commands**

**Once any solution works, verify with:**
```bash
# From WSL2
curl -s --max-time 5 http://86.87.233.125:8000/health

# Should return: {"status":"healthy","service":"coordinator"}
```

**If that works, you're ready for friends!**

## 🚀 **Next: Phase 2A Friend Testing**

Once external access works:
1. **Generate API keys**: `openssl rand -hex 16`
2. **Send friends**: `./setup-friend-node.sh API_KEY`  
3. **Monitor**: `watch -n 5 'curl -s localhost:8000/dashboard | jq'`

Your breakthrough is so close! 🎯 