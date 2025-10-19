# Docker Deployment Guide

This guide explains how to run the Fraud Detection demo using Docker containers.

## What is Docker?

Docker packages your application and all its dependencies into **containers** - isolated, lightweight environments that run consistently anywhere. Think of it like shipping containers: your app runs the same way on your laptop, a server, or the cloud.

### Key Concepts

- **Image**: A template for your application (like a snapshot)
- **Container**: A running instance of an image (like a running program)
- **Dockerfile**: Instructions to build an image
- **docker compose**: Tool to run multiple containers together

## Prerequisites

Install Docker Desktop:
- **Mac/Windows**: Download from https://www.docker.com/products/docker-desktop
- **Linux**:
  ```bash
  curl -fsSL https://get.docker.com -o get-docker.sh
  sudo sh get-docker.sh
  ```

Verify installation:
```bash
docker --version
docker compose version
```

**Note**: Modern Docker uses `docker compose` (with a space), not the older `docker compose` (with hyphen).

## Quick Start

### 1. Build and run with one command:

```bash
docker compose up --build
```

This will:
- Build the backend (Python/FastAPI) image
- Build the frontend (SvelteKit) image
- Start both containers
- Set up networking between them

### 2. Access the application:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 3. Stop the containers:

Press `Ctrl+C` in the terminal, or run:
```bash
docker compose down
```

## Detailed Commands

### Build images (without starting):
```bash
docker compose build
```

### Start in detached mode (background):
```bash
docker compose up -d
```

### View logs:
```bash
docker compose logs -f
# Or for specific service:
docker compose logs -f backend
docker compose logs -f frontend
```

### Stop and remove containers:
```bash
docker compose down
```

### Rebuild from scratch (clears cache):
```bash
docker compose build --no-cache
docker compose up
```

## Architecture

### Backend Container
- **Image**: Python 3.12 slim
- **Port**: 8000
- **Volumes**:
  - `fraud_detection.db` - SQLite database (persisted)
  - `models/` - ML model files (persisted)

### Frontend Container
- **Image**: Node 20 Alpine (multi-stage build)
- **Port**: 3000
- **Build**: Compiles SvelteKit to production build

### Networking
- Both containers are on the same Docker network
- Frontend calls backend via `http://localhost:8000`

## Data Persistence

The database and ML models are mounted as **volumes**, meaning:
- Data persists even when containers stop
- Changes are reflected immediately
- Located in your project directory

## Troubleshooting

### Port already in use:
```bash
# Kill process on port 8000:
lsof -ti:8000 | xargs kill -9

# Or change port in docker compose.yml:
ports:
  - "8001:8000"  # host:container
```

### Rebuild after code changes:
```bash
docker compose up --build
```

### View running containers:
```bash
docker ps
```

### Execute command in container:
```bash
docker compose exec backend python seed_database.py
docker compose exec backend python train_model.py
```

### Fresh start (removes all data):
```bash
docker compose down -v  # WARNING: Deletes volumes!
docker compose up --build
```

## Production Deployment

For production hosting (AWS, Google Cloud, DigitalOcean, etc.):

1. **Push to Docker Hub**:
   ```bash
   docker tag fraud-detector-backend yourusername/fraud-detector-backend
   docker push yourusername/fraud-detector-backend
   ```

2. **Environment Variables**:
   - Create `.env` file for secrets
   - Update `VITE_API_URL` to point to your domain
   - Set `ENVIRONMENT=production`

3. **Use a process manager** like Docker Swarm or Kubernetes

4. **Add HTTPS** with a reverse proxy (nginx, Traefik, Caddy)

5. **Database**: Consider PostgreSQL instead of SQLite for production

## File Structure

```
fraud-detector/
├── Dockerfile              # Backend image
├── docker compose.yml      # Orchestration config
├── .dockerignore          # Excludes from backend image
├── frontend/
│   ├── Dockerfile         # Frontend image (multi-stage)
│   └── .dockerignore      # Excludes from frontend image
└── DOCKER.md              # This file
```

## Next Steps

- Deploy to a cloud platform (Fly.io, Railway, Render, etc.)
- Set up CI/CD with GitHub Actions
- Add monitoring with Docker stats or Prometheus
- Configure automatic backups of `fraud_detection.db`
