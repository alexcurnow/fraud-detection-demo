# Fraud Detection Demo Application

Real-time fraud detection system with event sourcing architecture, ML-based anomaly detection, and interactive UI.

**Built for interview demonstrations** - showcasing event sourcing, CQRS, machine learning, and full-stack development.

## Features

- 🎯 **Real-time fraud detection** with Isolation Forest ML model
- 📊 **Interactive dashboard** for testing transactions
- 🔄 **Event sourcing architecture** with complete audit trail
- 🚀 **Dockerized** for one-command deployment
- 📈 **11 engineered features** for fraud detection
- 🎨 **Modern UI** built with SvelteKit 5 + Tailwind CSS v4

## Quick Start (Docker)

```bash
# Clone the repository
git clone https://github.com/alexcurnow/fraud-detection-demo.git
cd fraud-detector

# Seed database and train ML model (one-time setup)
python3 demo_fraud_detection.py
python3 train_model.py

# Run with Docker
docker compose up -d

# Access the app
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

## Tech Stack

**Backend:**
- Python 3.12 + FastAPI (async REST API)
- scikit-learn (Isolation Forest for anomaly detection)
- NumPy (ML operations)
- SQLite (event store + read models)
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
│   └── models/                 # ML fraud detection
├── frontend/                   # SvelteKit UI
├── Dockerfile                  # Backend container
├── docker-compose.yml          # Orchestration
├── run_api.py                  # Start API server
├── train_model.py              # Train ML model
├── demo_fraud_detection.py     # Seed database
└── DOCKER.md                   # Docker guide
```

## Development Setup (Local)

### Prerequisites
- Python 3.12+
- Node.js 20+
- Docker (optional, for containerized deployment)

### Option 1: Docker (Recommended)
See Quick Start above.

### Option 2: Local Development

**1. Backend**
```bash
pip3 install -r requirements.txt
python3 demo_fraud_detection.py  # Seed database
python3 train_model.py            # Train ML model
python3 run_api.py                # Start API (port 8000)
```

**2. Frontend**
```bash
cd frontend
npm install
npm run dev                       # Start dev server (port 5173)
```

## Architecture

### Event Sourcing
- **Event Store**: Append-only log of all domain events
- **Projections**: Read models rebuilt from events
- **CQRS**: Separate write (events) and read (projections) models

### Event Types
- `AccountCreated` - New user account
- `TransactionInitiated` - Transaction started
- `TransactionCompleted` - Transaction succeeded
- `FraudFlagRaised` - ML model flagged transaction

### ML Fraud Detection

**Model**: Isolation Forest (unsupervised anomaly detection)
- **Contamination**: 5% (expected fraud rate)
- **Features**: 11 engineered features
- **Output**: Binary classification (95% fraud / 5% normal)

**Features Analyzed:**
1. Transaction amount
2. Amount deviation from user average
3. Transactions in last hour (velocity)
4. Distance from last transaction
5. Travel velocity (km/h)
6. Hour of day
7. Day of week
8. Is new merchant category
9. Is new device
10. Days since account creation
11. Total transaction count

**Flagging Reasons:**
- Unusual amount (>3x average)
- Velocity anomaly (≥3 transactions/hour)
- Geographic impossibility (>500 km/h)
- Suspicious timing (3-5 AM)
- New device
- Unusual location (>1000 km from last)

## API Endpoints

- `GET /` - Health check
- `GET /users` - List users with patterns
- `GET /users/{id}` - Get user details
- `GET /users/search?q=` - Search users (autocomplete)
- `POST /users/{id}/transactions` - Submit transaction for fraud check
- `GET /transactions/flagged` - View flagged transactions
- `GET /docs` - Interactive API documentation

## Demo Data

- **50 seeded users** with realistic transaction history
- **~1,260 transactions** across various patterns
- **~66 flagged transactions** (~5% fraud rate)
- **29 users** with fraud flags

## Use Cases

This demo showcases:
1. **Event Sourcing** - Complete audit trail of all transactions
2. **ML Integration** - Real-time fraud scoring on transaction submission
3. **Feature Engineering** - Extracting fraud indicators from raw data
4. **Interactive Demo** - Live UI for testing fraud scenarios
5. **Clean Architecture** - Separation of concerns, testable design
6. **Modern Stack** - Latest technologies (Python 3.12, Svelte 5, Tailwind v4)

## Fraud Detection Examples

**Try these in the UI:**
- **Normal**: $45 at grocery store, typical time
- **High amount**: $5000 electronics purchase → Flags "unusual_amount"
- **Velocity**: Submit 3 transactions within 1 hour → Flags "velocity_anomaly"
- **Geography**: Transaction from distant location → Flags "unusual_location" or "geographic_impossibility"
- **Timing**: 3 AM transaction → Flags "suspicious_timing"

## Docker Commands

```bash
# Start containers
docker compose up -d

# View logs
docker compose logs -f

# Stop containers
docker compose down

# See running containers
docker ps

# Rebuild after code changes
docker compose up --build
```

## Future Enhancements

- [ ] Production deployment (AWS/GCP)
- [ ] PostgreSQL instead of SQLite
- [ ] Real-time notifications for fraud
- [ ] Model retraining pipeline
- [ ] Admin dashboard
- [ ] User risk scoring

## License

MIT - Built for demonstration purposes
