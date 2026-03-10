"""LLM explanation API endpoints - Phase 2."""

import logging
from fastapi import APIRouter, HTTPException
from typing import List

from .models import ExplanationResponse, ExecutiveSummaryResponse
from ..llm import OllamaClient
from ..database import Database
from ..graph import FraudRingDetector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/explain", tags=["explanations"])

# Global LLM client
llm_client = OllamaClient()


@router.post("/transaction/{transaction_id}", response_model=ExplanationResponse)
async def explain_transaction_fraud(transaction_id: str):
    """
    Generate natural language explanation for a flagged transaction.

    Takes a transaction ID and returns an LLM-generated explanation of:
    - Why it was flagged
    - Key suspicious indicators
    - Recommended action
    """
    try:
        # Get transaction data
        transaction = Database.fetch_one(
            """
            SELECT t.*, a.user_email, a.total_transactions, a.total_volume
            FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
            WHERE t.transaction_id = ?
            """,
            (transaction_id,)
        )

        if not transaction:
            raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")

        # Get fraud analysis
        fraud_score = Database.fetch_one(
            "SELECT * FROM fraud_scores WHERE transaction_id = ?",
            (transaction_id,)
        )

        if not fraud_score:
            raise HTTPException(
                status_code=400,
                detail=f"Transaction {transaction_id} has not been scored for fraud"
            )

        # Get user patterns
        user_patterns = Database.fetch_all(
            """
            SELECT merchant_category, COUNT(*) as count
            FROM transactions
            WHERE account_id = ? AND status = 'completed'
            GROUP BY merchant_category
            ORDER BY count DESC
            LIMIT 3
            """,
            (transaction["account_id"],)
        )

        typical_hours = Database.fetch_all(
            """
            SELECT CAST(strftime('%H', initiated_at) AS INTEGER) as hour, COUNT(*) as count
            FROM transactions
            WHERE account_id = ? AND status = 'completed'
            GROUP BY hour
            ORDER BY count DESC
            LIMIT 5
            """,
            (transaction["account_id"],)
        )

        # Prepare context
        transaction_data = {
            "amount": float(transaction["amount"]),
            "merchant_name": transaction["merchant_name"],
            "merchant_category": transaction["merchant_category"],
            "latitude": transaction.get("latitude"),
            "longitude": transaction.get("longitude"),
            "timestamp": transaction["initiated_at"]
        }

        user_context = {
            "avg_transaction_amount": float(transaction["total_volume"]) / transaction["total_transactions"]
            if transaction["total_transactions"] > 0 else 0,
            "total_transactions": transaction["total_transactions"],
            "common_merchants": [p["merchant_category"] for p in user_patterns],
            "typical_hours": [h["hour"] for h in typical_hours],
            "fraud_flags": 1  # This transaction is flagged
        }

        import json
        fraud_analysis = {
            "risk_score": float(fraud_score["fraud_probability"]),
            "flagged_reasons": json.loads(fraud_score["flagged_reasons"]) if fraud_score["flagged_reasons"] else []
        }

        # Generate explanation
        explanation = llm_client.explain_transaction_fraud(
            transaction_data,
            user_context,
            fraud_analysis
        )

        return ExplanationResponse(explanation=explanation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error explaining transaction {transaction_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/network/{ring_type}", response_model=ExplanationResponse)
async def explain_fraud_ring(ring_type: str):
    """
    Generate natural language explanation for detected fraud rings.

    Explains specific fraud ring patterns (device_sharing, money_mule, etc.)
    """
    try:
        # Get specific ring type detection
        if ring_type == "device_sharing":
            rings = FraudRingDetector.detect_device_sharing_rings()
        elif ring_type == "money_mule":
            rings = FraudRingDetector.detect_money_mule_chains()
        elif ring_type == "merchant_collusion":
            rings = FraudRingDetector.detect_merchant_collusion()
        elif ring_type == "account_takeover":
            rings = FraudRingDetector.detect_account_takeover_rings()
        elif ring_type == "synthetic_identity":
            rings = FraudRingDetector.detect_synthetic_identity_rings()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown ring type: {ring_type}")

        if not rings:
            return ExplanationResponse(
                explanation=f"No {ring_type} fraud rings detected in the current data."
            )

        # Explain the first (most prominent) ring
        ring_data = rings[0]
        explanation = llm_client.explain_fraud_ring(ring_type, ring_data)

        return ExplanationResponse(explanation=explanation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error explaining {ring_type} fraud ring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summary", response_model=ExecutiveSummaryResponse)
async def generate_executive_summary():
    """
    Generate executive summary of all fraud activity.

    Provides high-level overview for management including:
    - Overall fraud landscape
    - Key patterns and trends
    - Priority actions
    """
    try:
        # Get flagged transactions
        flagged_transactions = Database.fetch_all(
            """
            SELECT transaction_id, amount, merchant_category, merchant_name, initiated_at
            FROM transactions
            WHERE status = 'flagged'
            ORDER BY initiated_at DESC
            LIMIT 100
            """,
        )

        # Get detected rings
        detected_rings = FraudRingDetector.detect_all_rings()

        total_risk = sum(float(t["amount"]) for t in flagged_transactions)
        total_rings = sum(len(rings) for rings in detected_rings.values())

        # Generate summary
        summary_text = llm_client.generate_executive_summary(
            flagged_transactions,
            detected_rings
        )

        # Extract priority actions (simple heuristic)
        priority_actions = []
        if len(flagged_transactions) > 50:
            priority_actions.append("Review high volume of flagged transactions")
        if detected_rings.get("money_mule", []):
            priority_actions.append("Investigate money mule chains immediately")
        if detected_rings.get("device_sharing", []):
            priority_actions.append("Lock accounts in device sharing rings")
        if total_risk > 100000:
            priority_actions.append(f"High risk exposure: ${total_risk:,.2f}")

        return ExecutiveSummaryResponse(
            summary=summary_text,
            total_flagged_transactions=len(flagged_transactions),
            total_fraud_rings=total_rings,
            total_risk_exposure=total_risk,
            priority_actions=priority_actions
        )

    except Exception as e:
        logger.error(f"Error generating executive summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def check_llm_health():
    """Check if LLM service is available."""
    try:
        available = llm_client._is_available()
        return {
            "llm_service": "available" if available else "unavailable",
            "model": llm_client.model,
            "base_url": llm_client.base_url
        }
    except Exception as e:
        return {
            "llm_service": "error",
            "error": str(e)
        }
