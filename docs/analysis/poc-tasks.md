# PoC Task Breakdown

This document outlines the engineering tasks required to build the "restreaming as support" Proof of Concept.

## 🚀 Status Update

**Epic 1: Coordinator Server** ✅ **COMPLETED**
- ✅ Issue #1: Setup Basic Server & Database
- ✅ Issue #2: Implement Core Endpoints  
- ✅ Issue #3: Implement Stats Collector Service
- ✅ Issue #4: Implement Spot-Check Prober Service
- ✅ Issue #5: Implement Payout & Dashboard Logic

**Epic 2: Node Client** ✅ **COMPLETED**
- ✅ Issue #6: Create Node Client Wrapper
- ✅ Issue #7: Dockerize the Node Client

**Epic 3: Infrastructure & Documentation** ✅ **COMPLETED (Local Testing)**
- ✅ Issue #8: Local Ingest Server Setup (via `start-host.sh`)
- ✅ Issue #9: Local Coordinator Deployment (via `start-host.sh`)
- ✅ Issue #10: Agent-Friendly Testing Documentation

**🧪 Local Testing Setup** ✅ **COMPLETED**
- ✅ One-command host setup (`start-host.sh`)
- ✅ One-command friend setup (`setup-node.sh`)
- ✅ Agent-friendly automation scripts
- ✅ Comprehensive testing documentation

---

## Epic 1: Coordinator Server ✅

The central service responsible for orchestration, verification, and reward calculation.

-   **[Issue #1] Setup Basic Server & Database:** ✅
    -   ✅ FastAPI project with PostgreSQL database
    -   ✅ SQLAlchemy models for streams, nodes, and probe results
    -   ✅ Docker configuration with docker-compose

-   **[Issue #2] Implement Core Endpoints:** ✅
    -   ✅ `POST /streams`: Stream registration with token pools
    -   ✅ `GET /streams`: Stream discovery for node operators
    -   ✅ `POST /nodes/heartbeat`: Node heartbeat monitoring
    -   ✅ `GET /dashboard`: Real-time dashboard data

-   **[Issue #3] Implement Stats Collector Service:** ✅
    -   ✅ Background worker polling `/stats.json` endpoints every 60s
    -   ✅ Validation of rtmp_relay stats data structure
    -   ✅ Database storage of probe results with success/failure tracking

-   **[Issue #4] Implement Spot-Check Prober Service:** ✅
    -   ✅ Random interval RTMP connection testing using ffprobe
    -   ✅ Fraud detection for nodes reporting healthy but failing spot-checks
    -   ✅ Automatic flagging of fraudulent nodes

-   **[Issue #5] Implement Payout & Dashboard Logic:** ✅
    -   ✅ Reward calculation based on uptime and fraud detection
    -   ✅ Analytics endpoints: `/payouts`, `/nodes/{id}/earnings`, `/leaderboard`
    -   ✅ Zero payout for flagged nodes, proportional rewards for honest nodes

---

## Epic 2: Node Client ✅

The Dockerized package that operators will run. The goal is zero-friction setup.

-   **[Issue #6] Create Node Client Wrapper:** ✅
    -   ✅ Python script managing rtmp_relay lifecycle
    -   ✅ Automatic stream discovery from coordinator
    -   ✅ Public IP discovery and heartbeat transmission
    -   ✅ Graceful shutdown and error handling

-   **[Issue #7] Dockerize the Node Client:** ✅
    -   ✅ Dockerfile building rtmp_relay from source
    -   ✅ Environment variable configuration
    -   ✅ Docker-compose for easy testing
    -   ✅ Comprehensive README with zero-friction setup instructions

---

## Epic 3: Infrastructure & Documentation

The supporting elements needed to run the PoC.

-   **[Issue #8] Deploy Central Ingest Server:**
    -   Set up a cloud instance running `elnormous/rtmp_relay` in "host" mode to act as the single ingest point for the PoC.

-   **[Issue #9] Deploy Coordinator Server:**
    -   Deploy the Coordinator server application and its database to a cloud environment.

-   **[Issue #10] Create Tester Documentation:**
    -   Write a simple `README.md` for the PoC testers with clear, step-by-step instructions on how to run the Node Client Docker container.

---

## 🎯 Next Steps

**ALL EPICS COMPLETE!** 🎉 The PoC is ready for local testing:

1. **Local Testing Phase** - Use `start-host.sh` and invite friends with `setup-node.sh`
2. **Document Results** - Record performance, bugs, and feedback
3. **Cloud Deployment** - Move to production infrastructure after successful local testing
4. **Alpha Testing** - Scale to larger community group
5. **Iterate Based on Feedback** - Refine the system based on real-world usage

The core economic loop is now implemented and ready for testing:
- ✅ Stream registration with token pools
- ✅ Node discovery and participation  
- ✅ Continuous verification (stats + spot-checks)
- ✅ Fraud detection and prevention
- ✅ Reward calculation and distribution 