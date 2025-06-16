# StreamrP2P Coordinator Server

The central coordination service for the "restreaming as support" Proof of Concept.

## Features

- **Stream Registration**: Sponsors can register streams with token pools
- **Node Discovery**: Node operators can discover available streams
- **Heartbeat Monitoring**: Tracks active nodes and their status
- **Stats Collection**: Continuously polls node `/stats.json` endpoints
- **Spot-Check Verification**: Randomly tests nodes with real RTMP connections
- **Payout Calculation**: Calculates rewards based on uptime and fraud detection
- **Dashboard & Analytics**: Real-time monitoring and leaderboards

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start all services (coordinator, worker, database, redis)
docker-compose up -d

# View logs
docker-compose logs -f coordinator
docker-compose logs -f worker

# Stop services
docker-compose down
```

### Manual Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Database**:
   ```bash
   # Start PostgreSQL (adjust connection details in .env)
   export DATABASE_URL="postgresql://streamr:streamr@localhost:5432/streamr_poc"
   ```

3. **Run Services**:
   ```bash
   # Terminal 1: API Server
   uvicorn app.main:app --host 0.0.0.0 --port 8000

   # Terminal 2: Background Worker
   python -m app.worker
   ```

## API Endpoints

### Core Endpoints

- `POST /streams` - Register a new stream
- `GET /streams` - List active streams
- `POST /nodes/heartbeat` - Node heartbeat
- `GET /dashboard` - Dashboard data

### Analytics Endpoints

- `GET /payouts?hours_back=1` - Calculate payouts
- `GET /nodes/{node_id}/earnings` - Node earnings summary
- `GET /leaderboard` - Top performing nodes
- `GET /health` - Health check

### Example Usage

**Register a Stream**:
```bash
curl -X POST "http://localhost:8000/streams" \
  -H "Content-Type: application/json" \
  -d '{
    "stream_id": "test_stream_001",
    "sponsor_address": "0x1234...abcd",
    "token_balance": 1000.0,
    "rtmp_url": "rtmp://ingest.example.com/live/test_stream_001"
  }'
```

**Node Heartbeat**:
```bash
curl -X POST "http://localhost:8000/nodes/heartbeat" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "node_001",
    "stream_id": "test_stream_001",
    "stats_url": "http://192.168.1.100:8080/stats.json"
  }'
```

**View Dashboard**:
```bash
curl "http://localhost:8000/dashboard"
```

## Architecture

### Services

1. **FastAPI Server** (`app/main.py`): REST API endpoints
2. **Stats Collector** (`app/stats_collector.py`): Polls node stats every 60s
3. **Spot-Check Prober** (`app/spot_check_prober.py`): Random RTMP connection tests
4. **Payout Service** (`app/payout_service.py`): Reward calculations

### Database Schema

- **streams**: Stream registrations and token pools
- **nodes**: Active node operators and their status
- **probe_results**: Stats collection and spot-check results

### Verification Logic

1. **Primary Verification**: Stats Collector polls `/stats.json` endpoints
2. **Anti-Fraud**: Spot-Check Prober performs random RTMP connection tests
3. **Fraud Detection**: Nodes that report healthy but fail spot-checks are flagged
4. **Rewards**: Based on uptime percentage, with zero payout for flagged nodes

## Environment Variables

```bash
DATABASE_URL=postgresql://streamr:streamr@localhost:5432/streamr_poc
```

## Development

### Running Tests

```bash
# TODO: Add test suite
pytest
```

### Database Migrations

```bash
# TODO: Add Alembic migrations
alembic upgrade head
```

## Next Steps

This coordinator implements **Issues #1-5** from the PoC task breakdown. Next steps:

1. Build the Node Client (Epic 2)
2. Deploy infrastructure (Epic 3)
3. Conduct alpha testing with 5-10 community members 