# 🤖 Agent Setup Prompt for StreamrP2P Friend Node

**Copy this entire prompt and send it to your AI assistant (Claude, ChatGPT, etc.)**

---

## 🎯 **Agent Instructions: Set Up StreamrP2P Friend Node**

Hi! My friend is streaming and I want to help support their stream by running a "restreaming node" that relays their content to other viewers. This helps distribute the load and I earn rewards for helping.

**Repository**: https://github.com/iddv/streamr  
**Stream Key**: `[FRIEND_WILL_GIVE_YOU_THIS]`  
**Goal**: Set up a Docker container that relays my friend's stream

### **What I need you to do:**

1. **Check Prerequisites**:
   - Verify Docker is installed and running on my system
   - If not installed, guide me through Docker installation for my OS

2. **Clone and Setup**:
   - Clone the StreamrP2P repository
   - Navigate to the correct directory
   - Run the friend node setup script with the stream key my friend gave me

3. **Verify It's Working**:
   - Check that the Docker container started successfully
   - Test that my relay is working
   - Give me the URL I should share with others to watch through my node

4. **Monitor and Troubleshoot**:
   - Show me how to check logs if something goes wrong
   - Help me verify my node is actually helping relay the stream
   - Guide me through any firewall or network issues

### **Expected Commands** (you should run these for me):

```bash
# Check Docker
docker --version
docker info

# Clone repository
git clone https://github.com/iddv/streamr.git
cd streamr

# Run setup (replace STREAM_KEY with what my friend gave me)
./setup-friend-node.sh STREAM_KEY

# Verify it's working
docker logs streamr-friend-node -f
curl http://localhost:8081/live/STREAM_KEY.m3u8

# Get my IP to share
curl ifconfig.me
```

### **What Success Looks Like**:
- Docker container named `streamr-friend-node` is running
- I can access `http://localhost:8081/live/STREAM_KEY.m3u8` and see stream data
- I have a shareable URL: `http://MY_IP:8081/live/STREAM_KEY.m3u8`
- My friend can see in their dashboard that I'm helping relay their stream

### **If Problems Occur**:
- Check Docker is running: `docker info`
- Check container status: `docker ps -a`
- View logs: `docker logs streamr-friend-node`
- Restart if needed: `docker stop streamr-friend-node && ./setup-friend-node.sh STREAM_KEY`

### **What to Tell Me**:
1. Confirm each step completed successfully
2. Give me the exact URL to share with viewers: `http://[MY_IP]:8081/live/[STREAM_KEY].m3u8`
3. Show me how to monitor my node's performance
4. Let me know if any firewall ports need to be opened (8081)

### **Important Notes**:
- This is a test/beta system - tokens aren't real money yet
- I'm helping my friend by relaying their stream to reduce their bandwidth costs
- The setup should take 5-10 minutes total
- If anything fails, show me the exact error messages

**Please start by checking if Docker is installed, then proceed with the setup!**

---

## 🎯 **Alternative: Super Simple Version**

If the above is too complex, here's a minimal version:

---

**Quick Agent Prompt:**

```
Help me set up a StreamrP2P friend node to support my friend's stream.

1. Clone: git clone https://github.com/iddv/streamr.git
2. Run: cd streamr && ./setup-friend-node.sh [STREAM_KEY]
3. Share: http://[MY_IP]:8081/live/[STREAM_KEY].m3u8

Make sure Docker is installed first. Check logs with: docker logs streamr-friend-node
```

---

## 📱 **Mobile/Discord Version**

For sharing in Discord/Slack:

```
🤖 Hey [AI Assistant]! Help me support my friend's stream:

Repo: https://github.com/iddv/streamr
Steps: Clone repo → run ./setup-friend-node.sh [STREAM_KEY] → share http://[MY_IP]:8081/live/[STREAM_KEY].m3u8

Need Docker installed. Should take 5 mins. Thx! 🚀
```

---

**Friends: Just copy any of these prompts and send to your AI assistant! 🤖✨** 