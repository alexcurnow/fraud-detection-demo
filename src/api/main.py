"""
FastAPI application for interactive fraud detection demo.

Endpoints:
- GET /users - List all users with their transaction patterns
- GET /users/{user_id} - Get specific user details
- POST /users/{user_id}/transactions - Create and score a new transaction
- GET /transactions/flagged - View all flagged transactions
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    UserPattern,
    UserListResponse,
    UserResponse,
    CreateTransactionRequest,
    TransactionResponse,
    FraudAnalysis,
    FlaggedTransactionResponse,
    FlaggedTransactionsListResponse
)
from ..database import Database
from ..models import FraudDetectionModel, FraudFeatureExtractor
from ..events import (
    EventStore,
    TransactionInitiated,
    TransactionCompleted,
    FraudFlagRaised,
    EventMetadata,
    EventHandler
)
from ..projections import (
    AccountProjection,
    TransactionProjection,
    DeviceProjection,
    LocationProjection
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Fraud Detection Demo API",
    description="Interactive fraud detection system with event sourcing and ML",
    version="1.0.0"
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
ml_model: Optional[FraudDetectionModel] = None
event_handler: Optional[EventHandler] = None


@app.on_event("startup")
async def startup_event():
    """Initialize database, ML model, and event processors on startup."""
    global ml_model, event_handler

    logger.info("Starting Fraud Detection API...")

    # Initialize database
    Database.get_connection()
    logger.info("✓ Database connected")

    # Load ML model
    ml_model = FraudDetectionModel()
    try:
        ml_model.load()
        logger.info(f"✓ ML model loaded: {ml_model.model_version}")
    except FileNotFoundError:
        logger.warning("⚠ No trained model found. Please train a model first.")
        ml_model = None

    # Initialize event processors
    event_handler = EventHandler()
    event_handler.register(AccountProjection())
    event_handler.register(TransactionProjection())
    event_handler.register(DeviceProjection())
    event_handler.register(LocationProjection())
    logger.info("✓ Event processors registered")

    logger.info("🚀 Fraud Detection API ready!")


@app.get("/")
async def root():
    """API health check."""
    return {
        "status": "running",
        "service": "Fraud Detection Demo API",
        "ml_model_loaded": ml_model is not None,
        "model_version": ml_model.model_version if ml_model else None
    }


@app.get("/users/search")
async def search_users(
    q: str = Query(..., min_length=1, description="Search query (email or account ID)")
):
    """
    Search users by email or account ID for autocomplete.

    Returns matching users with basic info.
    """
    users = Database.fetch_all(
        """
        SELECT account_id, user_email
        FROM accounts
        WHERE status = 'active'
        AND (user_email LIKE ? OR account_id LIKE ?)
        ORDER BY user_email
        LIMIT 10
        """,
        (f"%{q}%", f"%{q}%")
    )

    return [
        {"account_id": u["account_id"], "email": u["user_email"]}
        for u in users
    ]


@app.get("/users", response_model=UserListResponse)
async def list_users(
    limit: int = Query(20, ge=1, le=100, description="Number of users to return")
):
    """
    List all users with their transaction patterns.

    Shows typical spending habits, locations, and fraud history.
    """
    users_data = Database.fetch_all(
        """
        SELECT
            a.account_id,
            a.user_email,
            a.total_transactions,
            a.total_volume,
            a.fraud_flags
        FROM accounts a
        WHERE a.status = 'active'
        ORDER BY a.created_at DESC
        LIMIT ?
        """,
        (limit,)
    )

    user_patterns = []
    for user in users_data:
        # Get user's typical patterns
        avg_amount = user['total_volume'] / user['total_transactions'] if user['total_transactions'] > 0 else 0

        # Get common merchants
        merchants = Database.fetch_all(
            """
            SELECT merchant_category, COUNT(*) as count
            FROM transactions
            WHERE account_id = ? AND status = 'completed'
            GROUP BY merchant_category
            ORDER BY count DESC
            LIMIT 3
            """,
            (user['account_id'],)
        )
        common_merchants = [m['merchant_category'] for m in merchants]

        # Get typical hours
        hours = Database.fetch_all(
            """
            SELECT CAST(strftime('%H', initiated_at) AS INTEGER) as hour, COUNT(*) as count
            FROM transactions
            WHERE account_id = ? AND status = 'completed'
            GROUP BY hour
            ORDER BY count DESC
            LIMIT 5
            """,
            (user['account_id'],)
        )
        typical_hours = [h['hour'] for h in hours]

        # Get home location (most common location)
        location = Database.fetch_one(
            """
            SELECT latitude, longitude, COUNT(*) as count
            FROM location_events
            WHERE account_id = ?
            GROUP BY latitude, longitude
            ORDER BY count DESC
            LIMIT 1
            """,
            (user['account_id'],)
        )
        home_location = {
            "latitude": float(location['latitude']) if location else None,
            "longitude": float(location['longitude']) if location else None
        }

        user_patterns.append(UserPattern(
            account_id=user['account_id'],
            email=user['user_email'],
            total_transactions=user['total_transactions'],
            total_volume=float(user['total_volume']),
            avg_transaction_amount=avg_amount,
            common_merchants=common_merchants,
            typical_hours=typical_hours,
            home_location=home_location,
            fraud_flags=user['fraud_flags']
        ))

    return UserListResponse(
        total=len(user_patterns),
        users=user_patterns
    )


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """
    Get detailed information about a specific user.

    Includes transaction patterns and recent transaction history.
    """
    # Get user account
    user = Database.fetch_one(
        "SELECT * FROM accounts WHERE account_id = ?",
        (user_id,)
    )

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    # Build user pattern (reuse logic from list_users)
    avg_amount = user['total_volume'] / user['total_transactions'] if user['total_transactions'] > 0 else 0

    merchants = Database.fetch_all(
        """
        SELECT merchant_category, COUNT(*) as count
        FROM transactions
        WHERE account_id = ? AND status = 'completed'
        GROUP BY merchant_category
        ORDER BY count DESC
        LIMIT 3
        """,
        (user_id,)
    )
    common_merchants = [m['merchant_category'] for m in merchants]

    hours = Database.fetch_all(
        """
        SELECT CAST(strftime('%H', initiated_at) AS INTEGER) as hour, COUNT(*) as count
        FROM transactions
        WHERE account_id = ? AND status = 'completed'
        GROUP BY hour
        ORDER BY count DESC
        LIMIT 5
        """,
        (user_id,)
    )
    typical_hours = [h['hour'] for h in hours]

    location = Database.fetch_one(
        """
        SELECT latitude, longitude
        FROM location_events
        WHERE account_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (user_id,)
    )
    home_location = {
        "latitude": float(location['latitude']) if location else None,
        "longitude": float(location['longitude']) if location else None
    }

    pattern = UserPattern(
        account_id=user['account_id'],
        email=user['user_email'],
        total_transactions=user['total_transactions'],
        total_volume=float(user['total_volume']),
        avg_transaction_amount=avg_amount,
        common_merchants=common_merchants,
        typical_hours=typical_hours,
        home_location=home_location,
        fraud_flags=user['fraud_flags']
    )

    # Get recent transactions
    recent_txns = Database.fetch_all(
        """
        SELECT transaction_id, amount, merchant_name, merchant_category,
               initiated_at, status
        FROM transactions
        WHERE account_id = ?
        ORDER BY initiated_at DESC
        LIMIT 10
        """,
        (user_id,)
    )

    recent_transactions = [
        {
            "transaction_id": t['transaction_id'],
            "amount": float(t['amount']),
            "merchant": t['merchant_name'],
            "category": t['merchant_category'],
            "timestamp": t['initiated_at'],
            "status": t['status']
        }
        for t in recent_txns
    ]

    return UserResponse(
        account_id=user['account_id'],
        email=user['user_email'],
        created_at=datetime.fromisoformat(user['created_at']),
        status=user['status'],
        patterns=pattern,
        recent_transactions=recent_transactions
    )


@app.post("/users/{user_id}/transactions", response_model=TransactionResponse)
async def create_transaction(user_id: str, transaction: CreateTransactionRequest):
    """
    Create a new transaction for a user and score it for fraud in real-time.

    The system will:
    1. Create transaction events in the event store
    2. Update read models via event processors
    3. Extract features based on user's historical patterns
    4. Run ML model to generate fraud risk score
    5. Flag if anomalous and return detailed analysis
    """
    # Verify user exists
    user = Database.fetch_one(
        "SELECT * FROM accounts WHERE account_id = ?",
        (user_id,)
    )
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    # Generate transaction ID
    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

    # Use provided timestamp or current time
    timestamp = transaction.timestamp or datetime.now(timezone.utc)

    # Create TransactionInitiated event
    txn_event = TransactionInitiated(
        aggregate_id=transaction_id,
        account_id=user_id,
        amount=transaction.amount,
        currency="USD",
        merchant_category=transaction.merchant_category,
        merchant_name=transaction.merchant_name,
        timestamp=timestamp,
        metadata=EventMetadata(
            latitude=transaction.latitude,
            longitude=transaction.longitude,
            device_id=transaction.device_id,
            ip_address=transaction.ip_address
        )
    )
    EventStore.append(txn_event)

    # Auto-complete the transaction
    txn_completed = TransactionCompleted(
        aggregate_id=transaction_id,
        account_id=user_id,
        amount=transaction.amount,
        timestamp=timestamp,
        completed_at=timestamp
    )
    EventStore.append(txn_completed)

    # Process events to update read models
    event_handler.process_new_events()

    # Score transaction with ML model
    if ml_model is None:
        raise HTTPException(
            status_code=503,
            detail="ML model not loaded. Please train a model first."
        )

    prediction = ml_model.predict(transaction_id)

    # Extract features for response
    features = FraudFeatureExtractor.extract_features(transaction_id)

    # If flagged, create FraudFlagRaised event
    if prediction['is_fraud']:
        fraud_event = FraudFlagRaised(
            aggregate_id=transaction_id,
            transaction_id=transaction_id,
            account_id=user_id,
            fraud_probability=prediction['fraud_probability'],
            flagged_reasons=prediction['flagged_reasons'],
            model_version=prediction['model_version'],
            auto_blocked=False,
            timestamp=timestamp
        )
        EventStore.append(fraud_event)
        event_handler.process_new_events()

    # Build response
    fraud_analysis = FraudAnalysis(
        risk_score=prediction['fraud_probability'],
        is_flagged=prediction['is_fraud'],
        flagged_reasons=prediction['flagged_reasons'],
        model_version=prediction['model_version'],
        features_analyzed=features if features else {}
    )

    return TransactionResponse(
        transaction_id=transaction_id,
        account_id=user_id,
        amount=transaction.amount,
        merchant_name=transaction.merchant_name,
        merchant_category=transaction.merchant_category,
        timestamp=timestamp,
        status="flagged" if prediction['is_fraud'] else "completed",
        fraud_analysis=fraud_analysis
    )


@app.get("/transactions/flagged", response_model=FlaggedTransactionsListResponse)
async def get_flagged_transactions(
    limit: int = Query(50, ge=1, le=200, description="Number of transactions to return")
):
    """
    Get all flagged (suspicious) transactions across all users.

    Useful for reviewing fraud alerts and patterns.
    """
    flagged_txns = Database.fetch_all(
        """
        SELECT
            t.transaction_id,
            t.account_id,
            a.user_email,
            t.amount,
            t.merchant_category,
            t.merchant_name,
            t.initiated_at,
            f.fraud_probability,
            f.flagged_reasons
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        LEFT JOIN fraud_scores f ON t.transaction_id = f.transaction_id
        WHERE t.status = 'flagged'
        ORDER BY t.initiated_at DESC
        LIMIT ?
        """,
        (limit,)
    )

    transactions = []
    for txn in flagged_txns:
        # Parse flagged reasons from JSON string
        import json
        reasons = json.loads(txn['flagged_reasons']) if txn['flagged_reasons'] else []

        transactions.append(FlaggedTransactionResponse(
            transaction_id=txn['transaction_id'],
            account_id=txn['account_id'],
            user_email=txn['user_email'],
            amount=float(txn['amount']),
            merchant_category=txn['merchant_category'],
            merchant_name=txn['merchant_name'],
            initiated_at=datetime.fromisoformat(txn['initiated_at']),
            risk_score=float(txn['fraud_probability']) if txn['fraud_probability'] else 0.95,
            flagged_reasons=reasons
        ))

    return FlaggedTransactionsListResponse(
        total=len(transactions),
        transactions=transactions
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
