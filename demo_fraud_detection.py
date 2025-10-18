"""
Demo: Using the fraud detection model to score transactions.

This shows how to:
1. Load a trained model
2. Score transactions for fraud
3. See which features triggered the fraud flag
"""

import logging
from src.models import FraudDetectionModel
from src.database import Database

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    print("=" * 80)
    print("FRAUD DETECTION DEMO")
    print("=" * 80)

    # Load the trained model
    print("\n1. Loading trained model...")
    model = FraudDetectionModel()
    model.load()  # Loads latest model
    print(f"   ✓ Loaded model: {model.model_version}")
    print(f"   ✓ Features used: {', '.join(model.feature_names)}")

    # Get some transactions to score
    print("\n2. Fetching transactions to score...")
    transactions = Database.fetch_all(
        """
        SELECT transaction_id, amount, merchant_category, status
        FROM transactions
        WHERE status = 'completed'
        ORDER BY initiated_at DESC
        LIMIT 20
        """
    )
    print(f"   ✓ Found {len(transactions)} transactions")

    # Score each transaction
    print("\n3. Scoring transactions for fraud...")
    print("\n" + "-" * 80)

    fraud_count = 0
    for txn in transactions:
        result = model.predict(txn['transaction_id'])

        # Only show interesting ones (high fraud probability)
        if result['fraud_probability'] > 0.3:
            fraud_count += 1
            print(f"\n🚨 SUSPICIOUS TRANSACTION DETECTED!")
            print(f"   Transaction ID: {txn['transaction_id']}")
            print(f"   Amount: ${txn['amount']:.2f}")
            print(f"   Category: {txn['merchant_category']}")
            print(f"   Fraud Probability: {result['fraud_probability']:.1%}")
            print(f"   Flagged for: {', '.join(result['flagged_reasons'])}")

    print("\n" + "-" * 80)
    print(f"\nSummary: Found {fraud_count} suspicious transactions out of {len(transactions)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
