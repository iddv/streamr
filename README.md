# 🌐 StreamrP2P - Decentralized Streaming Infrastructure

**A peer-to-peer streaming platform where friends help friends reduce bandwidth costs while earning rewards.**

[![Infrastructure](https://img.shields.io/badge/Infrastructure-AWS%20CDK-orange)](infrastructure/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL-blue)](coordinator/)
[![Streaming](https://img.shields.io/badge/Streaming-SRS-red)](ingest-server/)
[![Status](https://img.shields.io/badge/Status-VPN%20Mesh%20Ready-brightgreen)](CURRENT_STATUS.md)

---

## 🎯 **MAJOR BREAKTHROUGH: VPN Mesh Solution**

**The Innovation**: Instead of fighting NAT traversal complexity, we're implementing a **self-hosted VPN mesh** that makes all friend nodes appear on the same private network. This eliminates router configuration, port forwarding, and platform compatibility issues.

**The Approach**: **Headscale** (open-source Tailscale control server) + official Tailscale clients = zero-config P2P mesh networking.

### **Why This Changes Everything**
- ✅ **No Router Configuration** - Eliminates the #1 user friction point
- ✅ **Cross-Platform Ready** - Tailscale clients exist for all platforms
- ✅ **Battle-Tested Networking** - Leverages mature NAT traversal technology
- ✅ **Self-Hosted Control** - No ongoing costs, complete ownership
- ✅ **True P2P Validation** - Perfect test of "video torrenting" concept

---

## 🚀 **Current Status: Ready for VPN Validation**

### **✅ What's Working (Production Ready)**
- **🏗️ AWS Infrastructure**: Fully automated CDK deployment
- **⚡ Database Performance**: 99%+ improvement (40k+ queries → 1 query)
- **🔒 Zero-Touch Deployment**: Complete CI/CD with secrets management
- **📊 Live Endpoints**: All coordinator APIs operational
- **📺 Streaming Server**: SRS server ready for RTMP/HLS
- **🤝 Friend Setup**: Cross-platform scripts and documentation

### **🔄 Next Phase: VPN Mesh Validation**
**Goal**: Validate VPN mesh approach with real friends testing  
**Timeline**: 4-6 hours total effort  
**Plan**: [`docs/analysis/VPN_MESH_VALIDATION_PLAN.md`](docs/analysis/VPN_MESH_VALIDATION_PLAN.md)

---

## 🌟 **How StreamrP2P Works**

### **The Vision: Video Torrenting**
StreamrP2P is essentially "video torrenting" - distributing stream chunks across friend nodes in real-time:
- **Traditional Torrenting**: File chunks distributed asynchronously
- **StreamrP2P**: Video chunks distributed with ~2-3 second latency  
- **Same Principle**: More peers = better distribution, reduced central bandwidth

### **Current Architecture**
```
Streamer → [VPN Mesh] → Friend Nodes → [VPN Mesh] → Viewers
          ✅ All nodes on same private network
```

### **The Economic Model**
- **Streamers**: Reduce bandwidth costs by distributing load
- **Friends**: Earn rewards for helping relay streams
- **Viewers**: Get better performance through distributed delivery
- **Platform**: Scales organically through social connections

---

## 🛠️ **Technical Stack**

### **Infrastructure**
- **AWS CDK**: Infrastructure as Code with TypeScript
- **EC2 + ALB**: Auto-scaling compute with load balancing
- **RDS PostgreSQL**: Optimized database with performance monitoring
- **ElastiCache**: Redis for session management and caching

### **Backend Services**
- **Coordinator API**: FastAPI with contribution-weighted payouts
- **Database Layer**: Optimized queries with window functions
- **Streaming Server**: SRS with RTMP ingest and HLS output
- **Monitoring**: Health checks and performance tracking

### **Networking (New!)**
- **Headscale**: Self-hosted VPN mesh control server
- **Tailscale Clients**: Cross-platform VPN mesh participants
- **WireGuard**: Underlying P2P encryption protocol
- **DERP Relays**: Fallback for difficult NAT scenarios

---

## 📊 **Live System Status**

### **🌐 Current Endpoints**
- **Web Dashboard**: http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com/
- **API Base**: http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com/
- **Health Check**: http://streamr-p2p-beta-alb-1243469977.eu-west-1.elb.amazonaws.com/health

### **📺 Streaming Endpoints**  
- **RTMP Ingest**: rtmp://108.129.97.122:1935/live/{stream_key}
- **HLS Playback**: http://108.129.97.122:8080/live/{stream_key}.m3u8
- **HTTP-FLV**: http://108.129.97.122:8080/live/{stream_key}.flv

### **🚀 Quick Deploy**
```bash
cd infrastructure
npx cdk deploy streamr-p2p-beta-ireland-application --require-approval never
# Result: Complete working system in 6.8 minutes
```

---

## 🎯 **Getting Started**

### **For VPN Mesh Testing (Current Phase)**
1. **Deploy Headscale**: Follow [`docs/analysis/VPN_MESH_VALIDATION_PLAN.md`](docs/analysis/VPN_MESH_VALIDATION_PLAN.md)
2. **Install Tailscale**: Download from https://tailscale.com/download
3. **Join Mesh**: Connect to self-hosted Headscale server
4. **Test Streaming**: Stream over private mesh network

### **For Current Friend Testing**
1. **Clone Repository**: `git clone https://github.com/iddv/streamr.git`
2. **Setup Friend Node**: `./setup-friend-node.sh YOUR_STREAM_KEY`
3. **Follow Guide**: [`docs/testing/FRIEND_SETUP.md`](docs/testing/FRIEND_SETUP.md)
4. **Share Feedback**: Report experience and issues

### **For Infrastructure Development**
1. **Prerequisites**: AWS CLI, Node.js, Docker
2. **Deploy Infrastructure**: `cd infrastructure && npx cdk deploy --all`
3. **Start Services**: `cd coordinator && docker-compose up`
4. **Run Tests**: `python -m pytest tests/`

---

## 📈 **Performance Achievements**

### **Database Optimization**
- **99%+ Performance Improvement**: 40,000+ queries → 1 query per stream
- **Sub-Second Payouts**: Contribution-weighted calculations in <1 second
- **Scalable Architecture**: Ready for thousands of concurrent streams

### **Deployment Automation**
- **6.8 Minute Deployments**: Complete infrastructure from zero to production
- **Zero Manual Configuration**: Automated secrets management
- **Production Ready**: Health checks, monitoring, error handling

### **Cost Optimization**
- **$45/month Operational**: Full production infrastructure
- **$36/month Paused**: Development mode with pause capability
- **Scaling Economics**: User-provided bandwidth reduces operational costs

---

## 🔮 **Roadmap**

### **Phase 1: VPN Mesh Validation (This Week)**
- [ ] Deploy Headscale control server
- [ ] Create VPN mesh setup scripts  
- [ ] Test with local devices
- [ ] Invite friends for real-world testing
- [ ] Collect performance and UX data

### **Phase 2A: Integration (If VPN Succeeds)**
- [ ] Embed WireGuard in custom client
- [ ] Auto-configuration for mesh joining
- [ ] Single executable deployment
- [ ] Bandwidth limits and monitoring

### **Phase 2B: Alternative (If VPN Partial)**
- [ ] Custom installer for Tailscale setup
- [ ] Guided setup wizard
- [ ] Multiple connection strategies
- [ ] Fallback relay options

### **Phase 3: Production Scale**
- [ ] Native apps for all platforms
- [ ] One-click setup experience
- [ ] Advanced economic models
- [ ] Global relay network

---

## 🤝 **Contributing**

### **Current Focus: VPN Mesh Validation**
We're actively testing the VPN mesh approach and need:
- **Friends for Testing**: Help validate real-world performance
- **Platform Testing**: Windows, Mac, Linux, mobile compatibility
- **Network Conditions**: Different ISPs, corporate networks, mobile
- **UX Feedback**: Documentation clarity and setup complexity

### **Development Areas**
- **Infrastructure**: AWS CDK improvements and cost optimization
- **Backend**: API enhancements and database scaling
- **Networking**: VPN mesh integration and P2P protocols
- **Frontend**: Dashboard improvements and user experience

### **Getting Involved**
1. **Test the Platform**: Try friend node setup and report issues
2. **Review Documentation**: Suggest improvements to guides
3. **Submit Issues**: Report bugs or feature requests
4. **Contribute Code**: Fork, develop, and submit pull requests

---

## 📚 **Documentation**

### **User Guides**
- [`docs/testing/FRIEND_SETUP.md`](docs/testing/FRIEND_SETUP.md) - Complete friend node setup
- [`docs/testing/REMOTE_TESTING_GUIDE.md`](docs/testing/REMOTE_TESTING_GUIDE.md) - Remote testing procedures
- [`LOCAL_TESTING_GUIDE.md`](LOCAL_TESTING_GUIDE.md) - Local development setup

### **Technical Documentation**
- [`docs/analysis/VPN_MESH_VALIDATION_PLAN.md`](docs/analysis/VPN_MESH_VALIDATION_PLAN.md) - VPN mesh implementation plan
- [`docs/aws-deployment/AWS_DEPLOYMENT_GUIDE.md`](docs/aws-deployment/AWS_DEPLOYMENT_GUIDE.md) - Infrastructure deployment
- [`ARCHITECTURE_ANALYSIS_REPORT.md`](ARCHITECTURE_ANALYSIS_REPORT.md) - System architecture overview

### **Analysis & Research**
- [`docs/analysis/DATABASE_SCALING_STRATEGY.md`](docs/analysis/DATABASE_SCALING_STRATEGY.md) - Database optimization strategy
- [`AWS_ARCHITECTURE_SECURITY_COST_REVIEW.md`](AWS_ARCHITECTURE_SECURITY_COST_REVIEW.md) - Security and cost analysis
- [`research/`](research/) - Economic and technical feasibility studies

---

## 🎉 **The Future of Streaming**

StreamrP2P represents a fundamental shift from centralized to decentralized streaming infrastructure:

- **Social**: Friends helping friends reduces costs and builds community
- **Economic**: Sustainable incentives drive organic growth
- **Technical**: P2P distribution scales better than traditional CDNs
- **Accessible**: Simple setup makes decentralized infrastructure practical

**We're proving that decentralized streaming infrastructure can be simple, social, and economically viable for real users today.**

---

## 📞 **Contact & Support**

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Comprehensive guides for all use cases
- **Current Status**: [`CURRENT_STATUS.md`](CURRENT_STATUS.md) - Latest development updates

**Join us in building the future of decentralized streaming! 🚀** 