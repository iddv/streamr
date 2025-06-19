# 🤝 StreamrP2P Friend Node Setup Guide

**You've been invited to help support a friend's stream!**

**What you're doing**: Setting up a "restreaming node" that helps relay your friend's stream to other viewers. This reduces their bandwidth costs and you earn test rewards for helping! 🎉

**Time needed**: 5-10 minutes  
**What you need**: A computer with internet connection  

---

## ⚠️ **Platform Requirements & Important Notes**

### **🌐 Router Configuration Required**
**IMPORTANT**: Most home networks will require router setup for this to work:
- Your computer firewall allowing port 8081 ✅ (handled by scripts)
- Your router forwarding external traffic to your computer ❌ **(You may need to configure this)**

**What this means**: After setup, you'll need to test if your relay URL works from outside your network. If not, you'll need to configure "port forwarding" on your home router.

### **💻 Platform Support**
- **✅ Linux/macOS**: Full support with bash scripts
- **✅ Windows**: PowerShell scripts provided (requires Docker Desktop)  
- **❌ Mobile devices**: Not supported (requires Docker)

### **🔧 Technical Requirements**
- **Docker Desktop** installed and running
- **Admin/sudo access** for Docker installation
- **Stable internet** with decent upload speed (1-10 Mbps recommended)
- **Router access** (may be needed for port forwarding)

**💡 If these requirements seem daunting, consider asking a more technical friend to help with setup!**

---

## 🔒 **Security & Resource Impact**

### **Is This Safe?**
✅ **Yes, this is safe for testing:**
- Uses standard Docker containers (isolated from your system)
- Only opens port 8081 for streaming (standard media port)
- No personal data accessed or stored
- Open source code you can inspect: https://github.com/iddv/streamr

### **Resource Usage**
📊 **What this will use:**
- **Bandwidth**: ~1-5 Mbps upload per viewer watching through your node
- **CPU**: Minimal (similar to watching a video yourself)
- **RAM**: ~100-200MB (less than a browser tab)
- **Storage**: ~500MB for Docker container

💡 **Real impact**: If 10 people watch through your node, expect ~10-50 Mbps upload usage. Most home internet can handle this easily, but you can monitor and stop anytime.

### **Computer Requirements**
- Keep your computer on while your friend is streaming
- Stable internet connection (faster upload = better performance)
- If your IP changes, just restart the setup script

---

## 🤖 **EASIEST: Use Your AI Assistant (Recommended)**

**Most people in 2025 will just use an AI agent for this!**

### **Step 1: Get Your Stream Key**
Your friend should have given you a **stream key** (like `obs-test` or `friend-test-001`). If not, ask them for it!

### **Step 2: Copy This Improved Prompt**
Copy this entire message and send it to your AI assistant (Claude, ChatGPT, Cursor, etc.):

```
🤖 Guide me through setting up a StreamrP2P friend node. I'm on [macOS/Linux/Windows].

I need the exact terminal commands to copy-paste. Don't run them for me.

1. Check if Docker is installed and running. Test with the 'hello-world' container.
2. Clone the repo: https://github.com/iddv/streamr
3. Run the setup script with my stream key: [REPLACE_WITH_YOUR_FRIENDS_KEY]
4. Verify the node is running locally by checking Docker logs and making a web request
5. Find my public IP address and construct the final shareable URL for my friend

The final URL should be: http://[MY_PUBLIC_IP]:8081/live/[STREAM_KEY].m3u8
```

**Replace `[REPLACE_WITH_YOUR_FRIENDS_KEY]` with the actual stream key your friend gave you!**
**Replace `[macOS/Linux/Windows]` with your operating system!**

### **Step 3: Follow AI's Step-by-Step Commands**
Your AI assistant will give you commands to:
- Install Docker (if needed)
- Clone the repository  
- Run the setup script
- Check if it's working
- Find your public IP

### **Step 4: Share Your Relay URL**
Once setup is complete, you'll have a URL like:
```
http://123.456.789.0:8081/live/obs-test.m3u8
```

**Send this URL to your friend** - they can share it with viewers who want to watch through your node!

---

## 💻 **Manual Setup (If You Prefer DIY)**

### **Prerequisites**
- Docker installed and running
- Basic command line knowledge
- The stream key your friend gave you

### **🐧 Linux/macOS Setup**

### **Step 1: Install Docker (If Needed)**
```bash
# Check if Docker is installed
docker --version

# If not installed:
# macOS: Download from https://docs.docker.com/desktop/mac/install/
# Linux: sudo apt-get update && sudo apt-get install docker.io
```

### **Step 2: Clone the Repository**
```bash
git clone https://github.com/iddv/streamr.git
cd streamr
```

### **Step 3: Run Setup Script**
```bash
./setup-friend-node.sh YOUR_STREAM_KEY
```
*(Replace `YOUR_STREAM_KEY` with what your friend gave you)*

### **🪟 Windows Setup**

### **Step 1: Install Docker Desktop**
1. Go to: https://docs.docker.com/desktop/windows/install/
2. Download Docker Desktop for Windows
3. Install (requires admin rights and restart)
4. Start Docker Desktop and wait for it to fully load

### **Step 2: Download the Repository**
1. Go to: https://github.com/iddv/streamr
2. Click "Code" → "Download ZIP"
3. Extract the ZIP file to your Desktop
4. Open the extracted `streamr` folder

### **Step 3: Run PowerShell Setup**
1. Right-click on `setup-friend-node.ps1`
2. Choose "Run with PowerShell"
3. If you get a security warning, type `Y` and press Enter
4. Enter your stream key when prompted

**Alternative**: Open PowerShell as Administrator and run:
```powershell
cd Desktop\streamr
powershell -ExecutionPolicy Bypass -File setup-friend-node.ps1 YOUR_STREAM_KEY
```

### **Universal Steps (All Platforms)**

**What this script does:**
- Pulls the SRS (Simple Realtime Server) Docker image
- Configures it with your stream key
- Starts the container with port 8081 exposed
- Sets up relay from your friend's stream to your node

### **Step 4: Verify It's Working**
```bash
# Check your node is running
docker logs streamr-friend-node -f

# Test your relay locally
curl http://localhost:8081/live/YOUR_STREAM_KEY.m3u8

# Should return stream playlist data (not an error)
```

### **Step 5: Configure Firewall**
```bash
# Linux: Allow port 8081
sudo ufw allow 8081

# macOS: System Preferences > Security & Privacy > Firewall > Options
# Click "+" and add Docker, allow incoming connections

# Windows: Windows Defender Firewall > Allow an app
# Find Docker Desktop and allow both private and public networks
```

### **Step 6: Share Your Relay URL**
```bash
# Find your public IP address
curl ifconfig.me

# Share this with your friend
echo "My relay URL: http://$(curl -s ifconfig.me):8081/live/YOUR_STREAM_KEY.m3u8"
```

### **Step 7: Verify Public Access**
Before sharing your URL, make sure the outside world can reach your node:

1. Go to: https://canyouseeme.org
2. Enter port: `8081`
3. Click "Check Port"
4. **If SUCCESS**: You're ready! Share your URL with your friend
5. **If ERROR**: Double-check firewall settings or router port forwarding

**Router/Port Forwarding Issues (Most Common):**
This is the #1 reason setups fail. Even if your computer allows port 8081, your router might not forward external traffic.

**Quick Test:**
1. Go to: https://canyouseeme.org
2. Enter port: `8081`
3. Click "Check Port"

**If it shows ERROR, you need to configure your router:**

**Step 1: Find Your Router's Admin Page**
```bash
# Usually one of these addresses:
http://192.168.1.1
http://192.168.0.1
http://10.0.0.1

# Or check your default gateway:
# Windows: ipconfig | findstr "Default Gateway"
# Linux/Mac: ip route | grep default
```

**Step 2: Configure Port Forwarding**
1. Log into your router (username often "admin", password on router label)
2. Look for: "Port Forwarding", "Virtual Server", "NAT", or "Gaming"
3. Add a new rule:
   - **External Port**: 8081
   - **Internal Port**: 8081  
   - **Internal IP**: Your computer's local IP
   - **Protocol**: TCP (or Both)
4. Save and reboot router

**Step 3: Find Your Computer's Local IP**
```bash
# Windows: ipconfig | findstr "IPv4"
# Linux: ip addr show | grep "inet "
# macOS: ifconfig | grep "inet "
```

**Common Router Brands:**
- **Netgear**: Advanced → Dynamic DNS/Port Forwarding
- **Linksys**: Smart Wi-Fi Tools → Port Range Forwarding  
- **TP-Link**: Advanced → NAT Forwarding → Virtual Servers
- **ASUS**: Adaptive QoS → Traditional QoS → Port Forwarding

**If Router Setup Fails:**
- Contact your ISP (some block port forwarding)
- Try a different port (8082, 8083, etc.)
- Consider asking a tech-savvy friend for help

---

## ✅ **What Success Looks Like**

- ✅ Docker container starts successfully
- ✅ Logs show "SRS server started"  
- ✅ Your relay URL returns stream data (not 404 error)
- ✅ Your friend confirms you're helping relay their stream
- ✅ Viewers can watch through your node

### **How to Monitor Your Node**
```bash
# Check if anyone is using your relay
docker logs streamr-friend-node -f

# Monitor resource usage
docker stats streamr-friend-node

# Check bandwidth usage (Linux)
sudo iftop -i eth0
```

---

## 🔧 **Troubleshooting**

### **If Setup Fails**
```bash
# Stop and restart
docker stop streamr-friend-node
docker rm streamr-friend-node
./setup-friend-node.sh YOUR_STREAM_KEY
```

### **Common Issues & Solutions**

**"Permission denied" error:**
```bash
# Linux: Add your user to docker group
sudo usermod -aG docker $USER
# Then log out and log back in
```

**"Port already in use" error:**
```bash
# Check what's using port 8081
sudo lsof -i :8081
# Kill the process or use different port
```

**Firewall blocking connections:**
```bash
# Test if port is accessible from outside
# Ask a friend to visit: http://YOUR_IP:8081
# Should see SRS server page, not timeout
```

**Stream URL returns 404:**
```bash
# Check if your friend is actually streaming
# Verify stream key matches exactly
# Check container logs for errors
docker logs streamr-friend-node -f
```

---

## 🎯 **Your Role in the Test**

### **What You're Testing**
- How easy is it to set up a support node?
- Does the relay work reliably?
- Is the documentation clear?
- Would you do this to help a friend?

### **What to Expect**
- Your computer will relay your friend's stream
- Other viewers can watch through your node
- Your friend's dashboard will show you're helping
- You'll earn test rewards (not real money yet!)

### **What to Report Back**
- How long did setup take?
- What was confusing or unclear?
- Did you feel confident about what you were doing?
- Any error messages you encountered?
- How much bandwidth/CPU did it actually use?

---

## 📞 **Getting Help**

### **If You Get Stuck**
1. **Check the logs**: `docker logs streamr-friend-node -f`
2. **Try the troubleshooting steps** above
3. **Ask your friend** - they invited you to test!
4. **Check the main repo**: https://github.com/iddv/streamr

### **What to Report**
- What step failed?
- What error message did you see?
- What operating system are you using?
- Screenshot of the error (if applicable)

---

## 🎉 **After Setup**

### **You're Now Helping!**
- Your node is relaying your friend's stream
- Viewers watching through your relay reduce your friend's bandwidth costs
- You're earning test rewards for helping
- You're part of the future of decentralized streaming!

### **How to Monitor Usage**
```bash
# See real-time stats
docker stats streamr-friend-node

# Check who's connected
docker logs streamr-friend-node -f | grep "play"
```

### **How to Stop**
```bash
docker stop streamr-friend-node
docker rm streamr-friend-node
```

### **How to Restart**
```bash
./setup-friend-node.sh YOUR_STREAM_KEY
```

---

## 🔄 **Managing Your Node Over Time**

### **Updating Your Node**
```bash
# Get the latest version
docker pull ossrs/srs:5

# Restart with updated container
docker stop streamr-friend-node
docker rm streamr-friend-node
./setup-friend-node.sh YOUR_STREAM_KEY
```

### **Completely Removing Your Node**
```bash
# Easy way: Use the teardown script
./teardown-friend-node.sh

# Manual way (if you prefer):
docker stop streamr-friend-node
docker rm streamr-friend-node
docker rmi ossrs/srs:5  # Optional: saves disk space
cd .. && rm -rf streamr  # Optional: removes repository
```

### **Controlling Resource Usage**
Currently, your node will serve as many viewers as your internet can handle. **Future versions will include bandwidth limits.** For now, you can:

```bash
# Monitor current usage
docker stats streamr-friend-node

# If usage gets too high, temporarily stop
docker stop streamr-friend-node

# Restart when ready
docker start streamr-friend-node
```

---

## 🚨 **Current Limitations**

This is a test system, so:
- **Not true P2P yet**: Using simple relay, not full mesh network
- **Manual coordination**: You need to share your IP manually
- **Test rewards only**: Tokens aren't real money (yet!)
- **Basic monitoring**: Limited dashboards and stats
- **IP changes**: Need to restart if your public IP changes

**These will all be improved in future versions!**

---

## ❓ **Frequently Asked Questions**

**Q: Will this slow down my internet?**
A: Only if many people watch through your node. You can monitor usage and stop anytime.

**Q: Can I limit how much bandwidth I contribute?**
A: Not yet, but this is planned! Currently, your node will serve as many viewers as your internet can handle. You can monitor usage with `docker stats streamr-friend-node` and temporarily stop if needed.

**Q: Do I need to keep my computer on the whole time?**
A: Yes, while your friend is streaming and people are watching through your node.

**Q: What if my internet cuts out?**
A: The container will restart automatically when your connection returns.

**Q: What if my public IP address changes?**
A: Most home internet connections have dynamic IPs that can change periodically. If this happens, the URL you shared with your friend will stop working. You'll need to find your new public IP (`curl ifconfig.me`) and send an updated URL. For this test, we'll handle this manually if it comes up!

**Q: Can I run multiple friend nodes?**
A: Not yet with this script, but you can help multiple friends by restarting with different keys.

**Q: Is this actually helping my friend?**
A: Yes! Every viewer watching through your node instead of directly reduces their bandwidth costs.

**Q: How do I know if people are using my node?**
A: Check the logs: `docker logs streamr-friend-node -f | grep "play"` - you'll see connections when viewers start watching.

**Q: I'm getting "Cannot connect to the Docker daemon" error?**
A: This usually means Docker isn't running. Make sure you've started Docker Desktop (Mac/Windows) or that the Docker service is active (Linux: `sudo systemctl start docker`).

**Q: On Linux, I get "permission denied" when running Docker commands?**
A: Your user needs to be in the `docker` group. Run: `sudo usermod -aG docker $USER` then log out and back in. Or prefix commands with `sudo`.

**Q: Does this work on Windows?**
A: Yes! Use the PowerShell script (`setup-friend-node.ps1`) instead of the bash script. You'll need Docker Desktop installed first.

**Q: Do I really need to configure my router?**
A: Most likely, yes. Home routers use NAT and don't automatically forward incoming traffic. The good news: this is a one-time setup, and the scripts guide you through testing and configuration.

**Q: My ISP blocks port forwarding - what can I do?**
A: Some ISPs (especially mobile/cellular) block this. Try a different port (8082, 8083) or contact your ISP. As a last resort, you might need a VPN with port forwarding support.

**Q: This seems too technical - is there an easier way?**
A: For this test phase, this is the simplest we can make it. Future versions will have GUI applications and automatic router configuration. For now, consider asking a tech-savvy friend to help with the initial setup!

---

**Thanks for helping test StreamrP2P! You're supporting the future of decentralized streaming! 🚀**

*Questions? Ask your friend who invited you to test!* 