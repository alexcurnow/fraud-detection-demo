"""
Re-score all existing transactions with the ML fraud detection model.

This script:
1. Loads all completed transactions
2. Runs them through the ML model
3. Creates FraudFlagRaised events for fraudulent transactions
4. Updates the read models
"""

import logging
from src.database import Database
from src.models import FraudDetectionModel
from src.events import EventStore, FraudFlagRaised, EventHandler
from src.projections import (
    AccountProjection,
    TransactionProjection,
    DeviceProjection,
    LocationProjection
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def rescore_all_transactions():
    """Re-score all completed transactions with the ML model."""

    # Initialize database and model
    Database.get_connection()
    logger.info("Database connected")

    # Load ML model
    model = FraudDetectionModel()
    try:
        model.load()
        logger.info(f"ML model loaded: {model.model_version}")
    except FileNotFoundError:
        logger.error("No trained model found. Please train a model first.")
        return

    # Initialize event handler
    event_handler = EventHandler()
    event_handler.register(AccountProjection())
    event_handler.register(TransactionProjection())
    event_handler.register(DeviceProjection())
    event_handler.register(LocationProjection())
    logger.info("Event processors registered")

    # Get all completed transactions that haven't been scored
    transactions = Database.fetch_all(
        """
        SELECT t.transaction_id, t.account_id, t.initiated_at
        FROM transactions t
        LEFT JOIN fraud_scores fs ON t.transaction_id = fs.transaction_id
        WHERE t.status = 'completed'
        AND fs.transaction_id IS NULL
        ORDER BY t.initiated_at
        """
    )

    logger.info(f"Found {len(transactions)} transactions to score")

    flagged_count = 0
    safe_count = 0

    for txn in transactions:
        transaction_id = txn['transaction_id']
        account_id = txn['account_id']

        # Score the transaction
        prediction = model.predict(transaction_id)

        if prediction['is_fraud']:
            # Create FraudFlagRaised event
            fraud_event = FraudFlagRaised(
                aggregate_id=transaction_id,
                transaction_id=transaction_id,
                account_id=account_id,
                fraud_probability=prediction['fraud_probability'],
                flagged_reasons=prediction['flagged_reasons'],
                model_version=prediction['model_version'],
                auto_blocked=False,
                timestamp=txn['initiated_at']
            )
            EventStore.append(fraud_event)
            flagged_count += 1

            logger.info(
                f"FRAUD: {transaction_id} - {prediction['fraud_probability']:.1%} - "
                f"{', '.join(prediction['flagged_reasons'])}"
            )
        else:
            safe_count += 1

    # Process all the fraud events to update read models
    if flagged_count > 0:
        logger.info("Processing fraud events to update read models...")
        event_handler.process_new_events()

    # Print summary
    logger.info("=" * 80)
    logger.info("RESCORING COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total transactions scored: {len(transactions)}")
    logger.info(f"Flagged as fraud: {flagged_count} ({flagged_count/len(transactions)*100:.1f}%)")
    logger.info(f"Marked as safe: {safe_count} ({safe_count/len(transactions)*100:.1f}%)")
    logger.info("=" * 80)


if __name__ == "__main__":
    rescore_all_transactions()
