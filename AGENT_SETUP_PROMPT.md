# 🤖 Agent Setup Prompt for Your Friend

**Copy this entire message and send it to Claude/ChatGPT/Cursor:**

---

## 🚀 StreamrP2P Friend Node Setup

My friend is running a P2P streaming platform and asked me to help test it by running a "friend node" that relays their stream. Please help me set this up step by step.

**Repository**: https://github.com/iddv/streamr  
**Stream Key**: `obs-test`  
**My OS**: [Windows/Mac/Linux - REPLACE WITH YOUR OS]

### What I need you to do:

1. **Check Prerequisites**: Verify Docker is installed (`docker --version`)
2. **Clone Repository**: Clone the StreamrP2P repository
3. **Run Setup Script**: Execute the friend node setup with stream key `obs-test`
4. **Verify Local Access**: Test that my relay works locally
5. **Find Public IP**: Get my public IP address for sharing
6. **Test External Access**: Guide me through router/firewall setup if needed
7. **Show Final URL**: Give me the exact URL to share with my friend

### Expected final result:
- Docker container `streamr-friend-node` running successfully
- Local test URL working: `http://localhost:8081/live/obs-test.m3u8`
- Shareable URL: `http://[MY_PUBLIC_IP]:8081/live/obs-test.m3u8`
- Router configured to forward port 8081 (if needed)

### What success looks like:
```
✅ Friend node started successfully!
📊 Your Node Status:
  Node ID: friend_[username]_[timestamp]
  HLS Output: http://localhost:8081/live/obs-test.m3u8
🌐 Your public IP: [DETECTED_IP]
📋 Your relay URL: http://[PUBLIC_IP]:8081/live/obs-test.m3u8
```

### Please guide me through:
- Docker installation (if not installed)
- Repository cloning and script execution
- Local testing to verify the relay works
- Router port forwarding setup (if external access fails)
- Troubleshooting any Docker or network issues

**Start by checking if Docker is installed, then proceed step by step!**

---

## 🎯 Alternative Ultra-Simple Version

If the above is too detailed, here's a minimal version:

```
Help me set up a StreamrP2P friend node:

1. Check Docker installed
2. git clone https://github.com/iddv/streamr.git
3. cd streamr  
4. ./scripts/setup-friend-node.sh obs-test
5. Get my public IP and construct shareable URL
6. Test external access works

Final goal: http://[MY_IP]:8081/live/obs-test.m3u8
``` 