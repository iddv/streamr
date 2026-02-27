# StreamrP2P

Live streaming is expensive. A single streamer pushing 8 Mbps to 100 viewers burns through bandwidth fast, and the bill lands squarely on the creator. CDNs help, but they're built for scale — not for the indie streamer with a loyal audience of 50.

StreamrP2P flips the model. Your friends run lightweight relay nodes that redistribute your stream to other viewers, like BitTorrent but for live video. They earn rewards for the bandwidth they contribute. You save money. Viewers get a faster, more resilient stream. Everyone wins.

## How it works

```
                    ┌──────────┐
   OBS/Streaming    │  Ingest  │     HLS chunks
   Software ──RTMP──▶  Server  ├──────────────┐
                    │  (SRS)   │               │
                    └──────────┘               ▼
                                        ┌─────────────┐
                                        │ Coordinator  │
                                        │   (API)      │
                                        └──────┬──────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          ▼                    ▼                    ▼
                    ┌───────────┐        ┌───────────┐       ┌───────────┐
                    │  Friend   │        │  Friend   │       │  Direct   │
                    │  Node A   │        │  Node B   │       │  Viewer   │
                    └─────┬─────┘        └─────┬─────┘       └───────────┘
                          │                    │
                     ┌────┴────┐          ┌────┴────┐
                     │ Viewer  │          │ Viewer  │
                     │ Viewer  │          │ Viewer  │
                     └─────────┘          └─────────┘
```

1. You stream via OBS to the ingest server (RTMP)
2. The coordinator tracks which friend nodes are online and healthy
3. Friend nodes pull HLS chunks and serve them to nearby viewers
4. The coordinator calculates bandwidth contributions and distributes rewards
5. Viewers connect through the best available source automatically

## Three roles, one network

**Streamers** register, create a stream, and get an RTMP ingest URL and a stream key. Point OBS at it and go live. Share the stream key with friends you trust.

**Friends** run a small Go binary (~5MB) that connects to the coordinator, pulls stream chunks, and serves them to viewers. No Docker, no complex setup — just download and run. They earn $0.05/GB relayed, verified by the coordinator's anti-fraud system.

**Viewers** open a URL in their browser. HLS.js handles playback. They're automatically routed to the best source — a friend node if one's available, or the origin server as fallback.

## Getting started

### Stream something

```bash
# 1. Register as a streamer
curl -X POST https://your-coordinator/api/v1/auth/register-streamer \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "...", "display_name": "YourName"}'

# 2. Login and grab your token
curl -X POST https://your-coordinator/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "..."}'
# → {"token": "eyJ...", "user_id": "...", "role": "streamer"}

# 3. Create a stream
curl -X POST https://your-coordinator/streams \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stream_id": "my-stream", "rtmp_url": "rtmp://ingest-ip:1935/live/my-stream"}'
# → {"stream_key": "abc123...", ...}

# 4. Configure OBS
#    Server:     rtmp://ingest-ip:1935/live/my-stream
#    Stream Key: ?key=abc123...
```

### Run a friend node

```bash
# Download the binary for your platform from releases
./streamr-node \
  -coordinator https://your-coordinator \
  -stream-key abc123... \
  -node-id my-node
```

That's it. The node registers itself, starts pulling chunks, and begins serving viewers. Earnings accumulate automatically.

### Watch a stream

Open `https://your-coordinator/watch/my-stream` in any browser. The viewer page uses HLS.js with automatic source selection and reconnection.

## Run it yourself

### Prerequisites

- AWS account (infrastructure runs on CDK)
- Node.js 18+ (for CDK)
- Python 3.8+ (for the coordinator)
- Go 1.23+ (for building the node client)
- Docker (for local development)

### Infrastructure

```bash
cd infrastructure
npm ci
npx cdk deploy --all --context stage=beta
```

This creates the full stack: VPC, RDS (PostgreSQL), ElastiCache (Redis), ECS (Fargate), ALB, and an Elastic IP for RTMP ingest.

### Coordinator (local dev)

```bash
cd coordinator
docker-compose up -d          # PostgreSQL + Redis
alembic upgrade head          # Run migrations
uvicorn app.main:app --reload # Start the API
```

### Node client

```bash
cd node-client-go
go build -o streamr-node ./cmd/streamr-node
./streamr-node -coordinator http://localhost:8000 -debug
```

### Tests

```bash
# Python unit tests
cd coordinator && python -m pytest tests/unit/ -v

# Go tests
cd node-client-go && go test ./...

# CDK tests
cd infrastructure && npm test

# Integration tests against a live coordinator
./scripts/run-integration-tests.sh http://your-coordinator smoke
./scripts/run-integration-tests.sh http://your-coordinator lifecycle
```

## Architecture

| Component | Tech | Purpose |
|-----------|------|---------|
| Coordinator | FastAPI, PostgreSQL, Redis | API, auth, node tracking, payouts, dashboards |
| Ingest Server | SRS | RTMP ingest, HLS segmentation |
| Node Client | Go | Stream relay, bandwidth reporting |
| Infrastructure | AWS CDK (TypeScript) | VPC, ECS, RDS, ElastiCache, ALB |
| CI/CD | GitHub Actions + OIDC | Auto-deploy on push to main |

### Key design decisions

- **Fiat-first economics** — rewards are in USD, not tokens. Avoids the volatility and regulatory complexity that killed competitors.
- **Contribution-weighted payouts** — you earn based on verified bytes relayed, not uptime. Gaming the system is hard when every bandwidth report is cross-checked.
- **Trust scoring** — nodes build reputation over time. Low-trust nodes get fewer viewer assignments. Fraud triggers automatic penalties.
- **Hybrid delivery** — viewers get routed to friend nodes when available, with automatic fallback to origin. No single point of failure.
- **Single binary distribution** — the Go node client is a statically-linked ~5MB binary. No runtime dependencies, no Docker required for friends.

## API overview

The coordinator exposes a REST API with JWT (RS256) authentication. Full OpenAPI docs are available at `/docs` on any running instance.

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /api/v1/auth/register-streamer` | — | Register with email/password |
| `POST /api/v1/auth/login` | — | Get JWT token |
| `POST /api/v1/auth/register` | — | Register a node with stream key |
| `POST /streams` | Streamer | Create a stream |
| `PATCH /streams/{id}/status` | Owner | Transition stream state |
| `POST /nodes/heartbeat` | Node | Report node health |
| `GET /watch/{stream_id}` | — | Viewer page (HLS.js) |
| `GET /dashboard/streamer/{id}` | — | Streamer dashboard |
| `GET /dashboard/node/{id}` | — | Node earnings dashboard |
| `GET /api/v1/economics/config` | — | Platform economics config |
| `POST /api/v1/feedback` | — | Submit feedback |

## Project structure

```
├── coordinator/          # FastAPI backend (Python)
│   ├── app/              # Application code
│   ├── alembic/          # Database migrations
│   └── tests/            # Unit + integration tests
├── node-client-go/       # Relay node binary (Go)
│   ├── cmd/              # Entry point
│   └── internal/         # Packages
├── infrastructure/       # AWS CDK stacks (TypeScript)
│   ├── lib/stacks/       # Foundation + Application stacks
│   └── test/             # CDK tests
├── tests/                # E2E integration tests
├── scripts/              # Automation and setup scripts
└── docs/                 # Documentation
```

## License

Copyright (c) 2024-2025 Ian de Villiers. All Rights Reserved.
Proprietary and Confidential Software. Unauthorized use prohibited.
