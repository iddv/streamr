# StreamrP2P Node Client

The Node Client for the "restreaming as support" Proof of Concept. This Docker container runs an RTMP relay that helps distribute live streams while earning token rewards.

## 🚀 Quick Start (Zero-Friction Setup)

### Prerequisites

- Docker installed on your machine
- Internet connection
- Available ports 1935 (RTMP) and 8080 (Stats)

### Step 1: Get the Stream ID

Contact the PoC coordinator to get:
- **Stream ID**: The stream you'll be relaying (e.g., `test_stream_001`)
- **Coordinator URL**: The coordination server URL (e.g., `http://coordinator.example.com:8000`)

### Step 2: Run the Node Client

**Option A: Using Docker Run (Simplest)**

```bash
docker run -d \
  --name streamr-node \
  -p 1935:1935 \
  -p 8080:8080 \
  -e STREAM_ID=test_stream_001 \
  -e COORDINATOR_URL=http://coordinator.example.com:8000 \
  streamr/node-client:latest
```

**Option B: Using Docker Compose (Recommended)**

1. Create a `docker-compose.yml` file:
```yaml
version: '3.8'
services:
  node-client:
    image: streamr/node-client:latest
    environment:
      - STREAM_ID=test_stream_001
      - COORDINATOR_URL=http://coordinator.example.com:8000
      - NODE_ID=my_unique_node_001
    ports:
      - "1935:1935"
      - "8080:8080"
    restart: unless-stopped
```

2. Start the node:
```bash
docker-compose up -d
```

### Step 3: Verify It's Working

Check the logs:
```bash
docker logs streamr-node
```

You should see:
```
✓ Node Client initialized
✓ Discovered public IP: 203.0.113.42
✓ Found stream: test_stream_001
✓ RTMP relay is running successfully
✓ Starting heartbeat loop
✓ Heartbeat sent successfully
```

Check your stats endpoint:
```bash
curl http://localhost:8080/stats.json
```

## 📊 Monitoring Your Node

### View Real-Time Logs
```bash
docker logs -f streamr-node
```

### Check Node Status
```bash
# Your local stats
curl http://localhost:8080/stats.json

# Your earnings (replace NODE_ID)
curl http://coordinator.example.com:8000/nodes/my_unique_node_001/earnings

# Global leaderboard
curl http://coordinator.example.com:8000/leaderboard
```

### Dashboard
Visit the coordinator dashboard: `http://coordinator.example.com:8000/dashboard`

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STREAM_ID` | ✅ | - | Stream to relay (provided by coordinator) |
| `COORDINATOR_URL` | ✅ | - | Coordinator server URL |
| `NODE_ID` | ❌ | `node_<random>` | Unique identifier for your node |
| `RTMP_PORT` | ❌ | `1935` | RTMP relay port |
| `STATS_PORT` | ❌ | `8080` | Stats/monitoring port |
| `HEARTBEAT_INTERVAL` | ❌ | `30` | Heartbeat frequency (seconds) |

### Example Configurations

**Basic Setup:**
```bash
docker run -d \
  -p 1935:1935 -p 8080:8080 \
  -e STREAM_ID=test_stream_001 \
  -e COORDINATOR_URL=http://coordinator.example.com:8000 \
  streamr/node-client:latest
```

**Custom Node ID:**
```bash
docker run -d \
  -p 1935:1935 -p 8080:8080 \
  -e STREAM_ID=test_stream_001 \
  -e COORDINATOR_URL=http://coordinator.example.com:8000 \
  -e NODE_ID=alice_gaming_rig \
  streamr/node-client:latest
```

**Custom Ports:**
```bash
docker run -d \
  -p 1936:1936 -p 8081:8081 \
  -e STREAM_ID=test_stream_001 \
  -e COORDINATOR_URL=http://coordinator.example.com:8000 \
  -e RTMP_PORT=1936 \
  -e STATS_PORT=8081 \
  streamr/node-client:latest
```

## 🔧 Troubleshooting

### Common Issues

**1. "Stream not found in coordinator"**
- Verify the `STREAM_ID` is correct
- Check that the coordinator is running and accessible

**2. "Failed to discover public IP"**
- Node will fallback to localhost (127.0.0.1)
- This is fine for local testing but may affect rewards in production

**3. "RTMP relay failed to start"**
- Check if ports 1935/8080 are already in use
- Try different ports using `RTMP_PORT` and `STATS_PORT`

**4. "Heartbeat failed"**
- Verify `COORDINATOR_URL` is correct and accessible
- Check network connectivity

### Debug Commands

**Check if ports are available:**
```bash
# Check if port 1935 is free
netstat -ln | grep 1935

# Check if port 8080 is free  
netstat -ln | grep 8080
```

**Test coordinator connectivity:**
```bash
curl http://coordinator.example.com:8000/health
```

**View detailed logs:**
```bash
docker logs streamr-node 2>&1 | grep -E "(ERROR|WARN|✓|✗)"
```

## 💰 Earning Rewards

### How Rewards Work

1. **Uptime**: Your node earns based on how reliably it relays the stream
2. **Quality**: The coordinator verifies your node is actually working
3. **Anti-Fraud**: Random spot-checks ensure you're not cheating
4. **Pool Distribution**: Rewards are shared among all active nodes

### Maximizing Earnings

- **Keep your node running 24/7**
- **Ensure stable internet connection**
- **Monitor logs for any errors**
- **Don't try to game the system** (spot-checks will catch fraud)

### Checking Earnings

```bash
# Replace with your actual node ID
curl http://coordinator.example.com:8000/nodes/my_unique_node_001/earnings
```

## 🛑 Stopping Your Node

```bash
# If using docker run
docker stop streamr-node
docker rm streamr-node

# If using docker-compose
docker-compose down
```

## 🏗️ Building from Source

If you want to build the Docker image yourself:

```bash
git clone https://github.com/your-repo/streamr-poc
cd streamr-poc/node-client
docker build -t my-streamr-node .
```

## 📞 Support

- **Issues**: Report problems in the GitHub repository
- **Discord**: Join the StreamrP2P testing channel
- **Logs**: Always include logs when reporting issues

## ⚠️ Important Notes

- This is a **Proof of Concept** - tokens are not real
- Keep your node running to maximize rewards
- The system detects and penalizes fraud attempts
- Your public IP will be visible to the coordinator
- Ensure you have sufficient bandwidth for relaying streams

---

**Ready to start earning? Run the Quick Start commands above! 🚀** 