# 🌐 StreamrP2P - Decentralized Streaming Infrastructure

**A peer-to-peer streaming platform where friends help friends reduce bandwidth costs while earning rewards.**

[![Infrastructure](https://img.shields.io/badge/Infrastructure-AWS%20CDK-orange)](infrastructure/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL-blue)](coordinator/)
[![Streaming](https://img.shields.io/badge/Streaming-SRS-red)](ingest-server/)
[![Status](https://img.shields.io/badge/Status-Friends%20Testing%20Ready-brightgreen)](CURRENT_STATUS.md)

---

## 📋 **Navigation Hub**

### **📊 Current Status & Latest Progress**
👉 **[CURRENT_STATUS.md](CURRENT_STATUS.md)** - What's working now, recent breakthroughs, live endpoints

### **🚀 Future Plans & Roadmap** 
👉 **[PROJECT_TRACKER.md](PROJECT_TRACKER.md)** - Priorities, timeline, what's next

### **📺 Live System**
👉 **[LIVE_ENDPOINTS.md](LIVE_ENDPOINTS.md)** - Production URLs, testing info, deployment status

---

## 🎯 **What is StreamrP2P?**

**The Vision**: "Video Torrenting" - distribute stream chunks across friend nodes in real-time, just like BitTorrent but for live video.

**The Economics**: 
- **Streamers**: Reduce bandwidth costs by distributing load
- **Friends**: Earn rewards for helping relay streams  
- **Viewers**: Get better performance through distributed delivery

**The Reality**: We have a **working production system** ready for friends testing!

---

## 🚀 **Quick Start**

- **📊 Current Progress**: [CURRENT_STATUS.md](CURRENT_STATUS.md) - Latest development status  
- **📋 Project Roadmap**: [PROJECT_TRACKER.md](PROJECT_TRACKER.md) - Future plans and milestones
- **🌐 Live System**: [LIVE_ENDPOINTS.md](LIVE_ENDPOINTS.md) - Production URLs and status
- **🎯 Stable Endpoints**: [ENDPOINT_REFERENCE.md](ENDPOINT_REFERENCE.md) - Never-changing URLs guide
- **📚 Full Documentation**: [docs/README.md](docs/README.md) - Complete documentation hub

### **🎮 For Streamers**
1. **Stream to our server**: `rtmp://108.129.47.155:1935/live/your_key`
2. **Check dashboard**: http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com/
3. **Invite friends**: Share the setup guide with supporters

### **🤝 For Friends (Supporters)**

**🎉 NEW: Single Binary Client (24x Easier!)**
- **📦 Download**: [Latest Go Client Release](https://github.com/iddv/streamr/releases/latest) - Choose your OS
- **🚀 Run**: Double-click (Windows) or `./streamr-node` (Mac/Linux) - **No installation needed!**
- **⚡ 5MB binary** vs 200MB+ Docker setup - **instant startup**

**📋 Alternative: Docker Setup**
1. **Get setup guide**: [`docs/testing/FRIEND_SETUP.md`](docs/testing/FRIEND_SETUP.md)
2. **Run support node**: `scripts/setup-friend-node.sh STREAM_KEY`
3. **Earn rewards**: Get paid for helping distribute streams

### **🏗️ For Developers**
1. **Deploy infrastructure**: `cd infrastructure && npx cdk deploy --all`
2. **Start services**: `cd coordinator && docker-compose up`
3. **Run tests**: `python -m pytest tests/`

### **🧠 AI Advisory Consultation**

StreamrP2P includes an AI advisory system with three specialized consultant personas:

- **🔧 Infrastructure Visionary**: Technical architecture and P2P optimization
- **💰 Economic Justice Architect**: Tokenomics and creator economics  
- **🌍 Human Connection Catalyst**: Community building and user adoption

**Usage**: When working with this project, you can **"consult with our zen advisors"** to get expert review and refinement of your work, designs, or decisions from all three specialized perspectives.

👉 **[AI Agent Usage Guide](research/ai_agent_usage_guide.md)** - Complete consultation workflow and examples

---

## 🛠️ **Technical Stack**

### **Infrastructure**
- **AWS CDK**: Infrastructure as Code (TypeScript)
- **EC2 + ALB**: Auto-scaling compute with load balancing  
- **RDS PostgreSQL**: Optimized database with 99%+ performance improvement
- **ElastiCache Redis**: Session management and caching

### **Services**
- **Coordinator API**: FastAPI with real-time node coordination
- **Streaming Server**: SRS with RTMP ingest and HLS output
- **Node Client**: Python scripts for friend supporters
- **Fraud Detection**: Automated validation and earnings calculation

### **Deployment**
- **Docker Compose**: Local development and production orchestration
- **CI/CD Pipeline**: GitHub Actions with automated deployment
- **Monitoring**: Health checks, CloudWatch, performance tracking

---

## 📚 **Documentation Structure**

### **🎯 Current Focus**
- [`CURRENT_STATUS.md`](CURRENT_STATUS.md) - Latest progress and breakthroughs
- [`PROJECT_TRACKER.md`](PROJECT_TRACKER.md) - Roadmap and priorities
- [`docs/testing/FRIEND_SETUP.md`](docs/testing/FRIEND_SETUP.md) - Friend node setup guide

### **📊 System Status**
- [`LIVE_ENDPOINTS.md`](LIVE_ENDPOINTS.md) - Production URLs and testing info
- [`docs/testing/LOCAL_TESTING_GUIDE.md`](docs/testing/LOCAL_TESTING_GUIDE.md) - Local development setup
- [`docs/testing/REMOTE_TESTING_GUIDE.md`](docs/testing/REMOTE_TESTING_GUIDE.md) - Remote testing procedures
- [`docs/testing/FRIEND_TEST_PROTOCOL.md`](docs/testing/FRIEND_TEST_PROTOCOL.md) - Friends testing protocol

### **🏗️ Infrastructure & Deployment**
- [`infrastructure/README.md`](infrastructure/README.md) - AWS deployment guide
- [`docs/aws-deployment/`](docs/aws-deployment/) - Detailed AWS documentation
- [`docs/analysis/ARCHITECTURE_ANALYSIS_REPORT.md`](docs/analysis/ARCHITECTURE_ANALYSIS_REPORT.md) - System architecture

### **📈 Analysis & Research**
- [`research/`](research/) - Economic and technical feasibility studies
- [`docs/analysis/`](docs/analysis/) - Performance analysis and optimization strategies
- [`docs/analysis/AWS_ARCHITECTURE_SECURITY_COST_REVIEW.md`](docs/analysis/AWS_ARCHITECTURE_SECURITY_COST_REVIEW.md) - Security and cost analysis
- [`docs/analysis/BREAKTHROUGH_MILESTONE_SUMMARY.md`](docs/analysis/BREAKTHROUGH_MILESTONE_SUMMARY.md) - Major milestone documentation

### **🛠️ Scripts & Setup**
- [`scripts/setup-friend-node.sh`](scripts/setup-friend-node.sh) - Friend node setup (Linux/Mac)
- [`scripts/setup-friend-node.ps1`](scripts/setup-friend-node.ps1) - Friend node setup (Windows)
- [`scripts/setup-node.sh`](scripts/setup-node.sh) - General node setup
- [`scripts/`](scripts/) - All utility and setup scripts

### **📚 Onboarding**
- [`docs/onboarding/AGENT_SETUP_PROMPT.md`](docs/onboarding/AGENT_SETUP_PROMPT.md) - AI agent setup guide

---

## 🎉 **Major Achievements**

### **✅ Production System Operational**
- **Live Streaming**: 8+ Mbps RTMP streams with perfect A/V sync
- **Real-time Coordination**: Sub-second API response times
- **Automated Deployment**: 6.8 minute zero-touch deployments
- **Database Performance**: 40,000+ queries reduced to 1 query per stream
- **Cost Optimized**: $45/month full production, $36/month paused

### **✅ Ready for Friends Testing**
- **Complete Documentation**: Setup guides for all platforms
- **Cross-Platform Scripts**: Windows, Mac, Linux support
- **Fraud Detection**: Automated validation and earnings calculation
- **Security Hardened**: Production security groups and monitoring

---

## 🤝 **Contributing**

### **🔥 Current Priority: Friends Testing**
We need friends to test the real-world P2P streaming experience:
- **Platform Testing**: Windows, Mac, Linux compatibility
- **Network Validation**: Different ISPs and NAT configurations  
- **UX Feedback**: Setup complexity and documentation clarity
- **Economic Model**: Real-world earnings and reward distribution

### **Development Areas**
- **Frontend**: Dashboard and user interface improvements
- **Client Packaging**: Native installers for easy distribution
- **Mobile Support**: PWA or native app development
- **Performance**: Optimization and scaling improvements

### **Getting Involved**
1. **Test the Platform**: Try friend node setup ([guide](docs/testing/FRIEND_SETUP.md))
2. **Review Documentation**: Suggest improvements to guides
3. **Submit Issues**: Report bugs or feature requests on GitHub
4. **Contribute Code**: Fork, develop, and submit pull requests

---

## 📞 **Contact & Support**

- **Current Status**: [`CURRENT_STATUS.md`](CURRENT_STATUS.md) - Latest development updates
- **GitHub Issues**: Report bugs and request features  
- **Documentation**: Comprehensive guides for all use cases

**Join us in building the future of decentralized streaming! 🚀**

---

*StreamrP2P proves that decentralized streaming infrastructure can be simple, social, and economically viable for real users today.* 