# StreamrP2P — Deep Code & Product Review + Development Backlog

**Review Date**: February 26, 2026  
**Reviewer**: Kiro AI  
**Purpose**: Assess current state, validate vision alignment, and create actionable backlog

---

## 1. Where We Are — Honest Assessment

### Phase: 2D+ (Production Streaming Operational)
**Last meaningful development**: January 2025 (~13 months ago)

The project has a solid foundation but has been dormant for over a year. The core streaming pipeline works end-to-end, the infrastructure is production-grade, and the economic model has been thoughtfully designed. But the actual P2P functionality — the core value proposition — hasn't been built yet.

### What's Real and Working
- **Streaming pipeline**: RTMP ingest → SRS → HLS/HTTP-FLV output. A/V sync resolved.
- **Coordinator API**: 18+ endpoints covering streams, nodes, payouts, economics, dashboards.
- **Infrastructure**: Full AWS CDK with VPC, RDS, ElastiCache, ECS Fargate, ALB + NLB with Elastic IP.
- **CI/CD**: GitHub Actions for infra deploy, Go client builds, and post-deploy integration tests.
- **Economic model**: Contribution-weighted payouts, graduated fraud penalties, bandwidth ledger, trust scores.
- **Go client binary**: Cross-platform builds working, but it's a shell — connects to coordinator and exits.
- **Database schema**: 5 tables (streams, nodes, probe_results, bandwidth_ledger, user_accounts).
- **Background services**: Stats collector (60s polling) and spot-check prober (5-15 min random RTMP tests).

### What's Missing (The Hard Parts)
- **No actual P2P relay**: The Go client can't relay streams. It just does a health check and exits.
- **No VPN mesh**: Headscale/Tailscale integration was planned but never started.
- **No authentication**: `get_authenticated_node()` returns a hardcoded dummy value.
- **No real bandwidth verification**: Reports are accepted but `is_verified` stays False, `trust_score` stays None.
- **No database migrations**: Using `create_all()` — no Alembic, no version control on schema.
- **No frontend**: Two HTML templates exist (economic dashboard, streams dashboard) but they're static shells that call API endpoints.
- **No stream discovery**: No way for viewers to find streams.
- **No user registration/login**: No user accounts beyond the node-level UserAccount model.
- **Placeholder economics**: Hourly earnings hardcoded to $0.25/hour, platform margin hardcoded to 7.5%.

---

## 2. Vision Alignment Check

### Original PRFAQ Vision vs Current Reality

| PRFAQ Claim | Current Reality | Alignment |
|---|---|---|
| Mobile-first P2P streaming | Desktop-only, no P2P relay built | ❌ Far off |
| Sub-5-second latency | HLS segments (10s) = ~15-20s latency | ❌ Not close |
| 90% creator revenue share | Economic analysis flagged this as unsustainable | ✅ Correctly pivoted |
| Watch-to-earn tokens | Fiat-first approach adopted (good pivot) | ✅ Aligned with advisor guidance |
| Blockchain integration | Deferred (correct per Economic Justice Architect) | ✅ Smart deferral |
| Gaming hardware integration | Not started, not needed for MVP | ⚪ Deferred |
| 10,000+ beta users | 0 external users | ❌ Aspirational |
| AI-powered mesh network | Not built | ❌ Future |

### Where Vision Was Correctly Adjusted
The project made several smart pivots based on ZEN advisor guidance:
1. **Fiat-first** instead of tokenomics (avoids Theta Network's -95% token collapse)
2. **Friends-first** instead of public launch (validates with 5 people, not 5000)
3. **Go binary** instead of Docker (targets 85% install success vs 5%)
4. **Contribution-weighted payouts** instead of equal-share (prevents gaming)
5. **$0.05/GB transparent rate** instead of speculative token rewards

### Where Vision Needs Recalibration
The PRFAQ is wildly aspirational and disconnected from the actual product. It reads like a Series B pitch deck for a product that's still in early alpha. The core thesis — "friends help friends reduce streaming costs" — is sound and validated by the architecture. But the PRFAQ should be rewritten to match reality.

---

## 3. Code Quality Assessment

### Coordinator (Python/FastAPI) — Grade: B-
**Strengths:**
- Clean separation of concerns (models, schemas, services, endpoints)
- Optimized queries (fixed N+1 problem with single aggregated queries)
- Proper async patterns in stats collector and spot-check prober
- Graceful shutdown handling in worker manager

**Issues:**
- No authentication anywhere — `get_authenticated_node()` is a stub
- No input validation beyond Pydantic basics (e.g., stream_id format, SQL injection via raw text())
- `migration_endpoints.py` uses raw SQL via `text()` — should be removed or secured
- No Alembic migrations — `create_all()` will silently skip schema changes
- `payout_service.py` opens/closes DB sessions manually instead of using dependency injection
- No rate limiting on any endpoint
- No CORS configuration
- `datetime.utcnow()` is deprecated in Python 3.12+ (use `datetime.now(UTC)`)
- Economic dashboard endpoints return placeholder/hardcoded values

### Infrastructure (CDK/TypeScript) — Grade: A-
**Strengths:**
- Multi-stage deployment (beta/gamma/prod) with proper config separation
- Security groups properly scoped (ALB → service, service → DB/cache)
- ECS Fargate with health checks, log groups, proper IAM roles
- NLB with Elastic IP for stable RTMP endpoint
- Operational bastion with SSM (no SSH keys)
- Cost optimization (NAT gateway disabled for non-prod)

**Issues:**
- Hardcoded Elastic IP allocation ID (`eipalloc-054297e161bb78275`)
- No HTTPS/TLS anywhere — all HTTP
- No WAF on ALB
- No auto-scaling configured on ECS service (fixed `desiredCount: 1`)
- Database in public subnet when NAT disabled (cost optimization trades security)
- No CloudWatch alarms defined despite config supporting them
- SRS container has no custom config mounted — using defaults

### Go Client — Grade: D
**Strengths:**
- Clean CLI with flags, help, version
- Cross-platform build pipeline works
- Logrus structured logging

**Issues:**
- Does literally nothing beyond a health check and `fmt.Scanln()`
- No internal packages despite directory structure suggesting them
- No RTMP relay capability
- No heartbeat/registration with coordinator
- No bandwidth reporting
- No configuration file support
- Hardcoded coordinator URL as default

### Tests — Grade: C+
**Strengths:**
- Flexible test infrastructure (local/production/custom targets)
- Good smoke tests covering schema validation and performance
- Stream lifecycle state machine test is thorough

**Issues:**
- No unit tests for payout_service, stats_collector, or spot_check_prober
- No tests for economic endpoints
- No tests for bandwidth reporting
- No negative/error path tests
- No load/stress tests
- Integration tests require a running coordinator (no mocking)

---

## 4. Architecture Assessment

### What's Solid
```
OBS → RTMP → [NLB + Elastic IP] → [ECS: SRS] → HLS/FLV → Viewers
                                    [ECS: Coordinator] → [RDS PostgreSQL]
                                                       → [ElastiCache Redis]
```
This is a clean, production-grade streaming architecture. The separation of SRS (streaming) and Coordinator (API) in the same ECS task is pragmatic for the current scale.

### What's Missing from the Architecture
```
The P2P layer doesn't exist yet:

Current:  Streamer → SRS → Viewer (centralized)
Target:   Streamer → SRS → Friend Nodes → Viewers (distributed)
                           ↑
                     This part is unbuilt
```

The entire value proposition — friends relaying stream chunks to reduce bandwidth — requires:
1. Go client that can receive stream chunks from SRS
2. Go client that can serve those chunks to viewers
3. Coordinator orchestrating which nodes serve which viewers
4. Bandwidth measurement and reporting
5. NAT traversal or VPN mesh for node connectivity

---

## 5. Development Backlog

### Priority Legend
- 🔴 P0 — Must have before any testing with friends
- 🟠 P1 — Must have for meaningful friend testing
- 🟡 P2 — Should have for beta quality
- 🟢 P3 — Nice to have / future

---

### Epic 1: Foundation Cleanup (Sprint 1-2)
*Get the house in order before building new features*

| # | Task | Priority | Est. | Notes |
|---|------|----------|------|-------|
| 1.1 | Add Alembic migrations | 🔴 P0 | 4h | Replace `create_all()`, version control schema |
| 1.2 | Implement JWT authentication | 🔴 P0 | 8h | Replace dummy `get_authenticated_node()` |
| 1.3 | Add CORS middleware | 🔴 P0 | 1h | Required for any frontend |
| 1.4 | Add rate limiting | 🟠 P1 | 3h | Protect API from abuse |
| 1.5 | Remove `migration_endpoints.py` | 🔴 P0 | 0.5h | Raw SQL admin endpoint is a security risk |
| 1.6 | Fix `datetime.utcnow()` deprecation | 🟡 P2 | 2h | Use `datetime.now(UTC)` throughout |
| 1.7 | Add HTTPS/TLS to ALB | 🟠 P1 | 4h | ACM cert + HTTPS listener |
| 1.8 | Add Alembic to Docker image | 🔴 P0 | 2h | Migration support in deployment |
| 1.9 | Configure SRS with custom config | 🟠 P1 | 3h | Mount A/V sync config into container |

---

### Epic 2: Go Client — Core P2P Functionality (Sprint 2-5)
*This is the heart of the product — without this, there's no P2P*

| # | Task | Priority | Est. | Notes |
|---|------|----------|------|-------|
| 2.1 | Implement coordinator registration | 🔴 P0 | 4h | POST /nodes/heartbeat on startup |
| 2.2 | Implement periodic heartbeat loop | 🔴 P0 | 3h | Send heartbeat every 30s |
| 2.3 | Add configuration file support | 🟠 P1 | 4h | YAML/TOML config for coordinator URL, node ID, etc. |
| 2.4 | Implement HLS chunk fetching | 🔴 P0 | 8h | Pull .ts segments from SRS |
| 2.5 | Implement local HLS server | 🔴 P0 | 8h | Serve chunks to local viewers |
| 2.6 | Implement bandwidth measurement | 🔴 P0 | 6h | Track bytes transferred per session |
| 2.7 | Implement bandwidth reporting | 🔴 P0 | 4h | POST to /api/v1/sessions/{id}/bandwidth-report |
| 2.8 | Add graceful shutdown | 🟠 P1 | 2h | Deregister from coordinator on exit |
| 2.9 | Add auto-update mechanism | 🟡 P2 | 8h | Check for new versions, self-update |
| 2.10 | Add system tray / background mode | 🟡 P2 | 12h | Run as background service |

---

### Epic 3: P2P Relay Network (Sprint 4-7)
*The actual "video torrenting" — distributing chunks across friend nodes*

| # | Task | Priority | Est. | Notes |
|---|------|----------|------|-------|
| 3.1 | Design chunk distribution protocol | 🔴 P0 | 8h | How coordinator assigns chunks to nodes |
| 3.2 | Implement VPN mesh (Headscale) | 🔴 P0 | 12h | Deploy Headscale, integrate Tailscale in Go client |
| 3.3 | Implement peer-to-peer chunk relay | 🔴 P0 | 16h | Node A fetches from SRS, serves to Node B |
| 3.4 | Implement viewer routing | 🔴 P0 | 12h | Coordinator tells viewer which node to connect to |
| 3.5 | Implement chunk verification | 🟠 P1 | 8h | Verify chunks aren't corrupted in relay |
| 3.6 | Implement fallback to SRS | 🟠 P1 | 6h | If no peers available, fall back to direct SRS |
| 3.7 | Add WebSocket coordination | 🟠 P1 | 8h | Real-time node assignment updates |
| 3.8 | Implement adaptive bitrate relay | 🟡 P2 | 12h | Nodes serve quality matching their bandwidth |

---

### Epic 4: Economic Model — Make It Real (Sprint 3-6)
*Replace placeholders with actual calculations*

| # | Task | Priority | Est. | Notes |
|---|------|----------|------|-------|
| 4.1 | Implement real bandwidth verification | 🔴 P0 | 8h | Cross-reference reports with probe data |
| 4.2 | Implement trust score calculation | 🔴 P0 | 6h | Based on verification history |
| 4.3 | Replace hardcoded economic values | 🟠 P1 | 4h | $0.05/GB rate, actual platform margin |
| 4.4 | Implement payout scheduling | 🟠 P1 | 8h | Periodic payout calculations (hourly/daily) |
| 4.5 | Implement earnings history API | 🟠 P1 | 4h | Real hourly earnings, not placeholders |
| 4.6 | Add economic alerts | 🟡 P2 | 4h | Alert on suspicious patterns |
| 4.7 | Implement founder supporter multiplier | 🟡 P2 | 3h | 1.1x earnings for early adopters |
| 4.8 | Add payout export (CSV/JSON) | 🟢 P3 | 3h | For tax/accounting purposes |

---

### Epic 5: Frontend & User Experience (Sprint 4-8)
*People need to see what's happening*

| # | Task | Priority | Est. | Notes |
|---|------|----------|------|-------|
| 5.1 | Build streamer dashboard | 🟠 P1 | 16h | Stream status, node count, bandwidth savings |
| 5.2 | Build friend node dashboard | 🟠 P1 | 12h | Earnings, bandwidth contributed, trust score |
| 5.3 | Build viewer page | 🟠 P1 | 8h | HLS player with stream selection |
| 5.4 | Build admin dashboard | 🟡 P2 | 12h | System health, all streams, all nodes |
| 5.5 | Add real-time updates (WebSocket/SSE) | 🟡 P2 | 8h | Live node count, earnings ticker |
| 5.6 | Build onboarding flow | 🟡 P2 | 8h | Step-by-step friend setup wizard |
| 5.7 | Mobile-responsive design | 🟡 P2 | 6h | Dashboard works on phones |

---

### Epic 6: Observability & Operations (Sprint 2-4)
*You can't fix what you can't see*

| # | Task | Priority | Est. | Notes |
|---|------|----------|------|-------|
| 6.1 | Add CloudWatch alarms | 🟠 P1 | 4h | CPU, memory, error rates, 5xx responses |
| 6.2 | Add structured logging | 🟠 P1 | 4h | JSON logs with correlation IDs |
| 6.3 | Add health check for background worker | 🟠 P1 | 2h | Ensure stats collector and prober are running |
| 6.4 | Add ECS auto-scaling | 🟡 P2 | 4h | Scale based on active streams/nodes |
| 6.5 | Add database performance indexes | 🟡 P2 | 2h | Apply the planned but unapplied indexes |
| 6.6 | Add WAF to ALB | 🟡 P2 | 3h | Basic web application firewall |
| 6.7 | Move database to private subnet | 🟡 P2 | 4h | Enable NAT gateway for gamma/prod |

---

### Epic 7: Testing & Quality (Sprint 2-6)
*Build confidence before inviting friends*

| # | Task | Priority | Est. | Notes |
|---|------|----------|------|-------|
| 7.1 | Unit tests for payout_service | 🟠 P1 | 4h | Test contribution weighting, penalties |
| 7.2 | Unit tests for stats_collector | 🟠 P1 | 3h | Test validation logic, error handling |
| 7.3 | Unit tests for spot_check_prober | 🟠 P1 | 3h | Test fraud detection, node flagging |
| 7.4 | Integration test for bandwidth reporting | 🟠 P1 | 4h | End-to-end bandwidth flow |
| 7.5 | Go client unit tests | 🟠 P1 | 6h | Test registration, heartbeat, relay |
| 7.6 | Load test coordinator | 🟡 P2 | 6h | Simulate 50+ nodes reporting |
| 7.7 | End-to-end P2P relay test | 🟡 P2 | 8h | Full stream → relay → viewer test |

---

### Epic 8: Friend Testing Program (Sprint 6-8)
*The moment of truth*

| # | Task | Priority | Est. | Notes |
|---|------|----------|------|-------|
| 8.1 | Write friend setup guide (updated) | 🟠 P1 | 3h | Step-by-step with Go binary |
| 8.2 | Create feedback collection system | 🟠 P1 | 4h | Anonymous form or in-app feedback |
| 8.3 | Set up 5-friend test network | 🔴 P0 | 4h | Recruit and onboard 5 friends |
| 8.4 | Run 1-week validation test | 🔴 P0 | Ongoing | Monitor stability, collect feedback |
| 8.5 | Implement session summaries | 🟡 P2 | 6h | Post-session email/notification |
| 8.6 | Add anonymous feedback endpoint | 🟡 P2 | 3h | Per Community Catalyst guidance |

---

## 6. Recommended Sprint Plan

### Sprint 1 (Weeks 1-2): Foundation
- Epic 1 (all P0 items): Auth, migrations, security cleanup
- Epic 6.1-6.3: Basic observability

### Sprint 2 (Weeks 3-4): Go Client Core
- Epic 2.1-2.7: Registration, heartbeat, HLS fetch/serve, bandwidth reporting
- Epic 7.1-7.3: Unit tests for existing services

### Sprint 3 (Weeks 5-6): Economics + VPN
- Epic 4.1-4.3: Real bandwidth verification, trust scores
- Epic 3.2: VPN mesh deployment (Headscale)

### Sprint 4 (Weeks 7-8): P2P Relay
- Epic 3.1, 3.3-3.4: Chunk distribution, peer relay, viewer routing
- Epic 3.6: SRS fallback

### Sprint 5 (Weeks 9-10): Frontend + Polish
- Epic 5.1-5.3: Streamer, friend, and viewer dashboards
- Epic 4.4-4.5: Payout scheduling, earnings history

### Sprint 6 (Weeks 11-12): Friend Testing
- Epic 8.1-8.4: Setup guides, feedback system, 5-friend test
- Epic 7.7: End-to-end P2P test

**Total estimated timeline**: ~12 weeks to friend-testable P2P streaming

---

## 7. Key Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| VPN mesh adds latency | Stream quality degrades | Benchmark Headscale latency early (Sprint 3) |
| HLS segment relay adds buffering | Viewer experience suffers | Test with 2s segments instead of 10s |
| Friends don't install Go binary | No test network | Provide native installers (.msi, .dmg, .deb) |
| Economic model doesn't motivate | Friends stop running nodes | Validate $0.05/GB rate feels fair in testing |
| 13-month gap means infrastructure drift | AWS resources may have changed | Verify all endpoints still work before coding |
| No HTTPS means ISP interference | Streams blocked or degraded | Add TLS in Sprint 1 |

---

## 8. Investigation Backlog

### 8.1 — Deployment Drops RTMP Stream Without OBS Error

**Discovered**: Phase 8 E2E testing (2026-02-28, commit `69cc87f`)

**Symptoms**:
- OBS shows "Live" throughout the entire ECS rolling deployment — no error, no disconnect indicator
- After deployment completes, VLC viewer fails (empty HLS master playlist, no segments)
- OBS still thinks it's streaming; user can click "End Stream" normally
- Restarting the stream in OBS after deploy restores HLS playback

**Root Cause (hypothesis)**:
- ECS rolling update stops the old task (kills SRS container), NLB deregisters the old target
- The NLB TCP connection to OBS doesn't cleanly RST — OBS keeps sending RTMP data into a half-open socket
- New SRS container starts fresh with no RTMP publisher, so no HLS segments are generated
- The stale master playlist (`#EXT-X-STREAM-INF` with no variant URL) persists from the old SRS instance's initial publish

**Impact**: Medium — streamers must manually restart OBS after every deploy. Friends testing will hit this.

**Investigation needed**:
1. Check NLB connection draining settings (default 300s) — does it send RST to existing connections?
2. Check if OBS auto-reconnect is enabled by default and whether it detects the dead connection
3. Consider adding a pre-deploy webhook that sends RTMP disconnect to OBS (not standard)
4. Consider `minimumHealthyPercent: 100` + `maximumPercent: 200` on ECS service to keep old task alive until new one is healthy (but RTMP state still can't migrate)
5. Long-term: evaluate blue/green deployment with DNS switchover for zero-downtime streaming

**Workaround**: Restart stream in OBS after each deployment.

---

## 9. First Action: Verify Current State

Before writing any code, run these checks:

```bash
# 1. Verify infrastructure is still running
curl http://streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com/health

# 2. Verify RTMP endpoint
curl -v rtmp://52.213.32.59:1935

# 3. Verify database has expected schema
# (via operational bastion or direct connection)

# 4. Verify CI/CD pipeline still works
# Push a trivial change and watch GitHub Actions

# 5. Run existing smoke tests
TEST_TARGET=production python -m pytest tests/test_production_smoke.py -v
```

If any of these fail, fix them before starting new development.
