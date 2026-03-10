#!/usr/bin/env python3
"""
Phase 2 Status Check Script.

Verifies that all Phase 2 services are running:
- Neo4j graph database
- Ollama LLM service
- FastAPI backend
- Frontend (optional)
"""

import sys
import httpx
from neo4j import GraphDatabase
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class Phase2StatusChecker:
    """Checks status of all Phase 2 services."""

    def __init__(self):
        self.all_ok = True

    def check_neo4j(self) -> bool:
        """Check Neo4j connection."""
        logger.info("\n[1/4] Checking Neo4j Graph Database...")

        try:
            driver = GraphDatabase.driver(
                "bolt://localhost:7687",
                auth=("neo4j", "frauddetection123")
            )
            driver.verify_connectivity()
            driver.close()

            logger.info("  ✓ Neo4j is RUNNING on bolt://localhost:7687")
            logger.info("  ✓ Neo4j Browser: http://localhost:7474")
            return True

        except Exception as e:
            logger.error(f"  ✗ Neo4j is NOT running: {e}")
            logger.info("  → Start with: docker compose up -d neo4j")
            return False

    def check_ollama(self) -> bool:
        """Check Ollama LLM service."""
        logger.info("\n[2/4] Checking Ollama LLM Service...")

        try:
            response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)

            if response.status_code == 200:
                models = response.json().get("models", [])
                logger.info("  ✓ Ollama is RUNNING on http://localhost:11434")

                if models:
                    logger.info(f"  ✓ Available models: {[m['name'] for m in models]}")
                else:
                    logger.warning("  ⚠ No models installed yet")
                    logger.info("  → Pull model with: docker exec fraud-detection-ollama ollama pull llama3.2")

                return True
            else:
                logger.error(f"  ✗ Ollama returned status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"  ✗ Ollama is NOT running: {e}")
            logger.info("  → Start with: docker compose up -d ollama")
            return False

    def check_api(self) -> bool:
        """Check FastAPI backend."""
        logger.info("\n[3/4] Checking FastAPI Backend...")

        try:
            response = httpx.get("http://localhost:8000/", timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                logger.info("  ✓ FastAPI is RUNNING on http://localhost:8000")
                logger.info(f"  ✓ API Status: {data.get('status')}")
                logger.info(f"  ✓ ML Model: {data.get('model_version', 'Not loaded')}")
                logger.info("  ✓ API Docs: http://localhost:8000/docs")

                # Check Phase 2 endpoints
                try:
                    health_resp = httpx.get("http://localhost:8000/explain/health", timeout=5.0)
                    if health_resp.status_code == 200:
                        health_data = health_resp.json()
                        logger.info(f"  ✓ LLM Integration: {health_data.get('llm_service')}")
                except Exception:
                    logger.warning("  ⚠ Phase 2 endpoints not available yet")

                return True
            else:
                logger.error(f"  ✗ API returned status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"  ✗ FastAPI is NOT running: {e}")
            logger.info("  → Start with: python run_api.py")
            return False

    def check_frontend(self) -> bool:
        """Check SvelteKit frontend (optional)."""
        logger.info("\n[4/4] Checking SvelteKit Frontend...")

        try:
            response = httpx.get("http://localhost:3000/", timeout=5.0)

            if response.status_code == 200:
                logger.info("  ✓ Frontend is RUNNING on http://localhost:3000")
                return True
            else:
                logger.warning(f"  ⚠ Frontend returned status {response.status_code}")
                return True  # Non-critical

        except Exception:
            logger.warning("  ⚠ Frontend is not running (optional)")
            logger.info("  → Start with: cd frontend && npm run dev")
            return True  # Non-critical

    def check_docker_containers(self):
        """Show Docker container status."""
        import subprocess

        logger.info("\nDocker Containers:")
        logger.info("-" * 60)

        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=fraud-detection", "--format", "table {{.Names}}\t{{.Status}}"],
                capture_output=True,
                text=True
            )
            print(result.stdout)
        except Exception as e:
            logger.warning(f"Could not check Docker containers: {e}")

    def run_all_checks(self):
        """Run all status checks."""
        logger.info("=" * 60)
        logger.info("FRAUD DETECTION PHASE 2 - STATUS CHECK")
        logger.info("=" * 60)

        neo4j_ok = self.check_neo4j()
        ollama_ok = self.check_ollama()
        api_ok = self.check_api()
        frontend_ok = self.check_frontend()

        self.check_docker_containers()

        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)

        status = {
            "Neo4j": neo4j_ok,
            "Ollama": ollama_ok,
            "FastAPI": api_ok,
            "Frontend": frontend_ok
        }

        for service, ok in status.items():
            status_icon = "✓" if ok else "✗"
            logger.info(f"  {status_icon} {service}")

        critical_ok = neo4j_ok and ollama_ok and api_ok

        if critical_ok:
            logger.info("\n✓ All critical services are READY!")
            logger.info("\nNext steps:")
            logger.info("  1. Seed fraud rings: python seed_fraud_rings.py")
            logger.info("  2. Test network analysis: GET http://localhost:8000/network/rings")
            logger.info("  3. Test LLM explanations: POST http://localhost:8000/explain/summary")
            return True
        else:
            logger.error("\n✗ Some critical services are NOT running")
            logger.info("\nTo start all services:")
            logger.info("  docker compose up -d")
            return False


def main():
    checker = Phase2StatusChecker()
    all_ok = checker.run_all_checks()

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
