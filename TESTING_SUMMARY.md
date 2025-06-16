# 🧪 StreamrP2P Local Testing - Ready to Go!

Your "restreaming as support" PoC is ready for local testing! Here's everything you need to know.

## 🎯 What We Built

A complete **hybrid verification system** for decentralized content delivery:

- **📡 Central Ingest Server**: Receives your OBS stream
- **🏗️ Coordinator Server**: Manages nodes, tracks performance, calculates rewards
- **📦 Node Client**: Friends run this to relay your stream and earn tokens
- **🔍 Verification System**: Stats polling + random spot-checks to prevent fraud
- **💰 Reward System**: Automatic payouts based on uptime and honesty

## 🚀 Quick Start (3 Steps)

### Step 1: Setup Your PC as Host
```bash
./start-host.sh
```
This starts the coordinator and ingest server on your PC.

### Step 2: Start Streaming in OBS
- Server: `rtmp://localhost:1935/live`
- Stream Key: `test_stream_001`

### Step 3: Invite Friends
Send them this one-liner (replace with your actual IP):
```bash
curl -sSL https://raw.githubusercontent.com/your-username/streamr/main/setup-node.sh | bash -s http://YOUR_IP:8000 test_stream_001
```

**That's it!** 🎉

---

## 📁 File Guide

### 🏠 For You (Host)
- **`start-host.sh`** - One-command setup for your PC
- **`LOCAL_TESTING_GUIDE.md`** - Detailed manual setup instructions

### 👥 For Friends
- **`setup-node.sh`** - One-command node setup (agent-friendly)
- **`FRIEND_SETUP.md`** - Multiple setup options for friends

### 📊 Monitoring
- Dashboard: `http://localhost:8000/dashboard`
- Leaderboard: `http://localhost:8000/leaderboard`
- Payouts: `http://localhost:8000/payouts`

---

## 🤖 Agent-Friendly Features

Both setup scripts are designed to work perfectly with AI agents:

### For Host Setup:
```bash
# Agent can run this to set up the coordinator
./start-host.sh
```

### For Friend Setup:
```bash
# Agent can run this to join the network
./setup-node.sh http://COORDINATOR_IP:8000 test_stream_001 agent_node_$(date +%s)
```

**Key Agent Benefits:**
- ✅ Clear success/failure feedback
- ✅ Automatic port conflict resolution
- ✅ Connectivity testing before setup
- ✅ Detailed error messages with solutions
- ✅ No user interaction required

---

## 🔍 What Gets Tested

### ✅ Core Economic Loop
1. **Stream Registration**: Your stream gets registered in the coordinator
2. **Node Discovery**: Friends discover your stream automatically
3. **Performance Tracking**: System monitors each node's uptime and stats
4. **Fraud Detection**: Random spot-checks catch dishonest nodes
5. **Reward Distribution**: Honest nodes earn tokens, fraudsters get zero

### ✅ Technical Verification
- **Stats Polling**: Every 60s, coordinator checks each node's `/stats.json`
- **Spot-Check Probing**: Random RTMP connection tests using ffprobe
- **Uptime Tracking**: Continuous monitoring of node availability
- **Fraud Flagging**: Automatic detection and penalization of fake nodes

### ✅ Social Dynamics
- **Leaderboard**: Public ranking of top-performing nodes
- **Earnings Transparency**: Anyone can check node earnings
- **Community Building**: Friends compete for highest uptime

---

## 📊 Success Metrics

**You'll know it's working when:**

1. **Dashboard shows active nodes**:
   ```bash
   curl localhost:8000/dashboard | jq
   ```

2. **Friends appear in leaderboard**:
   ```bash
   curl localhost:8000/leaderboard | jq
   ```

3. **Payouts are calculated correctly**:
   ```bash
   curl localhost:8000/payouts | jq
   ```

4. **Fraud detection catches cheaters**:
   ```bash
   # Check worker logs for spot-check results
   docker-compose -f coordinator/docker-compose.yml logs worker
   ```

---

## 🎮 Testing Scenarios

### Scenario 1: Happy Path
1. Start your host setup
2. Begin streaming in OBS
3. 3-5 friends join with the setup script
4. Monitor dashboard to see all nodes active
5. Check leaderboard after 30 minutes

### Scenario 2: Fraud Detection
1. Have a friend run a "fake" node (modify stats URL to invalid)
2. Watch worker logs to see fraud detection in action
3. Verify fraudulent node gets zero payout

### Scenario 3: Network Resilience
1. Have friends randomly stop/start their nodes
2. Verify system handles node churn gracefully
3. Check that only active nodes get rewards

---

## 🚨 Common Issues & Solutions

### "Cannot reach coordinator"
- **Check firewall**: Ensure port 8000 is open
- **Verify IP**: Use `curl -s https://api.ipify.org` to get your public IP
- **Test locally**: `curl http://localhost:8000/health`

### "RTMP connection failed"
- **Check OBS settings**: Server should be `rtmp://localhost:1935/live`
- **Verify ingest server**: `curl http://localhost:8081/stats.json`
- **Check ports**: Ensure 1935 and 1936 are available

### "No nodes in dashboard"
- **Verify friend setup**: Check their node logs with `docker logs streamr-node`
- **Test connectivity**: Friends should be able to reach `http://YOUR_IP:8000/health`
- **Check stream registration**: `curl localhost:8000/streams`

---

## 💡 Pro Tips

### For Maximum Testing Value:
1. **Run for 2-4 hours** to see meaningful reward calculations
2. **Have friends in different locations** to test network diversity
3. **Try stopping/starting nodes** to test resilience
4. **Monitor logs actively** to catch any issues early
5. **Document any bugs** for fixing before cloud deployment

### For Agent Testing:
1. **Use the setup scripts** - they're designed for automation
2. **Monitor return codes** - scripts exit with proper error codes
3. **Parse JSON responses** - all API endpoints return structured data
4. **Check logs programmatically** - `docker logs` provides structured output

---

## 🎯 Next Steps After Testing

Once local testing is successful:

### Phase 1: Document Results
- [ ] Record performance metrics
- [ ] Note any bugs or issues
- [ ] Collect friend feedback
- [ ] Measure resource usage

### Phase 2: Cloud Deployment (Epic 3)
- [ ] Deploy coordinator to cloud server
- [ ] Setup central ingest server
- [ ] Create public documentation
- [ ] Launch alpha test with larger group

### Phase 3: Scale & Iterate
- [ ] Add more verification mechanisms
- [ ] Implement token economics
- [ ] Build web dashboard
- [ ] Integrate with Streamr Network

---

## 🎉 Ready to Test!

**Everything is set up and ready to go!**

1. **Run `./start-host.sh`** to set up your PC
2. **Start streaming in OBS**
3. **Share `FRIEND_SETUP.md`** with your friends
4. **Monitor the dashboard** to watch your network grow
5. **Document everything** for the next phase

**The future of decentralized streaming starts with your test! 🚀**

---

## 📞 Need Help?

- **Check logs**: All services provide detailed logging
- **Test connectivity**: Use the built-in health checks
- **Review documentation**: `LOCAL_TESTING_GUIDE.md` has full details
- **Monitor dashboard**: Real-time view of system status

**Happy testing! 🎮** 