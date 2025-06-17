# 🎥 Streaming Setup Clarification

## 🤔 Your Questions Answered

### Q: Is the streaming client the same as the friend server for restreaming?

**No, they are different components:**

### 📡 **Streaming Client (You)**
- **What**: OBS Studio or similar streaming software
- **Purpose**: Creates the original video stream
- **Runs on**: Your PC (the host)
- **Streams to**: Central ingest server (`rtmp://localhost:1935/live`)
- **Stream key**: `test_stream_001`

### 📦 **Restreaming Nodes (Friends)**
- **What**: Docker containers running `rtmp_relay` + Python wrapper
- **Purpose**: Relay/redistribute your stream to viewers
- **Runs on**: Friends' computers
- **Gets stream from**: Central ingest server
- **Provides stream to**: End viewers (simulated in PoC)

## 🏗️ Complete Architecture

```
Your Setup:                    Friends' Setup:              End Users:
┌─────────────────┐           ┌─────────────────┐          ┌─────────────────┐
│ 🎥 OBS Studio   │──RTMP──→  │ 📦 Node Client  │──RTMP──→ │ 📱 Viewers      │
│ (Streaming)     │           │ (Restreaming)   │          │ (Future)        │
│                 │           │                 │          │                 │
│ 🏗️ Coordinator  │←─Stats──  │ 📊 Stats Report │          │                 │
│ 📡 Ingest       │           │ 💰 Earn Tokens  │          │                 │
└─────────────────┘           └─────────────────┘          └─────────────────┘
```

## 🎯 What Each Component Does

### Your PC (Host):
1. **OBS Studio**: Creates the video stream
2. **Ingest Server**: Receives your OBS stream
3. **Coordinator**: Manages the network, tracks nodes, calculates rewards

### Friends' PCs (Nodes):
1. **Node Client**: Downloads your stream from ingest server
2. **Restreaming**: Makes the stream available for viewers
3. **Stats Reporting**: Reports performance to coordinator
4. **Earning Tokens**: Gets rewarded for good performance

## 📊 Minimum Testing Requirements

### ✅ **Absolute Minimum: 2 People Total**
- **You**: Host (OBS + Coordinator + Ingest)
- **1 Friend**: Node client for restreaming

**This tests:**
- ✅ Basic stream flow
- ✅ Node registration and heartbeat
- ✅ Stats collection
- ✅ Reward calculation
- ❌ Network effects (need more nodes)

### 🎯 **Recommended: 3-4 People Total**
- **You**: Host
- **2-3 Friends**: Node clients

**This tests:**
- ✅ All basic functionality
- ✅ Multiple node coordination
- ✅ Comparative performance tracking
- ✅ Leaderboard functionality
- ✅ Network resilience (nodes going up/down)

### 🚀 **Ideal: 5-6 People Total**
- **You**: Host
- **4-5 Friends**: Node clients

**This tests:**
- ✅ Everything above
- ✅ Fraud detection (can simulate fake nodes)
- ✅ Network scaling behavior
- ✅ Meaningful competition dynamics
- ✅ Resource usage patterns

## 🧪 Testing Scenarios by Group Size

### 2 People (You + 1 Friend)
```bash
# You run:
./start-host.sh

# Friend runs:
curl -sSL https://raw.githubusercontent.com/iddv/streamr/main/setup-node.sh | bash -s http://YOUR_IP:8000 test_stream_001

# Test: Basic functionality, single node rewards
```

### 3-4 People (You + 2-3 Friends)
```bash
# You run:
./start-host.sh

# Each friend runs (with unique node IDs):
curl -sSL https://raw.githubusercontent.com/iddv/streamr/main/setup-node.sh | bash -s http://YOUR_IP:8000 test_stream_001 friend1_node
curl -sSL https://raw.githubusercontent.com/iddv/streamr/main/setup-node.sh | bash -s http://YOUR_IP:8000 test_stream_001 friend2_node
curl -sSL https://raw.githubusercontent.com/iddv/streamr/main/setup-node.sh | bash -s http://YOUR_IP:8000 test_stream_001 friend3_node

# Test: Multi-node coordination, leaderboard, node churn
```

### 5-6 People (You + 4-5 Friends)
```bash
# Same as above, plus:
# - Have one friend simulate a "fake" node (modify stats URL)
# - Test fraud detection
# - Try stopping/starting nodes randomly
# - Monitor resource usage on all machines
```

## 🎮 What Friends Need to Know

### For Friends (Simple Version):
1. **You're helping test a streaming system**
2. **You'll run a small program that helps relay video**
3. **It's completely automated - just run one command**
4. **You'll "earn" fake tokens based on how well it works**
5. **It uses Docker, so it's safe and contained**

### Technical Requirements for Friends:
- **Docker installed** (that's it!)
- **Ports 1935 and 8080 available** (script handles conflicts)
- **Internet connection** to reach your coordinator
- **Basic terminal access** (or agent can do it)

## 🔍 What You'll Monitor

### Real-time Dashboard:
```bash
# See all active nodes
curl http://localhost:8000/dashboard | jq

# Check leaderboard
curl http://localhost:8000/leaderboard | jq

# View earnings
curl http://localhost:8000/payouts | jq
```

### Success Indicators:
- ✅ All friends appear in dashboard
- ✅ Stats are being collected every 60 seconds
- ✅ Spot-checks are running (check worker logs)
- ✅ Rewards are calculated proportionally
- ✅ System handles nodes going offline gracefully

## 🚨 Common Misconceptions

### ❌ **Wrong**: Friends need OBS or streaming software
### ✅ **Correct**: Only you need OBS. Friends just run the node client.

### ❌ **Wrong**: Friends need to configure streaming settings
### ✅ **Correct**: Friends just run one command. Everything is automatic.

### ❌ **Wrong**: You need many people to test basic functionality
### ✅ **Correct**: 2 people total (you + 1 friend) tests core functionality.

### ❌ **Wrong**: Friends are "viewers" of the stream
### ✅ **Correct**: Friends are "relay nodes" that help distribute the stream.

## 🎯 Quick Start Summary

1. **You**: Run `./start-host.sh` and start streaming in OBS
2. **Friends**: Run the one-liner command you give them
3. **Monitor**: Check dashboard to see everyone connected
4. **Test**: Let it run for 30+ minutes to see meaningful data

**Minimum viable test: Just you + 1 friend! 🚀** 