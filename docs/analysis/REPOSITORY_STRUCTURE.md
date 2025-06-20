# 📁 StreamrP2P Repository Structure

**Clean, organized structure for AI agent navigation and professional development.**

---

## 🏗️ **Root Directory Overview**

```
streamr/                           # 🚀 StreamrP2P Root
├── infrastructure/                # 🏗️ AWS CDK Infrastructure (NEW!)
├── coordinator/                   # 🎛️ FastAPI Backend Services  
├── node-client/                   # 👥 Friend Node P2P Client
├── docs/                          # 📚 Organized Documentation Hub
├── research/                      # 🔬 Strategic Research & Planning
├── archive/                       # 📦 Historical Development Notes
├── scripts/                       # 🛠️ Development & Testing Utilities
├── ingest-server/                 # 📡 RTMP Streaming Configuration
├── CURRENT_STATUS.md              # 📊 Current Progress & Next Steps
├── README.md                      # 🗺️ AI Agent Navigation Map
├── REPOSITORY_STRUCTURE.md        # 📁 This file - structure guide
├── BREAKTHROUGH_MILESTONE_SUMMARY.md # 🎯 Major Achievement Summary
├── LOCAL_TESTING_GUIDE.md         # 🔧 Local Development Guide
└── setup-friend-node.sh           # 👥 Friend Onboarding Script
```

---

## 🏗️ **Infrastructure Directory** *(NEW - CDK Architecture)*

```
infrastructure/                    # AWS CDK Infrastructure as Code
├── lib/
│   ├── config/
│   │   ├── types.ts               # TypeScript interfaces & types
│   │   ├── streamr-config.ts      # Multi-stage configuration
│   │   └── deployment-context.ts  # Context utilities
│   └── stacks/
│       ├── foundation-stack.ts    # VPC, RDS, ElastiCache
│       └── application-stack.ts   # EC2, ALB, Security Groups
├── bin/
│   └── infrastructure.ts          # CDK app entry point
├── scripts/
│   └── deploy-beta.sh            # 🚀 One-command deployment
├── test/                          # CDK unit tests
├── README.md                      # Complete infrastructure guide
├── package.json                   # CDK dependencies
└── cdk.json                       # CDK configuration
```

**Purpose**: Professional AWS infrastructure with multi-stage (beta/gamma/prod) and multi-region support.

---

## 🎛️ **Coordinator Directory** *(Core Backend)*

```
coordinator/                       # FastAPI Backend Services
├── app/
│   ├── __init__.py
│   ├── main.py                    # 🎯 Main FastAPI application
│   ├── database.py                # Database connection & models
│   ├── models.py                  # SQLAlchemy data models
│   ├── schemas.py                 # Pydantic request/response schemas
│   ├── payout_service.py          # 💰 Earnings calculation engine
│   ├── spot_check_prober.py       # 🔍 Fraud detection service
│   ├── stats_collector.py         # 📊 Node statistics collection
│   └── worker.py                  # Background task worker
├── database/                      # Database migrations & setup
├── docker/                        # Docker configuration
├── docker-compose.yml             # 🐳 Service orchestration
├── Dockerfile                     # Container definition
├── requirements.txt               # Python dependencies
└── README.md                      # Backend documentation
```

**Purpose**: Coordination server that manages friend nodes, calculates earnings, and provides real-time API.

---

## 👥 **Node Client Directory** *(Friend P2P Client)*

```
node-client/                       # Friend Node Implementation
├── scripts/
│   └── node_client.py            # 👥 Main friend node client
├── docker/                        # Docker configuration for nodes
├── docker-compose.yml             # Node service definition
├── Dockerfile                     # Node container setup
├── test_local_node.py             # 🧪 Local testing script
└── README.md                      # Node setup guide
```

**Purpose**: Client that friends run to participate in P2P network and earn rewards.

---

## 📚 **Documentation Hub** *(Organized by Topic)*

```
docs/                              # Centralized Documentation
├── aws-deployment/                # ☁️ AWS & Infrastructure Guides
│   ├── AWS_DEPLOYMENT_GUIDE.md    # Step-by-step AWS setup
│   ├── AWS_MCP_CONFIGURATION.md   # MCP server configuration
│   ├── CDK_VS_TERRAFORM_COMPARISON.md # Infrastructure comparison
│   └── STREAMR_CDK_INFRASTRUCTURE_PLAN.md # CDK architecture plan
├── networking/                    # 🌐 Network & Security Guides  
│   ├── FIX_WSL2_NETWORKING.md     # WSL2 networking fixes
│   ├── TROUBLESHOOT_WSL2_EXTERNAL_ACCESS.md # External access guide
│   └── SECURE_REMOTE_TESTING_OPTIONS.md # Security considerations
├── testing/                       # 🧪 Testing Strategies & Guides
│   ├── PRAGMATIC_REMOTE_TESTING_PLAN.md # Phase 2A testing plan
│   ├── REMOTE_TESTING_CHECKLIST.md # Security checklist
│   ├── REMOTE_TESTING_GUIDE.md    # Remote testing guide
│   ├── FRIEND_SETUP.md            # Friend onboarding
│   └── STREAMING_SETUP_CLARIFICATION.md # Streaming setup
└── analysis/                      # 📊 Research & Analysis
    ├── BINARY_PROPOSAL.md         # Binary executable proposal
    ├── community_adoption_analysis.md # Community strategy
    ├── competitive-analysis.md    # Market analysis
    ├── economic_feasibility_analysis.md # Economic model
    ├── legal-regulatory.md        # Legal considerations
    ├── NETWORKING_AUTOMATION_SUMMARY.md # Automation analysis
    ├── poc-tasks.md               # Proof of concept tasks
    ├── proof-of-bandwidth.md      # Bandwidth validation
    ├── social-design.md           # Social platform design
    ├── sponsorship-contract-architecture.md # Smart contracts
    ├── technical_feasibility_analysis.md # Technical analysis
    └── TESTING_SUMMARY.md         # Testing methodology
```

**Purpose**: Organized documentation by topic area for easy navigation and maintenance.

---

## 🔬 **Research Directory** *(Strategic Planning)*

```
research/                          # Strategic Research & Planning
├── ai_agent_usage_guide.md        # AI agent collaboration guide
├── analysis_of_feasibility.md     # Project feasibility analysis
├── prfaq_phase2_ready.md          # 🎯 Updated PRFAQ (Phase 2 ready)
├── prfaq.md                       # Original product vision
├── product_development_plan.md    # Development roadmap
├── project_tracker.md             # Progress tracking
├── README.md                      # Research overview
└── [AI Advisor Personas]          # Specialized AI advisor documents
```

**Purpose**: High-level strategy, product vision, and specialized AI advisor consultation.

---

## 📦 **Archive Directory** *(Historical Context)*

```
archive/                           # Historical Development
├── chat1.txt                      # Early development conversations
├── chat2.txt                      # Technical breakthrough discussions  
└── chat3.txt                      # Architecture planning sessions
```

**Purpose**: Preserves development history and decision-making context.

---

## 🛠️ **Scripts Directory** *(Development Utilities)*

```
scripts/                           # Development & Testing Scripts
├── setup-host-networking-macos.sh # macOS network configuration
├── setup-host-networking-wsl.ps1  # WSL network configuration  
└── test-networking.sh             # Network connectivity testing
```

**Purpose**: Automation scripts for development environment setup and testing.

---

## 📡 **Ingest Server Directory** *(Streaming Configuration)*

```
ingest-server/                     # RTMP Streaming Setup
├── ingest_config.yaml             # SRS server configuration
├── nginx.conf                     # Nginx RTMP configuration
├── simple-nginx.conf              # Simplified nginx setup
├── start-ingest.ps1               # Windows startup script
└── start-ingest.sh                # Linux startup script
```

**Purpose**: RTMP streaming server configuration and startup scripts.

---

## 🎯 **Key Files at Root Level**

| File | Purpose | When to Read |
|------|---------|--------------|
| **CURRENT_STATUS.md** | 📊 Project progress, achievements, next steps | First priority for status |
| **README.md** | 🗺️ AI agent navigation map | Entry point for understanding |
| **REPOSITORY_STRUCTURE.md** | 📁 This file - detailed structure guide | Understanding organization |
| **BREAKTHROUGH_MILESTONE_SUMMARY.md** | 🎯 Major achievements summary | Understanding recent progress |
| **LOCAL_TESTING_GUIDE.md** | 🔧 Complete local testing guide | Development and testing |
| **setup-friend-node.sh** | 👥 One-command friend onboarding | Friend setup automation |

---

## 🎭 **AI Agent Navigation Tips**

### **For Status & Progress**
1. Start with `CURRENT_STATUS.md` for overall project status
2. Check `BREAKTHROUGH_MILESTONE_SUMMARY.md` for recent achievements
3. Review `infrastructure/README.md` for deployment readiness

### **For Technical Understanding**
1. Explore `coordinator/app/main.py` for backend logic
2. Check `node-client/scripts/node_client.py` for P2P implementation
3. Review `infrastructure/lib/stacks/` for AWS architecture

### **For Documentation**
1. Use `docs/` subdirectories for specific topic areas
2. Check `research/` for strategic planning and vision
3. Reference `archive/` for historical development context

### **For Development**
1. Use `LOCAL_TESTING_GUIDE.md` for local setup
2. Run `./start-host.sh` for local development server
3. Use `infrastructure/scripts/deploy-beta.sh` for AWS deployment

---

## 🚀 **Clean & Professional Structure**

This repository structure provides:

- ✅ **Clear Separation of Concerns**: Infrastructure, application, docs, research
- ✅ **AI Agent Friendly**: Easy navigation with clear purpose statements
- ✅ **Professional Organization**: Industry-standard directory structure
- ✅ **Scalable Architecture**: Ready for team collaboration and growth
- ✅ **Documentation First**: Comprehensive guides for all aspects
- ✅ **Development Ready**: All tools and scripts organized and accessible

**Result**: A production-ready codebase that's easy to navigate, understand, and contribute to! 🎉 