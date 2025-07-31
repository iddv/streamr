# StreamrP2P Technical Stack

## Build System & Package Management

### Infrastructure (AWS CDK)
- **Language**: TypeScript
- **Framework**: AWS CDK v2.200.1+
- **Package Manager**: npm
- **Build**: `npm run build` (TypeScript compilation)
- **Test**: `npm test` (Jest)

### Backend Services (Python)
- **Language**: Python 3.8+
- **Framework**: FastAPI 0.104.1
- **Package Manager**: pip/Poetry
- **Dependencies**: `requirements.txt` or `pyproject.toml`
- **ASGI Server**: Uvicorn with standard extras

### Node Client (Go)
- **Language**: Go 1.23.4+
- **Build System**: Go modules
- **Cross-compilation**: Automated via `scripts/build.sh`
- **Binary Size**: ~5MB statically linked

## Technical Decision Framework
For major technical architecture decisions, consult our **Infrastructure Visionary** ZEN advisor (see `.kiro/steering/zen-advisors.md`). Key principles:
- Hybrid approaches over pure solutions (CDN + P2P)
- Real-time systems over polling (WebSockets, SSE)
- One-click experiences over complex setups
- Feature flags for safe deployment

## Core Technology Stack

### Infrastructure & Deployment
- **Cloud Provider**: AWS (primary region: eu-west-1)
- **Infrastructure as Code**: AWS CDK (TypeScript)
- **Compute**: EC2 instances (t3.micro/small/medium based on stage)
- **Load Balancing**: Application Load Balancer (ALB)
- **Networking**: VPC with public/private subnets
- **DNS**: Elastic IP for RTMP, ALB DNS for HTTP

### Backend Services
- **API Framework**: FastAPI (Python)
- **Database**: PostgreSQL 15.4 (AWS RDS)
- **Cache**: Redis (AWS ElastiCache)
- **Background Tasks**: Celery with Redis broker
- **Authentication**: JWT tokens (planned)
- **Monitoring**: CloudWatch integration

### Streaming Infrastructure
- **Streaming Server**: SRS (Simple Realtime Server)
- **Protocols**: RTMP (ingest), HLS/HTTP-FLV (output)
- **Container**: Docker with docker-compose orchestration
- **Ports**: 1935 (RTMP), 8080 (HTTP/HLS), 8000 (API)

### Client Applications
- **Node Client**: Go binary (cross-platform)
- **Web Dashboard**: HTML/JavaScript (served by FastAPI)
- **Streaming Software**: OBS Studio integration

## Common Commands

### Infrastructure Deployment
```bash
# Deploy to beta environment
cd infrastructure && ./scripts/deploy-beta.sh

# Deploy specific stack
npx cdk deploy streamr-p2p-beta-ireland-foundation --context stage=beta

# Destroy infrastructure (careful!)
npx cdk destroy --all --context stage=beta

# Check deployment status
./scripts/monitor-deployment.sh
```

### Backend Development
```bash
# Start all services locally
cd coordinator && docker-compose up -d

# Run API server only
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run background worker
python -m app.worker

# Database migration
alembic upgrade head

# Run tests
python -m pytest tests/
```

### Node Client Development
```bash
# Build for current platform
cd node-client-go && go build -o streamr-node ./cmd/streamr-node

# Build for all platforms
./scripts/build.sh

# Run with debug logging
./streamr-node -debug

# Test coordinator connection
./streamr-node -coordinator http://localhost:8000
```

### Testing & Validation
```bash
# Integration tests
python -m pytest tests/test_stream_lifecycle_integration.py

# Production smoke tests
python -m pytest tests/test_production_smoke.py

# Stream testing
./scripts/test_streaming.sh

# Friend node setup
./scripts/setup-friend-node.sh STREAM_KEY
```

## Architecture Patterns

### Multi-Stage Deployment
- **Beta**: Experimental changes (t3.micro, no protection)
- **Gamma**: Pre-production testing (t3.small, deletion protection)
- **Prod**: Live operations (t3.medium, full protection)

### Service Architecture
- **Coordinator**: Central API and coordination service
- **Stats Collector**: Background service polling node health
- **Spot-Check Prober**: Anti-fraud verification system
- **Payout Service**: Economic reward calculations

### Database Design
- **Performance Optimized**: Single aggregated queries using PostgreSQL window functions
- **Economic Model**: Contribution-weighted payouts with fraud detection
- **Scaling Strategy**: PostgreSQL → TimescaleDB for time-series data

### Security Patterns
- **Network Isolation**: VPC with private subnets for database/cache
- **Secrets Management**: AWS Secrets Manager integration
- **Least Privilege**: IAM roles with minimal permissions
- **Encryption**: RDS and EBS encryption enabled

## Development Conventions

### Code Style
- **Python**: Black formatter, isort imports, ruff linting
- **TypeScript**: Standard CDK conventions
- **Go**: Standard Go formatting (`go fmt`)

### Testing Strategy
- **Unit Tests**: pytest for Python, Jest for TypeScript, Go testing for Go
- **Integration Tests**: End-to-end stream lifecycle testing
- **Smoke Tests**: Production endpoint validation

### Documentation Standards
- **API Documentation**: FastAPI auto-generated OpenAPI
- **Infrastructure**: CDK construct documentation
- **User Guides**: Markdown in `docs/` directory

### Deployment Strategy
- **Infrastructure First**: CDK stacks before application deployment
- **Health Checks**: Comprehensive endpoint monitoring
- **Rollback Capability**: Infrastructure and application versioning
- **Cost Control**: Pause/resume capabilities for development stages