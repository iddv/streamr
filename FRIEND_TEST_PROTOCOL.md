# 🧪 StreamrP2P Friend Test Protocol

**Test Date**: TBD  
**Test Type**: First External Friend Test  
**Participants**: 3 people (Streamer + 2 Friends)  
**Duration**: 1-2 hours  

---

## 🎯 **Test Objectives**

### **Primary Goals**
1. **Technical Validation**: Verify end-to-end streaming through friend's node works
2. **UX Validation**: Assess setup difficulty and user experience
3. **Value Validation**: Confirm participants see value in "restreaming as support"

### **Success Criteria**
- [ ] Friend 1 completes setup in under 15 minutes
- [ ] Friend 2 successfully watches stream through Friend 1's relay
- [ ] Stream quality is acceptable (minimal buffering/lag)
- [ ] All participants understand what they're doing and why

---

## 📋 **Pre-Test Checklist**

### **Infrastructure Ready**
- [ ] Coordinator API responding: http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com/health
- [ ] SRS streaming server running: rtmp://108.129.97.122:1935/live/
- [ ] Dashboard accessible: http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com/dashboard
- [ ] Setup scripts updated with correct endpoints

### **Documentation Ready**
- [ ] Friend setup guide is clear and complete
- [ ] Troubleshooting steps documented
- [ ] Test protocol reviewed

### **Participants Briefed**
- [ ] Friend 1 has Docker installed
- [ ] Friend 2 has VLC or compatible player
- [ ] Everyone understands the test purpose
- [ ] Backup communication channel established (Discord/Slack)

---

## 🚀 **Test Execution Steps**

### **Phase 1: Infrastructure Test (5 minutes)**
1. **Streamer starts stream**:
   ```bash
   # In OBS or streaming software
   RTMP URL: rtmp://108.129.97.122:1935/live/
   Stream Key: friend-test-001
   ```

2. **Verify stream is live**:
   - Check dashboard: Shows active stream
   - Direct playback: http://108.129.97.122:8080/live/friend-test-001.m3u8

### **Phase 2: Friend 1 Setup (10-15 minutes)**
1. **Send setup instructions** to Friend 1
2. **Friend 1 runs setup**:
   ```bash
   git clone https://github.com/your-repo/streamr.git
   cd streamr
   ./setup-friend-node.sh friend-test-001
   ```
3. **Verify Friend 1's node is working**:
   ```bash
   # Friend 1 checks their relay
   curl http://localhost:8081/live/friend-test-001.m3u8
   
   # Friend 1 shares their IP
   curl ifconfig.me
   ```

### **Phase 3: Friend 2 Viewing (5 minutes)**
1. **Friend 1 shares relay URL** with Friend 2:
   ```
   http://[Friend1-IP]:8081/live/friend-test-001.m3u8
   ```
2. **Friend 2 opens in VLC**:
   - Media → Open Network Stream
   - Paste URL and play
3. **Verify playback quality**:
   - Minimal lag compared to direct stream
   - No significant buffering
   - Audio/video sync maintained

### **Phase 4: Stress Test (10 minutes)**
1. **Test interruptions**:
   - Friend 1 restarts their node
   - Streamer briefly stops/starts stream
   - Test different network conditions
2. **Monitor recovery**:
   - How quickly does the relay recover?
   - Do viewers get disconnected?
   - Are error messages helpful?

---

## 📊 **Data Collection**

### **Technical Metrics**
- [ ] Setup time for Friend 1: _____ minutes
- [ ] Stream latency through relay: _____ seconds
- [ ] Buffering events: _____ times
- [ ] Connection drops: _____ times
- [ ] Error messages encountered: _____

### **User Experience Metrics**
- [ ] Friend 1 confidence level (1-10): _____
- [ ] Setup instruction clarity (1-10): _____
- [ ] Overall difficulty (1-10): _____
- [ ] Would do this to help a friend (Y/N): _____
- [ ] Understands the value proposition (Y/N): _____

### **Qualitative Feedback**
Record verbatim quotes for:
- What was confusing?
- What worked well?
- What would make this easier?
- How do you feel about the concept?
- Would you recommend this to others?

---

## 🐛 **Issue Tracking**

### **Setup Issues**
| Issue | Severity | Workaround | Fix Required |
|-------|----------|------------|--------------|
| | | | |

### **Streaming Issues**
| Issue | Severity | Impact | Fix Required |
|-------|----------|--------|--------------|
| | | | |

### **UX Issues**
| Issue | Severity | User Impact | Fix Required |
|-------|----------|-------------|--------------|
| | | | |

---

## 📝 **Post-Test Actions**

### **Immediate (Same Day)**
- [ ] Collect all feedback from participants
- [ ] Document critical issues that block adoption
- [ ] Create GitHub issues for bugs found
- [ ] Thank participants and share results

### **Short Term (1 Week)**
- [ ] Fix critical setup issues
- [ ] Improve documentation based on feedback
- [ ] Update setup scripts with lessons learned
- [ ] Plan next round of testing

### **Medium Term (1 Month)**
- [ ] Implement GUI wrapper if setup was too complex
- [ ] Add automatic IP discovery/sharing
- [ ] Improve error handling and recovery
- [ ] Build proper P2P mesh (vs simple relay)

---

## 🎯 **Success Scenarios**

### **Minimum Viable Success**
- Friend 1 gets their node running (even with help)
- Friend 2 can watch the stream through the relay
- Everyone understands the basic concept
- No major technical blockers identified

### **Good Success**
- Friend 1 completes setup independently in under 15 minutes
- Stream quality through relay is acceptable
- Participants are excited about the concept
- Only minor UX improvements needed

### **Excellent Success**
- Setup is intuitive and fast
- Stream quality is indistinguishable from direct
- Participants immediately see the value
- Friends volunteer to help with next tests

---

## 🚨 **Failure Scenarios & Responses**

### **Setup Fails Completely**
- **Response**: Switch to screen share and walk through setup
- **Learning**: Document every step that caused confusion
- **Next**: Simplify setup or build GUI wrapper

### **Stream Quality Unacceptable**
- **Response**: Investigate network/encoding issues
- **Learning**: Identify minimum bandwidth requirements
- **Next**: Optimize streaming parameters or add quality controls

### **Participants Don't See Value**
- **Response**: Dig deeper into their concerns
- **Learning**: Understand value proposition gaps
- **Next**: Refine messaging or pivot features

---

## 📞 **Emergency Contacts**

- **Technical Issues**: [Your contact]
- **Infrastructure Problems**: [Backup contact]
- **Participant Questions**: [Support contact]

---

## 📈 **Next Test Planning**

Based on results, plan follow-up tests:
- **If successful**: Expand to 5-10 friends
- **If partial**: Fix issues and retest with same group
- **If failed**: Simplify approach and retest fundamentals

---

**Ready to test the future of decentralized streaming! 🚀** 