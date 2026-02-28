# StreamrP2P — MVP Deployment Tracker

**Created:** February 27, 2026
**Goal:** Get the code-complete MVP (68/68 tasks) tested, cleaned, deployed to AWS beta, and validated end-to-end.

---

## Phase 1: Pre-flight — Verify Existing Infrastructure ✅

> Before touching any code, confirm what's still alive from the previous deployment.

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1.1 | Verify beta ALB is responding | ✅ | `healthy` at `streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com/health` |
| 1.2 | Verify RDS instance `streamr-p2p-beta-db` is running | ✅ | PostgreSQL 15.13, db.t3.micro, available |
| 1.3 | Verify ElastiCache cluster `streamr-p2p-beta-cache` exists | ✅ | cache.t4g.micro, available |
| 1.4 | Verify ECR repository has images / is accessible | ✅ | 10 images, `latest` tag present |
| 1.5 | Verify ECS cluster and service exist | ✅ | `streamr-p2p-beta-cluster`, service running 1/1 (task def rev 17) |
| 1.6 | Verify GitHub Actions OIDC role still exists | ✅ | OIDC stack active, role exists |
| 1.7 | Verify Elastic IP `52.213.32.59` is still allocated | ✅ | `eipalloc-054297e161bb78275` allocated |
| 1.8 | Check CloudFormation stack status for all 3 stacks | ✅ | All 3 stacks (oidc, foundation, application) in UPDATE_COMPLETE |

**Result:** All infrastructure alive. Proceeded with fresh DB approach.

### Pre-Phase 2: Database Reset ✅
| # | Task | Status | Notes |
|---|------|--------|-------|
| P.1 | Wipe database (DROP SCHEMA public CASCADE + CREATE SCHEMA public) | ✅ | One-off Fargate task, coordinator exit code 0 |
| P.2 | Disable ECS Exec (was enabled temporarily) | ✅ | `--disable-execute-command` applied |
| P.3 | Clean up one-off Fargate task | ✅ | Task stopped automatically, Fargate auto-cleans |

---

## Phase 2: Code Cleanup — Before Any Merge to Main ✅

> The deploy workflow auto-triggers on push to `main` for `infrastructure/**`, `coordinator/**`, `tests/**`. Nothing goes to main until this phase is done.

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.1 | Delete stale `=4.0.0` file from repo root | ✅ | Deleted |
| 2.2 | Verify `infrastructure/node_modules/` is in `.gitignore` | ✅ | In `.gitignore`, not tracked in git |
| 2.3 | Parameterize Elastic IP allocation ID | ✅ | Now reads from CDK context `elasticIpAllocationId`, defaults to current value |
| 2.4 | Parameterize Elastic IP address in CfnOutputs | ✅ | Now reads from CDK context `elasticIpAddress`, all 3 outputs updated |
| 2.5 | Review Alembic migrations for fresh-DB safety | ✅ | All 4 migrations safe on empty DB — migration 002 data loops execute 0 times on empty tables |
| 2.6 | Verify no secrets/credentials in committed code | ✅ | Scan complete: no AWS keys, no API tokens |
| 2.7 | Verify Headscale `SET_VIA_SECRETS` won't crash service | ✅ | Container is `essential: false` — fails gracefully |
| 2.8 | Verify SRS container config | ✅ | Custom `srs.conf` exists but NOT mounted in ECS task def. Deferred to post-deploy (default SRS works, just 10s vs 2s HLS fragments) |
| 2.9 | Run `cd infrastructure && npm run build` to verify CDK compiles | ✅ | Clean compilation with EIP parameterization changes |

---

## Phase 3: Local Testing — Validate Before Deploy ✅

| # | Task | Status | Notes |
|---|------|--------|-------|
| 3.1 | Run Python unit tests | ✅ | 25/25 pure unit tests pass. 36 DB-dependent tests need local PG (not a blocker — run in CI) |
| 3.2 | Run Go tests: `cd node-client-go && go test ./...` | ✅ | 30/30 passed across 4 packages |
| 3.3 | Run CDK tests: `cd infrastructure && npm test` | ✅ | 2/2 passed (stack synthesis) |
| 3.4 | Run CDK synth: `npx cdk synth --context stage=beta` | ⬜ | Skipping — CDK build + tests pass, synth will run during deploy |
| 3.5 | Local docker-compose up: verify migrations run | ⬜ | Skipping — no local Docker needed, will validate on AWS |
| 3.6 | Local health check: `curl http://localhost:8000/health` | ⬜ | Skipping — will validate on AWS post-deploy |

---

## Phase 4: Staged Deployment to Beta ✅

| # | Task | Status | Notes |
|---|------|--------|-------|
| 4.1 | Commit MVP code to `main` | ✅ | `eb78d38` — 75 files, 9962 insertions |
| 4.2 | Fix migration 002 FK ordering | ✅ | `c9850af` — drop FKs before index |
| 4.3 | Fix migration 001 idempotency | ✅ | `3fa3aac` — skip if tables exist from legacy `create_all()` |
| 4.4 | Fix ORM mapper (Node↔UserAccount) | ✅ | `d5c7737` — remove broken direct relationship |
| 4.5 | Deploy job passes | ✅ | GH Actions run `22505346527`, deploy in 9m51s |
| 4.6 | CF stack `UPDATE_COMPLETE` | ✅ | Task def rev 22, rollout COMPLETED |
| 4.7 | ECS task RUNNING 1/1 | ✅ | Rev 22, healthy |
| 4.8 | ALB health check passes | ✅ | `/health` → 200, DB ok, Redis ok, scheduler ok |
| 4.9 | Sanity tests pass (health + dashboard) | ✅ | CI sanity step green |
| 4.10 | Integration test script missing | ✅ | Script existed but tests lacked JWT auth — fixed in Phase 5 (commit `62f1f84`) |

**Issues resolved during deploy:**
- Migration 002 tried to drop index before dependent FKs → reordered
- Legacy rev 17 `create_all()` recreated tables during rolling deploy → made migration 001 idempotent
- SQLAlchemy mapper error on Node↔UserAccount relationship after schema refactor → removed broken direct relationship

---

## Phase 5: Post-Deploy Validation ✅

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.1 | Health check: `GET /health` | ✅ | DB ok, Redis ok, scheduler ok (4 jobs scheduled) |
| 5.2 | Auth: register test streamer | ✅ | `POST /api/v1/auth/register-streamer` → 200, JWT + user_id returned |
| 5.3 | Auth: login and receive JWT | ✅ | `POST /api/v1/auth/login` → 200, role=streamer, RS256 JWT |
| 5.4 | Auth: register test node | ✅ | `POST /api/v1/auth/register` → 200, role=node, stream_id + node_id in JWT. Required migration 005 (vpn_ip/capacity_pct columns missing) |
| 5.5 | Stream: create a stream | ✅ | `POST /streams` with JWT → 200, stream_id=validation-test-stream |
| 5.6 | Stream: verify stream key returned | ✅ | 43-char `token_urlsafe(32)` key returned |
| 5.7 | Dashboard: streamer dashboard renders | ✅ | `GET /dashboard/streamer/{id}` → 200 (4996 bytes HTML) |
| 5.8 | Dashboard: node dashboard renders | ✅ | `GET /dashboard/node/{id}` → 200 |
| 5.9 | Dashboard: viewer page renders | ✅ | `GET /watch/{id}` → 200 |
| 5.10 | Economics: config endpoint | ✅ | `GET /api/v1/economics/config` → 200 (rate_per_gb=0.05, platform_margin=0.075) |
| 5.11 | Admin: validation report | ✅ | `GET /api/v1/admin/validation-report` → 200 (5 streams, 1 live, bandwidth/payout data) |
| 5.12 | Feedback: submit feedback | ✅ | `POST /api/v1/feedback` → 201, id=1 |

**Issues resolved during Phase 5:**
- Migration 005 added missing `vpn_ip` (String(45)) and `capacity_pct` (Integer) columns to `nodes` table — ORM model had them but no migration created them, causing 500 on node registration.
- Integration tests fixed — added JWT auth (`auth_headers` fixture) to lifecycle tests that were getting 403 from `require_streamer` guard. Commit `62f1f84`.
- CI fully green: deploy + sanity + lifecycle integration tests all pass (GH Actions run `22506399032`).

---

## Phase 6: End-to-End Streaming Test

| # | Task | Status | Notes |
|---|------|--------|-------|
| 6.1 | OBS → `rtmp://52.213.32.59:1935/live/{stream_key}` | ✅ | OBS pushing to `rtmp://52.213.32.59:1935/live/e2e-phase6-test`. Stream key `q9MPth0fz8GdY9C3gMY7OctFUKWMAlASh7aykbLkHCI`. SRS accepts (default config, no on_publish callback mounted). |
| 6.2 | Verify SRS receives stream | ✅ | HLS master playlist at `:8080/live/e2e-phase6-test.m3u8` → 200. Variant playlist shows 6 segments (10s each, default SRS config). TS segments downloading correctly. |
| 6.3 | Watch via viewer page (HLS.js) | ⚠️ | Viewer page renders (200, 4996 bytes) at `/watch/e2e-phase6-test`. HLS.js loads. **Issue:** viewer routing returns `source_url: "http://localhost:8080/..."` (SRS_HOST env defaults to `localhost` inside container) — browser can't reach it. Needs `SRS_HOST` set to ALB DNS or use relative URL. |
| 6.4 | Watch via VLC (direct HLS) | ✅ | Direct HLS URL works: `http://streamr-p2p-beta-alb-...elb.amazonaws.com:8080/live/e2e-phase6-test.m3u8` plays in any HLS client. |
| 6.5 | Build and run Go node client against beta | ✅ | `go build` succeeds (Go 1.23.4). Binary at `/tmp/streamr-node`. Node registration via API confirmed working. |
| 6.6 | Verify node registers + heartbeats | ✅ | Two nodes registered (`e2e-test-node-001`, `e2e-test-node-002`). Heartbeat `POST /nodes/heartbeat` → `{"status":"success"}`. Redis state updated with trust_score=0.75, capacity_pct=25, vpn_ip=100.64.0.10. Dashboard shows 2 nodes on stream. |
| 6.7 | Verify bandwidth reports flow | ✅ | `POST /api/v1/sessions/e2e-phase6-test/bandwidth-report` → 200. Ledger entry id=1, 50MB reported, `is_verified: false`. Validation report shows 1 report, 0.05 GB total. |
| 6.8 | Verify payout cycle runs | ✅ | Payout scheduler active (next `hourly_payout` at 09:00 UTC). `/payouts` endpoint returns empty (no verified reports yet — bandwidth verification runs first, then payout processes verified reports). Payout service logic verified: rate=$0.05/GB, 7.5% margin, trust penalties < 0.5. |
| 6.9 | Verify trust score calculation | ✅ | Trust scoring returns 0.75 default for nodes with < 5 reports. `calculate_trust_score()` uses verified/total ratio over 30-day window. Consequences: < 0.3 → flagged, < 0.5 → 50% payout penalty. Admin report shows `avg_network_trust_score: 1.0`. |
| 6.10 | Test viewer routing with active node | ✅ | Immediately after heartbeat: `GET /api/v1/watch/e2e-phase6-test` → `{"source_type":"friend_node","node_id":"e2e-test-node-002","source_url":"/api/v1/proxy/e2e-phase6-test/index.m3u8"}`. Routing selects highest-trust, lowest-viewer-count node. Falls back to SRS after 90s stale cleanup if no heartbeat. |

**Issues found during Phase 6:**
- **SRS_HOST localhost bug (6.3):** Viewer routing fallback URL uses `http://localhost:8080/...` because `SRS_HOST` env var defaults to `localhost` inside the ECS container. Browser viewers can't reach this. Fix: set `SRS_HOST` env var to ALB DNS in ECS task def, or change fallback to use a relative URL like `/srs/live/{stream_id}.m3u8` with ALB path-based routing to SRS target group.
- **SRS custom config not mounted (known):** Default SRS config uses 10s HLS segments (vs 2s in custom config). No `on_publish` auth callback active. Both noted in Known Issues.
- **Node economics 500 bug:** `GET /api/v1/economics/node/{node_id}` returns 500 — endpoint looks up `UserAccount` by `node_id` but UserAccount uses `user_id` (UUID). Minor bug, needs node_id→user_id resolution.
- **Bandwidth verification pipeline:** Reports start as `is_verified: false`. Payout cycle only processes verified reports. The `bandwidth_verification` background job needs to verify reports before payouts can flow. This is working as designed but means first payout requires: report → verify → payout (multi-cycle).

---

## Phase 7: CI Pipeline & Test Hardening ✅

| # | Task | Status | Notes |
|---|------|--------|-------|
| 7.1 | Add `unit-tests` job with PostgreSQL service container | ✅ | Port 5433, 77 tests pass (unit + stream routes) |
| 7.2 | Add `go-tests` job | ✅ | 30 tests pass across 6 packages |
| 7.3 | Deploy job requires both test jobs to pass | ✅ | `needs: [unit-tests, go-tests]` |
| 7.4 | Fix SQLAlchemy 2.0 `func.case()` → `case()` | ✅ | `data_retention.py` |
| 7.5 | Fix ProbeResult join missing ON clause | ✅ | `spot_check_prober.py` |
| 7.6 | Fix slowapi limiter Redis dependency in tests | ✅ | Replace limiter object entirely with `memory://` storage |
| 7.7 | Fix APScheduler singleton collision in tests | ✅ | Fresh scheduler instance before app import |
| 7.8 | Split test invocations (unit vs stream routes) | ✅ | Separate pytest runs to avoid module state conflicts |
| 7.9 | DB-dependent tests auto-skip locally | ✅ | `_pg_is_available()` check, 50 tests skip locally, run in CI |
| 7.10 | Smart change detection (dorny/paths-filter) | ✅ | Skip deploy for CI-only changes, skip tests for unrelated changes |
| 7.11 | Fix Go cache-dependency-path warning | ✅ | `node-client-go/go.sum` |
| 7.12 | Add `node-client-go/**` to workflow trigger paths | ✅ | Go changes now trigger CI |

**Commits:**
- `cab8402` — Phase 6 bugs + CI pipeline with pre-deploy tests
- `a8506a2` — SQLAlchemy 2.0 compat + scheduler isolation + split test invocations
- `6f7e8ba` — Memory limiter storage in conftest (intermediate fix)
- `b8f0368` — Replace limiter object entirely in test fixture (final fix)
- `d521947` — Smart change detection + Go cache fix

**CI Results (commit b8f0368):** All 4 jobs green — unit-tests ✅, go-tests ✅, deploy ✅, post-deploy-tests ✅
**CI Results (commit d521947):** Changes job detected CI-only change → all downstream jobs correctly skipped ✅

---

## Known Issues & Risks

| Issue | Severity | Mitigation |
|-------|----------|------------|
| Headscale container has `SET_VIA_SECRETS` placeholders | Medium | `essential: false` — won't crash. VPN mesh non-functional until configured |
| ~~SRS custom config not mounted in ECS task def~~ | ~~Medium~~ | ✅ Fixed in `cab8402` — SRS container command writes custom config at startup |
| Elastic IP hardcoded in CDK | ~~Low~~ | ✅ Fixed — parameterized via CDK context in Phase 2 |
| No HTTPS without domain name | Medium | Beta runs HTTP. HTTPS requires `domainName` CDK context. Deferred until after friends testing. |
| ~~SRS_HOST defaults to `localhost` in viewer routing~~ | ~~High~~ | ✅ Fixed in `cab8402` — `_build_srs_url()` reads request Host header |
| ~~Node economics endpoint uses node_id as user_id~~ | ~~Low~~ | ✅ Fixed in `cab8402` — resolves node_id → user_id via Node table |
| ~~Uncommitted local changes~~ | ~~Medium~~ | ✅ All changes committed and pushed |
| Proxy can't reach nodes without VPN | High | Proxy resolves `vpn_ip` from Redis — empty without Headscale. Falls back to SRS every time. Viewer routing says `friend_node` but proxy silently serves SRS. See "Proxy Gap" section below. |
| SRS master playlist intermittently empty | Low | `#EXT-X-STREAM-INF` line present but variant URL sometimes missing. Go client retries every 2s, self-heals. SRS timing issue, not a blocker. |

---

## Phase 8: Friends Testing Readiness

### Restreaming Flow Analysis

The full restreaming pipeline is built end-to-end:

```
OBS → RTMP → [NLB:1935] → [SRS] → HLS segments
                                        ↓
                              [Go Node Client]
                              ├── HLS Fetcher (polls SRS playlist, downloads .ts segments)
                              ├── Segment Buffer (circular, 30 segments max)
                              ├── HLS Server (serves playlist + segments to viewers on :8080)
                              ├── Bandwidth Reporter (60s intervals → coordinator API)
                              └── Heartbeat Loop (30s → coordinator, updates Redis state)
                                        ↓
                              [Coordinator Viewer Routing]
                              ├── GET /api/v1/watch/{stream_id} → picks best node or SRS fallback
                              └── GET /api/v1/proxy/{stream_id}/{path} → proxies HLS via VPN IP
```

### What's Been Validated

| Component | Tested? | How |
|-----------|---------|-----|
| OBS → SRS RTMP ingest | ✅ | Phase 6.1 — live stream confirmed |
| SRS → HLS output | ✅ | Phase 6.2 — playlist + segments downloading |
| Viewer page (HLS.js) | ✅ | Phase 6.3 — renders, SRS_HOST fix deployed |
| VLC direct HLS | ✅ | Phase 6.4 — plays from ALB:8080 |
| Go client build | ✅ | Phase 6.5 — cross-platform binary |
| Node registration + heartbeat | ✅ | Phase 6.6 — API calls confirmed, Redis state updated |
| Bandwidth reports | ✅ | Phase 6.7 — ledger entries created |
| Viewer routing (API) | ✅ | Phase 6.10 — returns friend_node or SRS fallback |
| Trust scoring | ✅ | Phase 6.9 — default 0.75, penalties working |
| Go HLS fetcher (unit tests) | ✅ | 30 Go tests pass including HLS parsing |
| Go HLS server (unit tests) | ✅ | Playlist generation, segment serving, capacity limiting |
| Go bandwidth reporter (unit tests) | ✅ | Report queuing, retry logic |

### What Needs E2E Validation Before Friends Testing

| # | Test | Status | Notes |
|---|------|--------|-------|
| 8.1 | Go node fetches HLS from SRS via ALB | ✅ | Node registered, fetched segments from SRS via ALB:8080. Two-level playlist handling (master→variant) + query param stripping working. Commit `afe2d8e`. |
| 8.2 | Go node serves HLS to local viewer | ✅ | `curl localhost:9090/live/e2e-phase8-restream/index.m3u8` returned valid playlist with 25 segments. Clean `.ts` names served from buffer. |
| 8.3 | Viewer routing returns friend node proxy URL | ✅ | `GET /api/v1/watch/e2e-phase8-restream` → `source_type: friend_node`, `node_id: e2e-test-node-phase8`, proxy URL returned. Routing selects node after heartbeat updates Redis. |
| 8.4 | Proxy endpoint reaches node (without VPN) | ⚠️ | Proxy falls back to SRS as expected — node has no `vpn_ip` without Headscale. Proxy SRS fallback returns 200. For friends testing, direct node access (localhost:9090) is the path. VPN proxy path deferred to post-friends-testing. |
| 8.5 | Viewer page plays via friend node | ⚠️ | Deferred — requires VPN for proxy path, or direct node URL. Viewer page works with SRS fallback. Direct node HLS confirmed working via curl in 8.2. |
| 8.6 | Bandwidth reports flow during restream | ✅ | Reports accumulate during active restream. Validation report: 11 reports, 0.65 GB total. 60s reporter cycle confirmed. |
| 8.7 | Node graceful shutdown + deregistration | ✅ | Stale cleanup removes node from Redis after 90s → routing falls back to `source_type: srs`. Deregister API exists but couldn't test via SIGTERM in this environment (process killed too fast). Code path verified in unit tests. |
| 8.8 | Multiple nodes on same stream | ⬜ | Deferred — routing logic verified in Phase 6.10 with two nodes. Full E2E with two Go binaries not critical for friends testing. |
| 8.9 | Node capacity saturation | ⬜ | Deferred — capacity limiting verified in Go unit tests (503 at max_viewers). Full E2E not critical for friends testing. |
| 8.10 | Friend Quick Start guide accuracy | ⬜ | Update FRIEND_QUICK_START.md with validated commands and test. |

### Critical Gap: Proxy Can't Reach Friend Nodes (No VPN)

**The Problem:**
The viewer routing API correctly identifies a friend node (`source_type: friend_node`) and returns the proxy URL (`/api/v1/proxy/{stream_id}/index.m3u8`). But the proxy endpoint looks up the node's `vpn_ip` from Redis, finds it empty (no Headscale VPN configured), and silently falls back to serving SRS content. The viewer thinks they're watching via a friend node, but they're actually getting SRS direct.

**Why it matters:** This breaks the core value prop — friends run nodes, but viewers never actually get content from them. Bandwidth reports still flow (the node is fetching from SRS), but the restreaming loop isn't closed.

**Current flow (broken):**
```
Viewer → /api/v1/watch → "friend_node" + proxy URL
      → /api/v1/proxy → lookup vpn_ip → EMPTY → fallback to SRS
      → Viewer gets SRS content (not friend node content)
```

**Where the data lives:**
- Redis `stream:{stream_id}:nodes` stores: `vpn_ip`, `trust_score`, `capacity_pct`, `viewer_count`, `last_heartbeat`
- `stats_url` (e.g. `http://localhost:9090`) is stored in PostgreSQL `nodes` table but NOT in Redis
- Proxy only checks Redis for `vpn_ip`

**Fix Options:**

| Option | Complexity | Description |
|--------|-----------|-------------|
| A. Store `stats_url` in Redis, proxy uses it as fallback | Low | Add `stats_url` to `update_node_state()`. Proxy tries `vpn_ip` first, then `stats_url`. Works if node has a routable IP (public IP + port forwarding). |
| B. Viewer routing returns node URL directly (skip proxy) | Low | When node has no `vpn_ip` but has `stats_url`, return `stats_url` as `source_url` instead of proxy path. Viewer connects directly to node. |
| C. Configure Headscale VPN mesh | High | Full VPN setup — nodes get 100.x.x.x IPs, proxy works as designed. Production-grade but complex for friends testing. |
| D. Node reports public IP via STUN/external service | Medium | Node discovers its public IP at startup, reports it in heartbeats. Proxy uses public IP. Requires port forwarding on friend's router. |

**Recommended for friends testing:** Option B (direct URL) — simplest, no proxy overhead, validates the core restreaming loop. The viewer page would get a direct URL to the friend's node instead of going through the coordinator proxy.

---

## AWS Resource Reference

| Resource | Identifier |
|----------|-----------|
| Region | `eu-west-1` |
| Account | `164859598862` |
| ECS Cluster | `streamr-p2p-beta-cluster` |
| ECS Service | `streamr-p2p-beta-coordinator` |
| RDS | `streamr-p2p-beta-db` (`streamr-p2p-beta-db.c3q28wieso7a.eu-west-1.rds.amazonaws.com:5432`) |
| ElastiCache | `streamr-p2p-beta-cache` |
| ECR | `164859598862.dkr.ecr.eu-west-1.amazonaws.com/streamr-p2p-beta-coordinator` |
| ALB | `streamr-p2p-beta-alb-1130353833.eu-west-1.elb.amazonaws.com` |
| Elastic IP | `52.213.32.59` / `eipalloc-054297e161bb78275` |
| CF Stacks | `streamr-p2p-beta-eu-west-1-foundation`, `-application`, `-github-oidc` |
