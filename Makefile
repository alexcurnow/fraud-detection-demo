.PHONY: help dev api frontend train rescore docker-up docker-down clean

# Default Python (uses system or mise)
PYTHON := python3

help:
	@echo "Fraud Detection Demo - Available Commands:"
	@echo ""
	@echo "  make dev          - Run both API and frontend in dev mode"
	@echo "  make api          - Run backend API server"
	@echo "  make frontend     - Run frontend dev server"
	@echo "  make train        - Train ML model"
	@echo "  make rescore      - Re-score all transactions"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"
	@echo "  make clean        - Remove cache files"

# Run API server
api:
	$(PYTHON) run_api.py

# Run frontend
frontend:
	cd frontend && npm run dev

# Train ML model
train:
	$(PYTHON) train_model.py

# Re-score transactions
rescore:
	$(PYTHON) update_fraud_scores.py

# Docker commands
docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

# Development - run both (requires tmux or separate terminals)
dev:
	@echo "Run these in separate terminals:"
	@echo "  make api"
	@echo "  make frontend"

# Clean cache
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache

# Install dependencies
install:
	pip3 install -r requirements.txt
	cd frontend && npm install
