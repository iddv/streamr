# 🌐 Remote Testing Guide - StreamrP2P PoC

**Phase 2: Testing with Friends Across Real Networks**

This guide helps you transition from successful local testing to testing with friends across the internet.

## 🎯 Remote Testing Architecture

```
Your PC (Host):                    Friends' PCs (Nodes):
┌─────────────────────────┐       ┌─────────────────────────┐
│ 🎥 OBS → SRS Server     │       │ 📦 Node Client          │
│ 🏗️  Coordinator API     │◄────► │ (Connects via Internet) │
│ 🌐 Port Forwarding      │       │ 🌍 Any global location  │
└─────────────────────────┘       └─────────────────────────┘
         ^                                    ^
         │                                    │
    Router Config                        Friend Setup
```

## ✅ Prerequisites

Based on successful local testing, you need:
- ✅ **Local system working** (all services running on localhost)
- ✅ **Router admin access** (for port forwarding)
- ✅ **Static or dynamic IP** (friends need to reach you)
- ✅ **WSL networking configured** (if using Windows WSL)

## 🚀 Part 1: Configure External Access

### Step 1: Set Up WSL Port Forwarding (Windows)

If you're on Windows WSL, run this **as Administrator in PowerShell**:

```powershell
# Run the automated setup script
scripts/setup-host-networking-wsl.ps1

# Or manually configure ports
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=8000 connectaddress=127.0.0.1 connectport=8000
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=1935 connectaddress=127.0.0.1 connectport=1935  
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=8081 connectaddress=127.0.0.1 connectport=8081

# Verify port forwarding
netsh interface portproxy show all
```

### Step 2: Configure Router Port Forwarding

**Access your router's admin panel** (usually `192.168.1.1` or `192.168.0.1`) and forward these ports:

| External Port | Internal IP     | Internal Port | Service           |
|---------------|-----------------|---------------|-------------------|
| 8000          | YOUR_LOCAL_IP   | 8000          | Coordinator API   |
| 1935          | YOUR_LOCAL_IP   | 1935          | RTMP Streaming    |
| 8081          | YOUR_LOCAL_IP   | 8081          | SRS Stats         |

**Find your local IP:**
```bash
# On WSL/Linux
ip route get 8.8.8.8 | grep -oP 'src \K\S+'

# On Windows
ipconfig | findstr "IPv4"
```

### Step 3: Test External Connectivity

```bash
# Get your public IP
curl https://api.ipify.org

# Test external access (replace YOUR_PUBLIC_IP)
curl http://YOUR_PUBLIC_IP:8000/health

# If this works, you're ready for friends!
```

---

## 👥 Part 2: Friend Setup Instructions

### Quick Setup Command (Recommended)

Send this **one-command setup** to your friends:

```bash
# Replace YOUR_PUBLIC_IP with actual IP
curl -sSL https://raw.githubusercontent.com/your-username/streamr/main/setup-node.sh | bash -s http://YOUR_PUBLIC_IP:8000 test_stream_001
```

### Manual Setup (If Automated Fails)

**Step 1: Install Dependencies**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y docker.io docker-compose python3 python3-pip curl jq

# macOS
brew install docker docker-compose python3

# Start Docker
sudo systemctl start docker  # Linux
# Docker Desktop for macOS
```

**Step 2: Run Node Client**
```bash
# Quick Docker method
docker run -d \
  --name streamr-node \
  -p 8080:8080 \
  -e COORDINATOR_URL=http://YOUR_PUBLIC_IP:8000 \
  -e STREAM_ID=test_stream_001 \
  -e NODE_ID=friend_$(whoami)_$(date +%s) \
  streamr/node-client:latest

# Or Python method
git clone https://github.com/your-username/streamr.git
cd streamr/node-client
python3 test_local_node.py
```

---

## 🔍 Part 3: Monitoring Remote Testing

### Host Monitoring Commands

```bash
# Watch active nodes join your stream
watch -n 5 'curl -s http://localhost:8000/dashboard | jq'

# Monitor earnings calculations
curl http://localhost:8000/payouts?hours_back=1 | jq

# Check node validation activity  
cd coordinator && docker-compose logs --tail 20 worker

# Monitor RTMP server performance
docker logs streamr-ingest --tail 10
```

### Network Performance Testing

```bash
# Test connectivity from host to friends
# (Friends should run this and share results)
curl -w "Total time: %{time_total}s\n" http://YOUR_PUBLIC_IP:8000/health

# Check bandwidth usage
# Monitor your router's traffic graphs during streaming
```

### Debugging Connection Issues

```bash
# Common issues and fixes:

# 1. Friend can't connect to coordinator
curl http://YOUR_PUBLIC_IP:8000/health
# If fails: Check router port forwarding for port 8000

# 2. Node appears but disappears quickly  
cd coordinator && docker-compose logs worker | grep "stats collection error"
# Check if friend's port 8080 is accessible

# 3. High latency or disconnections
# Monitor router logs for connection drops
# Check friend's internet stability
```

---

## 📊 Part 4: Success Metrics for Remote Testing

### Phase 2A Goals (3-5 Friends)
- [ ] **External Connectivity**: Friends connect from different networks
- [ ] **Multi-Node Stability**: 3+ nodes stay connected for 30+ minutes  
- [ ] **Geographic Distribution**: Test nodes from different cities/regions
- [ ] **Performance Validation**: <2 second heartbeat response times
- [ ] **Earnings Distribution**: Accurate payouts across multiple nodes

### Phase 2B Goals (5-10 Friends)  
- [ ] **Load Testing**: Handle 10+ concurrent nodes
- [ ] **Fraud Detection**: Validate spot-check system at scale
- [ ] **Network Resilience**: Handle nodes joining/leaving dynamically
- [ ] **Mobile Testing**: Friends connect from mobile hotspots
- [ ] **International Testing**: Test across different countries

---

## ⚠️ Troubleshooting Common Issues

### 🔥 "Connection Refused" Errors
**Problem**: Friends can't reach `http://YOUR_PUBLIC_IP:8000`
**Solutions**:
1. Check router port forwarding configuration
2. Verify Windows Firewall allows port 8000
3. Test from external network (mobile hotspot)
4. Check if ISP blocks incoming connections

### 🔥 "Node Disappears from Dashboard"
**Problem**: Node connects but shows as offline quickly
**Solutions**:
1. Check friend's port 8080 accessibility: `curl http://FRIEND_IP:8080/stats.json`
2. Verify friend's firewall allows incoming connections
3. Check friend's Docker container logs: `docker logs streamr-node`

### 🔥 "RTMP Stream Not Reaching Nodes"
**Problem**: Friends connect but don't relay stream properly
**Solutions**:
1. Verify RTMP port 1935 forwarding in router
2. Check SRS server logs: `docker logs streamr-ingest`
3. Test direct RTMP connection: `ffplay rtmp://YOUR_PUBLIC_IP:1935/live/test_stream_001`

### 🔥 "High Latency or Timeouts"
**Problem**: System works but very slow
**Solutions**:
1. Check your upload bandwidth (streaming + API traffic)
2. Monitor router CPU usage during testing
3. Reduce stream bitrate in OBS settings
4. Ask friends to test from wired connections

---

## 🎉 Remote Testing Success Checklist

**Ready for friends when you can:**
- ✅ **External health check works**: `curl http://YOUR_PUBLIC_IP:8000/health`
- ✅ **Dashboard accessible externally**: Friends can view your streams
- ✅ **RTMP port reachable**: External tools can connect to port 1935
- ✅ **Local system stable**: No service crashes during 1+ hour test

**Friends successfully connected when:**
- ✅ **They appear in dashboard**: Node shows up in `/dashboard`
- ✅ **Heartbeats working**: Node stays "active" for 5+ minutes
- ✅ **Earnings calculated**: Node shows in `/payouts` endpoint
- ✅ **Validation passes**: Worker can poll their stats endpoint

---

## 🚀 Next Steps After Remote Success

1. **Document network configurations** that worked best
2. **Collect friend feedback** on setup experience  
3. **Test with larger groups** (10+ friends)
4. **Implement mobile app** for easier friend onboarding
5. **Deploy to cloud infrastructure** for scale testing

**Ready to revolutionize streaming with P2P? Let's get your friends connected! 🌟** 