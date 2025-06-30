# 🚀 StreamrP2P Friend Testing Instructions

> **Quick Start**: Your friend can join your streaming network in under 2 minutes!

## 📋 **What Your Friend Needs:**
- Any computer (Windows, Mac, or Linux)
- Docker installed
- Internet connection
- 5 minutes of time

---

## 🎯 **Option 1: Full P2P Node (Recommended)**

**For real StreamrP2P testing with earnings tracking:**

### Linux/Mac:
```bash
cd streamr
./scripts/setup-node.sh
```

### Windows:
```powershell
cd streamr
powershell -ExecutionPolicy Bypass -File scripts\setup-node.sh
```

**What this does:**
- ✅ Connects to live coordinator: `streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com`
- ✅ Uses real StreamrP2P node client with lifecycle management
- ✅ Automatically discovers LIVE streams ready for P2P support
- ✅ Tracks earnings and performance in real-time
- ✅ Shows up in dashboard and leaderboard
- ✅ Supports the `iddv-stream` when it's LIVE

---

## 🎯 **Option 2: Simple Setup (Basic Testing)**

**For quick relay testing without full P2P features:**

### Linux/Mac:
```bash
cd streamr
./scripts/setup-friend-node.sh obs-test
```

### Windows:
```powershell
cd streamr
powershell -ExecutionPolicy Bypass -File scripts\setup-friend-node.ps1
```

---

## 📊 **What Your Friend Will See:**

After running either script, they can check:

```bash
# See their node in the dashboard
curl http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com/dashboard

# Check their earnings
curl http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com/nodes/[NODE_ID]/earnings

# View the leaderboard
curl http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com/leaderboard
```

**Or visit the web dashboard:**
http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com/dashboard

---

## 🧹 **Cleanup When Done:**

```bash
# Stop the node
docker stop streamr-node  # (or streamr-friend-node for Option 2)

# Complete cleanup
./scripts/teardown-friend-node.sh
```

---

## 🎬 **Testing the Complete Flow:**

1. **Friend runs setup script** (2 minutes)
2. **You start streaming** via OBS to `rtmp://108.129.47.155:1935/live/obs-test`
3. **Both watch together** via VLC: `http://108.129.47.155:8080/live/obs-test.flv`
4. **Check the magic**: Friend sees their node helping in the dashboard!

---

## 🚨 **Troubleshooting:**

**"Cannot reach coordinator"**
- Check internet connection
- Try: `curl http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com/health`

**"Docker not found"**
- Install Docker Desktop: https://www.docker.com/products/docker-desktop

**"Ports in use"**
- The scripts auto-detect and use alternative ports

**"Stream not found"**
- Make sure you're streaming to `obs-test` stream key

---

## 🎉 **Success Indicators:**

Your friend's setup worked if they see:
- ✅ "Node started successfully!" message
- ✅ Their node ID in the coordinator dashboard
- ✅ Earnings tracking showing their contribution
- ✅ Their position in the leaderboard

**Ready to test with friends? Share this file!** 🚀 