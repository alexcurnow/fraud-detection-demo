"""
Run the Fraud Detection API server.

Usage:
    python run_api.py

The API will be available at http://localhost:8000
API documentation at http://localhost:8000/docs
"""

import uvicorn
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    print("=" * 80)
    print("Starting Fraud Detection API Server")
    print("=" * 80)
    print()
    print("API will be available at:")
    print("  - API: http://localhost:8000")
    print("  - Docs: http://localhost:8000/docs")
    print("  - ReDoc: http://localhost:8000/redoc")
    print()
    print("Press CTRL+C to stop the server")
    print("=" * 80)
    print()

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
