# 🚀 Join the StreamrP2P Test Network

Help test the "restreaming as support" system and earn (fake) tokens!

## 🎯 What You're Doing

You're running a node that helps relay live streams. The more reliable your node, the more tokens you earn. It's completely automated - just start it and let it run!

---

## ⚡ Option 1: One-Command Setup (Easiest)

**Just run this command** (replace `YOUR_FRIEND_IP` with the actual IP):

```bash
curl -sSL https://raw.githubusercontent.com/iddv/streamr/main/setup-node.sh | bash -s http://YOUR_FRIEND_IP:8000 test_stream_001
```

**Or download and run:**

```bash
wget https://raw.githubusercontent.com/iddv/streamr/main/setup-node.sh
chmod +x setup-node.sh
./setup-node.sh http://YOUR_FRIEND_IP:8000 test_stream_001
```

---

## 🐳 Option 2: Direct Docker (Simple)

```bash
docker run -d \
  --name streamr-node \
  -p 1935:1935 \
  -p 8080:8080 \
  -e STREAM_ID=test_stream_001 \
  -e COORDINATOR_URL=http://YOUR_FRIEND_IP:8000 \
  -e NODE_ID=friend_$(whoami)_$(date +%s) \
  streamr/node-client:latest

# Check if it's working
docker logs streamr-node -f
```

---

## 📁 Option 3: GitHub Clone (For Developers)

```bash
# Clone the repo
git clone https://github.com/iddv/streamr.git
cd streamr

# Run the setup script
./setup-node.sh http://YOUR_FRIEND_IP:8000 test_stream_001

# Or use docker-compose
cd node-client
export COORDINATOR_URL="http://YOUR_FRIEND_IP:8000"
export STREAM_ID="test_stream_001"
docker-compose up -d
```

---

## 🔍 Verify It's Working

After setup, you should see:
```
✅ Node started successfully!
🎉 Your node is now part of the StreamrP2P network!
💰 You'll start earning rewards based on your uptime and performance.
```

**Check your status:**
```bash
# View logs
docker logs streamr-node -f

# Check your stats
curl http://localhost:8080/stats.json

# See your earnings (replace NODE_ID)
curl http://YOUR_FRIEND_IP:8000/nodes/YOUR_NODE_ID/earnings

# View leaderboard
curl http://YOUR_FRIEND_IP:8000/leaderboard
```

---

## 🎮 For AI Agents

If you're an AI agent setting this up:

1. **Ensure Docker is installed** on the target system
2. **Use Option 1** (the setup script) - it handles everything automatically
3. **Monitor the logs** to ensure successful startup
4. **Report the Node ID** back to the user for tracking

**Agent-friendly command:**
```bash
# This command is fully automated and provides clear success/failure feedback
curl -sSL https://raw.githubusercontent.com/iddv/streamr/main/setup-node.sh | bash -s http://COORDINATOR_IP:8000 test_stream_001 agent_node_$(date +%s)
```

---

## 🛑 Stop Your Node

```bash
docker stop streamr-node
docker rm streamr-node
```

---

## 🆘 Troubleshooting

**"Cannot reach coordinator"**
- Check the IP address is correct
- Make sure the host's firewall allows port 8000

**"Port already in use"**
- The setup script automatically finds alternative ports
- Or manually specify: `docker run -p 1937:1935 -p 8082:8080 ...`

**"Docker not found"**
- Install Docker: https://docs.docker.com/get-docker/

**Need help?**
- Check logs: `docker logs streamr-node`
- Contact the test coordinator

---

## 💰 Earning Rewards

- **Keep your node running 24/7** for maximum rewards
- **Don't try to cheat** - the system detects fraud
- **Monitor your earnings** via the leaderboard
- **Higher uptime = higher rewards**

**Ready to start earning? Pick an option above and run it! 🚀** 