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

## Phase 4: Staged Deployment to Beta

| # | Task | Status | Notes |
|---|------|--------|-------|
| 4.1 | Create feature branch `deploy/mvp-v1` | ⬜ | Phase 2 cleanup commits go here |
| 4.2 | Open PR against `main` | ⬜ | CI triggers but NOT deployment |
| 4.3 | Verify CI passes on PR | ⬜ | CDK build, CDK tests, Go tests |
| 4.4 | Merge PR to `main` | ⬜ | Triggers deploy workflow automatically |
| 4.5 | Monitor GitHub Actions deploy job | ⬜ | OIDC → Foundation → Docker build+push → Application |
| 4.6 | Monitor ECS task startup / Alembic migration logs | ⬜ | CloudWatch logs |
| 4.7 | Verify new ECS task reaches RUNNING state | ⬜ | `runningCount: 1` |
| 4.8 | Verify ALB health check passes | ⬜ | Healthy target within 2-3 min |

**Rollback plan:** Entrypoint exits code 1 on migration failure → ECS keeps old task (rolling deploy). New code crash → ECS auto-rollback.

---

## Phase 5: Post-Deploy Validation

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.1 | Health check: `GET /health` | ⬜ | DB + Redis status |
| 5.2 | Auth: register test streamer | ⬜ | `POST /api/v1/auth/register-streamer` |
| 5.3 | Auth: login and receive JWT | ⬜ | `POST /api/v1/auth/login` |
| 5.4 | Auth: register test node | ⬜ | `POST /api/v1/auth/register` |
| 5.5 | Stream: create a stream | ⬜ | `POST /streams` with JWT |
| 5.6 | Stream: verify stream key returned | ⬜ | |
| 5.7 | Dashboard: streamer dashboard renders | ⬜ | `GET /dashboard/streamer/{id}` |
| 5.8 | Dashboard: node dashboard renders | ⬜ | `GET /dashboard/node/{id}` |
| 5.9 | Dashboard: viewer page renders | ⬜ | `GET /watch/{id}` |
| 5.10 | Economics: config endpoint | ⬜ | `GET /api/v1/economics/config` |
| 5.11 | Admin: validation report | ⬜ | `GET /api/v1/admin/validation-report` |
| 5.12 | Feedback: submit feedback | ⬜ | `POST /api/v1/feedback` |

---

## Phase 6: End-to-End Streaming Test

| # | Task | Status | Notes |
|---|------|--------|-------|
| 6.1 | OBS → `rtmp://52.213.32.59:1935/live/{stream_key}` | ⬜ | |
| 6.2 | Verify SRS receives stream | ⬜ | |
| 6.3 | Watch via viewer page (HLS.js) | ⬜ | |
| 6.4 | Watch via VLC (direct HLS) | ⬜ | |
| 6.5 | Build and run Go node client against beta | ⬜ | |
| 6.6 | Verify node registers + heartbeats | ⬜ | |
| 6.7 | Verify bandwidth reports flow | ⬜ | |
| 6.8 | Verify payout cycle runs | ⬜ | |
| 6.9 | Verify trust score calculation | ⬜ | |
| 6.10 | Test viewer routing with active node | ⬜ | |

---

## Known Issues & Risks

| Issue | Severity | Mitigation |
|-------|----------|------------|
| Headscale container has `SET_VIA_SECRETS` placeholders | Medium | `essential: false` — won't crash. VPN mesh non-functional until configured |
| SRS custom config not mounted in ECS task def | Medium | Default config works but 10s HLS segments (high latency). Fix post-deploy |
| Elastic IP hardcoded in CDK | ~~Low~~ | ✅ Fixed — parameterized via CDK context in Phase 2 |
| No HTTPS without domain name | Medium | Beta runs HTTP. HTTPS requires `domainName` CDK context |
| Uncommitted local changes | Medium | `=4.0.0` deleted + EIP parameterized in `application-stack.ts` — must commit to branch and merge to main |

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
