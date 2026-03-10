# Fraud Detection Demo Application

Real-time fraud detection system with event sourcing architecture, ML-based anomaly detection, graph-based fraud ring analysis, and LLM-powered explanations.

**Built for interview demonstrations** - showcasing event sourcing, CQRS, machine learning, graph databases, and full-stack development.

## Features

- **Real-time fraud detection** with Isolation Forest ML model
- **LLM explanations** powered by Ollama (llama3.2:1b) - natural language fraud analysis
- **Fraud ring detection** via Neo4j graph database (device sharing, money mules, merchant collusion)
- **Interactive dashboard** for testing transactions
- **Event sourcing architecture** with complete audit trail
- **Dockerized** for one-command deployment
- **Modern UI** built with SvelteKit 5 + Tailwind CSS v4

## Quick Start

The only prerequisite is [Docker](https://www.docker.com/products/docker-desktop).

```bash
git clone https://github.com/alexcurnow/fraud-detection-demo.git
cd fraud-detector
docker compose up
```

That's it. On first run, Docker will build the images and pull the `llama3.2:1b` model (~800MB) automatically. Subsequent starts are fast since the model is cached in a Docker volume.

Once everything is up:

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API + Docs | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |

Neo4j credentials: `neo4j` / `frauddetection123`

## Tech Stack

**Backend:**
- Python 3.12 + FastAPI
- scikit-learn (Isolation Forest anomaly detection)
- SQLite (event store + read models)
- Neo4j (graph database for fraud ring detection)
- Ollama + llama3.2:1b (local LLM for natural language explanations)
- Event Sourcing + CQRS architecture

**Frontend:**
- SvelteKit 5 (Svelte 5 runes)
- Tailwind CSS v4
- TypeScript

**Infrastructure:**
- Docker + Docker Compose
- Multi-stage builds for optimization

## Project Structure

```
fraud-detector/
├── src/
│   ├── api/                    # FastAPI endpoints
│   ├── events/                 # Event sourcing core
│   ├── projections/            # Read model builders
│   ├── models/                 # ML fraud detection
│   ├── graph/                  # Neo4j graph queries
│   └── llm/                    # Ollama LLM client
├── frontend/                   # SvelteKit UI
├── Dockerfile                  # Backend container
├── docker-compose.yml          # Orchestration
└── run_api.py                  # API entrypoint
```

## Architecture

### Event Sourcing
- **Event Store**: Append-only log of all domain events
- **Projections**: Read models rebuilt from events
- **CQRS**: Separate write (events) and read (projections) models

### ML Fraud Detection

**Model**: Isolation Forest (unsupervised anomaly detection)
- **Contamination**: 5% (expected fraud rate)
- **Features**: 11 engineered features

**Flagging Reasons:**
- Unusual amount (>3x average)
- Velocity anomaly (≥3 transactions/hour)
- Geographic impossibility (>500 km/h travel speed)
- Suspicious timing (3–5 AM)
- New device
- Unusual location (>1000 km from last)

### Graph Fraud Ring Detection

Neo4j powers network analysis to detect organised fraud:
- **Device sharing rings** – multiple accounts on one device
- **Money mule chains** – layered fund transfers between accounts
- **Merchant collusion** – coordinated spend at specific merchants
- **Account takeover clusters** – shared credentials across accounts

### LLM Explanations

Ollama runs `llama3.2:1b` locally (no external API calls). It generates natural language summaries of:
- Individual flagged transactions
- Detected fraud rings
- Executive fraud activity reports

## API Endpoints

- `GET /` – Health check
- `GET /users` – List users
- `POST /users/{id}/transactions` – Submit transaction for fraud scoring
- `GET /transactions/flagged` – Flagged transactions
- `GET /network/rings` – Detected fraud rings (Neo4j)
- `POST /explain/transaction` – LLM explanation for a flagged transaction
- `POST /explain/ring` – LLM explanation for a fraud ring
- `GET /docs` – Interactive API docs

## Demo Data

- **50 seeded users** with realistic transaction history
- **~1,260 transactions** across various patterns
- **~66 flagged transactions** (~5% fraud rate)

## Demo Scenarios to Try

- **Normal**: $45 at a grocery store at a typical time
- **High amount**: $5000 electronics purchase → `unusual_amount`
- **Velocity**: 3 transactions within 1 hour → `velocity_anomaly`
- **Geography**: Transaction from a distant location → `unusual_location` / `geographic_impossibility`
- **Timing**: 3 AM transaction → `suspicious_timing`

## Docker Commands

```bash
# Start (builds images on first run)
docker compose up

# Start in background
docker compose up -d

# View logs
docker compose logs -f

# View logs for a specific service
docker compose logs -f backend

# Stop
docker compose down

# Rebuild after code changes
docker compose up --build

# Full reset (deletes volumes including model cache and database)
docker compose down -v
```

## Local Development (without Docker)

**Prerequisites:** Python 3.12+, Node.js 20+, a running Neo4j instance, a running Ollama instance with `llama3.2:1b` pulled.

**Backend:**
```bash
pip install -r requirements.txt
python run_api.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## License

MIT – Built for demonstration purposes
