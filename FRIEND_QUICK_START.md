# 🚀 Quick Start: Help Your Friend Stream!

**Hey! Your friend invited you to test their P2P streaming platform. You'll help relay their stream and earn test rewards!**

⏱️ **Time needed**: 5-10 minutes  
🛠️ **What you need**: Docker installed  
💰 **Rewards**: Fake tokens based on how well you help!  

---

## ✅ **Current Status (Updated January 2025)**

🎉 **Good news! The streaming infrastructure is now working:**
- ✅ **RTMP Streaming**: Live and working at `rtmp://52.213.32.59:1935/live`
- ✅ **Dashboard**: Real-time monitoring at the URL below
- ✅ **Friend Nodes**: Setup scripts tested and working
- ✅ **Stream Playback**: HLS streaming confirmed working

**What this means for you**: The setup should work smoothly! If you encounter issues, it's likely router/firewall configuration (which we'll help you fix).

---

## 🎉 **NEW: Single Binary Option (Easiest!)**

**Skip Docker entirely - just download and run one file:**

1. **Download** for your OS: [Latest Release](https://github.com/iddv/streamr/releases/latest)
2. **Run it**: 
   - **Windows**: Double-click `streamr-node-windows-amd64.exe`
   - **Mac**: `./streamr-node-macos-intel` (or `-m1` for Apple Silicon)
   - **Linux**: `./streamr-node-linux-amd64`

**Benefits:**
- ✅ **5MB binary** vs 200MB+ Docker setup
- ✅ **Instant startup** - no waiting for Docker
- ✅ **No installation** - just download and run
- ✅ **Works everywhere** - Windows, Mac, Linux native

*Note: This is the new Phase 0 foundation - RTMP streaming coming soon!*

---

## 🎯 **Docker Setup (Classic Method)**

### **Copy-Paste This Into Your Terminal:**

**Linux/Mac:**
```bash
git clone https://github.com/iddv/streamr.git
cd streamr
./scripts/setup-friend-node.sh obs-test
```

**Windows (PowerShell as Admin):**
```powershell
git clone https://github.com/iddv/streamr.git
cd streamr
powershell -ExecutionPolicy Bypass -File scripts\setup-friend-node.ps1 obs-test
```

---

## 🤖 **Even Easier: Ask Your AI Assistant**

**Copy this entire message and send to Claude/ChatGPT/Cursor:**

```
Help me set up a StreamrP2P friend node to support my friend's stream.

1. Clone: git clone https://github.com/iddv/streamr.git
2. Navigate: cd streamr
3. Run setup: ./scripts/setup-friend-node.sh obs-test
4. Check Docker is installed first
5. Help me get my public IP address and construct the final shareable URL

The final URL should be: http://[MY_PUBLIC_IP]:8081/live/obs-test.m3u8

Make sure to test the setup works locally before giving me the shareable URL.
```

---

## ✅ **What Success Looks Like**

After setup, you should see:
```
✅ Friend node started successfully!
📊 Your Node Status:
  Node ID: friend_yourname_123456789
  HLS Output: http://localhost:8081/live/obs-test.m3u8
  
🌐 Your public IP: 123.456.789.0
📋 Your relay URL: http://123.456.789.0:8081/live/obs-test.m3u8
```

**Send that relay URL to your friend!** 🎉

### **📋 Final Step: Get Your Public IP**

**The setup script will help, but you can also:**
```bash
# Get your public IP
curl ifconfig.me

# Your shareable URL will be:
echo "http://$(curl -s ifconfig.me):8081/live/YOUR_STREAM_KEY.m3u8"
```

---

## 📊 **See Yourself In The Dashboard**

**Check the live dashboard:** http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com/economic-dashboard

You should see:
- ✅ Your node in "Active Sessions" 
- ✅ Your earnings updating in real-time
- ✅ Your position in the leaderboard
- ✅ Trust score and performance metrics

---

## 🚨 **Router Setup (Most Important!)**

**99% chance you'll need this:**

1. **Test if your relay is public:** Go to https://canyouseeme.org
2. **Enter port:** `8081`
3. **Click "Check Port"**
4. **If ERROR:** You need to configure your router:
   - Open router admin (usually 192.168.1.1 or 192.168.0.1)
   - Find "Port Forwarding" or "Virtual Server"
   - Forward port 8081 to your computer's local IP
   - Save and restart router

**If router setup fails:** Contact your ISP or ask a tech friend for help!

---

## 🎮 **What You're Actually Doing**

- **You're not a viewer** - you're a **relay node**
- **Your computer** downloads your friend's stream
- **Your computer** re-serves it to actual viewers
- **You earn rewards** for bandwidth and reliability
- **Your friend saves money** on streaming costs
- **Everyone wins!** 🎉

---

## 🔧 **Monitor Your Node**

```bash
# See live activity
docker logs streamr-friend-node -f

# Check resource usage  
docker stats streamr-friend-node

# Stop your node (if needed)
docker stop streamr-friend-node
```

---

## 🆘 **If Something Goes Wrong**

**"Docker not found":**
- Install Docker Desktop: https://docs.docker.com/get-docker/

**"Permission denied":**
```bash
# Linux: Add yourself to docker group
sudo usermod -aG docker $USER
# Then log out and back in
```

**"Port already in use":**
```bash
# Check what's using port 8081
sudo lsof -i :8081
# Kill the process or restart your computer
```

**Still stuck?** Ask your friend - they invited you to test!

---

## 🎯 **The Big Picture**

You're testing the **future of streaming**:
- No more expensive CDNs
- Friends help friends stream  
- Everyone earns rewards for helping
- Decentralized, community-powered
- **You're a pioneer!** 🚀

---

## 🎉 **You're Done!**

Once your relay URL is working:
1. **Share it with your friend**
2. **Check the dashboard** to see your earnings
3. **Keep your computer on** while they're streaming
4. **Watch your rewards grow!** 💰

**Thanks for helping test the future of streaming!** ⭐

---

*Questions? Issues? Your friend who invited you can help debug!* 