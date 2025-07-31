# StreamrP2P Project Structure

## Root Directory Organization

### Core Project Files
- `README.md` - Main project overview and navigation hub
- `CURRENT_STATUS.md` - Latest progress and system status (symlinked to documentation/)
- `PROJECT_TRACKER.md` - Roadmap and priorities (symlinked to planning/)
- `LIVE_ENDPOINTS.md` - Production URLs and testing info (symlinked to documentation/)

### Configuration Files
- `pyproject.toml` - Python project configuration (Poetry)
- `requirements-test.txt` - Testing dependencies
- `.gitignore` - Git ignore patterns

## Service Directories

### `/infrastructure` - AWS CDK Infrastructure
```
infrastructure/
├── bin/infrastructure.ts          # CDK app entry point
├── lib/
│   ├── config/                    # Configuration management
│   │   ├── types.ts              # TypeScript interfaces
│   │   ├── streamr-config.ts     # Main configuration
│   │   └── deployment-context.ts # Context utilities
│   └── stacks/                   # CDK stack definitions
│       ├── foundation-stack.ts   # VPC, RDS, ElastiCache
│       └── application-stack.ts  # EC2, ALB, Security Groups
├── scripts/                      # Deployment automation
└── test/                        # CDK unit tests
```

### `/coordinator` - FastAPI Backend Service
```
coordinator/
├── app/                         # Main application code
│   ├── main.py                 # FastAPI application
│   ├── database.py             # Database connection
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   ├── payout_service.py       # Economic calculations
│   ├── stats_collector.py      # Node monitoring
│   ├── spot_check_prober.py    # Anti-fraud verification
│   ├── worker.py               # Background tasks
│   └── templates/              # HTML templates
├── docker-compose.yml          # Local development setup
├── Dockerfile                  # Container definition
└── requirements.txt            # Python dependencies
```

### `/node-client-go` - Go Binary Client
```
node-client-go/
├── cmd/streamr-node/           # Main application entry
├── internal/                   # Private packages
│   ├── coordinator/           # API client
│   ├── config/               # Configuration
│   └── logging/              # Structured logging
├── scripts/build.sh          # Cross-platform builds
├── go.mod                    # Go module definition
└── go.sum                    # Dependency lock
```

### `/node-client` - Python Client (Legacy)
```
node-client/
├── scripts/node_client.py     # P2P node implementation
├── docker-compose.yml         # Container setup
└── test_local_node.py         # Local testing
```

## Documentation Structure

### `/docs` - Organized Documentation
```
docs/
├── README.md                   # Documentation index
├── analysis/                   # Strategic analysis
│   ├── ARCHITECTURE_ANALYSIS_REPORT.md
│   ├── AWS_ARCHITECTURE_SECURITY_COST_REVIEW.md
│   ├── BREAKTHROUGH_MILESTONE_SUMMARY.md
│   └── [30+ analysis documents]
├── aws-deployment/             # AWS-specific guides
├── networking/                 # Network troubleshooting
├── onboarding/                 # Setup guides
└── testing/                    # Testing procedures
```

### `/documentation` - Current Status Files
```
documentation/
├── CURRENT_STATUS.md           # Latest progress
├── LIVE_ENDPOINTS.md           # Production URLs
├── ENDPOINT_REFERENCE.md       # Stable endpoint guide
├── DEBUGGING_NARRATIVE.md      # Troubleshooting logs
└── MIGRATION_TRACKER.md        # Database changes
```

### `/research` - Strategic Planning
```
research/
├── README.md                   # Research index
├── prfaq.md                    # Product requirements
├── analysis_of_feasibility.md # Technical feasibility
├── ai_agent_usage_guide.md    # AI consultation workflow
└── [job specs and analysis]
```

## Utility Directories

### `/scripts` - Automation Scripts
```
scripts/
├── setup-friend-node.sh       # Friend node setup (Linux/Mac)
├── setup-friend-node.ps1      # Friend node setup (Windows)
├── deploy-*.sh                # Deployment scripts
├── test-*.sh                  # Testing scripts
└── operational-*.sh           # Operations scripts
```

### `/tests` - Test Suite
```
tests/
├── conftest.py                # Pytest configuration
├── test_production_smoke.py   # Production validation
└── test_stream_lifecycle_integration.py  # E2E tests
```

### `/ingest-server` - Streaming Configuration
```
ingest-server/
├── nginx.conf                 # Nginx configuration
├── ingest_config.yaml         # Streaming config
└── start-ingest.sh           # Startup script
```

## Archive and Planning

### `/archive` - Historical Artifacts
- Development conversation logs
- Deprecated configurations
- Legacy documentation

### `/planning` - Future Roadmap
- Development plans
- User journey analysis
- Implementation strategies

### `/generated-diagrams` - Visual Assets
- Architecture diagrams
- System overview images
- Generated visualizations

## File Naming Conventions

### Documentation Files
- `UPPERCASE_WITH_UNDERSCORES.md` - Major status/reference documents
- `lowercase-with-hyphens.md` - Analysis and research documents
- `CamelCase.md` - Technical reports and summaries

### Script Files
- `kebab-case.sh` - Shell scripts
- `kebab-case.ps1` - PowerShell scripts
- `snake_case.py` - Python scripts

### Configuration Files
- `docker-compose.yml` - Docker configurations
- `package.json` - Node.js projects
- `requirements.txt` - Python dependencies
- `go.mod` - Go modules

## Navigation Patterns

### Entry Points
1. **README.md** - Start here for project overview
2. **CURRENT_STATUS.md** - Latest progress and next actions
3. **docs/README.md** - Documentation hub
4. **Service README.md** - Service-specific guides

### Cross-References
- Status files link to detailed documentation
- Service READMEs reference deployment guides
- Analysis documents cross-reference related research
- Scripts include usage examples and documentation links

### Symlinks and Aliases
- Root status files symlinked to documentation/
- Planning files accessible from root for quick access
- Live endpoints referenced from multiple locations