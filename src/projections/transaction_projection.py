"""Transaction projection - builds transactions read model from events."""

import logging
from ..events.event_processor import EventProcessor
from ..events.event_models import (
    BaseEvent,
    TransactionInitiated,
    TransactionCompleted,
    TransactionFailed,
    FraudFlagRaised
)
from ..database import Database

logger = logging.getLogger(__name__)


class TransactionProjection(EventProcessor):
    """
    Builds and maintains the transactions read model.

    Processes:
    - TransactionInitiated: Creates transaction record with 'initiated' status
    - TransactionCompleted: Updates status to 'completed' and sets completed_at
    - TransactionFailed: Updates status to 'failed' and sets failed_at
    - FraudFlagRaised: Updates status to 'flagged'
    """

    def __init__(self):
        super().__init__(projection_name="TransactionProjection")

    def process_event(self, event: BaseEvent) -> None:
        """Process an event and update the transactions read model."""

        if isinstance(event, TransactionInitiated):
            self._handle_transaction_initiated(event)

        elif isinstance(event, TransactionCompleted):
            self._handle_transaction_completed(event)

        elif isinstance(event, TransactionFailed):
            self._handle_transaction_failed(event)

        elif isinstance(event, FraudFlagRaised):
            self._handle_fraud_flag_raised(event)

    def can_handle(self, event: BaseEvent) -> bool:
        """Only handle events relevant to transactions."""
        return isinstance(event, (
            TransactionInitiated,
            TransactionCompleted,
            TransactionFailed,
            FraudFlagRaised
        ))

    def _handle_transaction_initiated(self, event: TransactionInitiated) -> None:
        """Create a new transaction record."""
        Database.execute(
            """
            INSERT INTO transactions (
                transaction_id, account_id, amount, currency,
                merchant_category, merchant_name, status, initiated_at,
                latitude, longitude, device_id, ip_address
            )
            VALUES (?, ?, ?, ?, ?, ?, 'initiated', ?, ?, ?, ?, ?)
            """,
            (
                event.aggregate_id,
                event.account_id,
                event.amount,
                event.currency,
                event.merchant_category,
                event.merchant_name,
                event.timestamp.isoformat(),
                event.metadata.latitude,
                event.metadata.longitude,
                event.metadata.device_id,
                event.metadata.ip_address
            )
        )
        logger.debug(f"Transaction initiated: {event.aggregate_id} (${event.amount})")

    def _handle_transaction_completed(self, event: TransactionCompleted) -> None:
        """Update transaction status to completed."""
        Database.execute(
            """
            UPDATE transactions
            SET status = 'completed',
                completed_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE transaction_id = ?
            """,
            (event.completed_at.isoformat(), event.aggregate_id)
        )
        logger.debug(f"Transaction completed: {event.aggregate_id}")

    def _handle_transaction_failed(self, event: TransactionFailed) -> None:
        """Update transaction status to failed."""
        Database.execute(
            """
            UPDATE transactions
            SET status = 'failed',
                failed_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE transaction_id = ?
            """,
            (event.failed_at.isoformat(), event.aggregate_id)
        )
        logger.debug(f"Transaction failed: {event.aggregate_id} - {event.reason}")

    def _handle_fraud_flag_raised(self, event: FraudFlagRaised) -> None:
        """Update transaction status to flagged and save fraud score."""
        import json

        # Update transaction status
        Database.execute(
            """
            UPDATE transactions
            SET status = 'flagged',
                updated_at = CURRENT_TIMESTAMP
            WHERE transaction_id = ?
            """,
            (event.transaction_id,)
        )

        # Save fraud score details
        Database.execute(
            """
            INSERT INTO fraud_scores (
                transaction_id,
                fraud_probability,
                is_fraud,
                model_version,
                flagged_reasons,
                scored_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(transaction_id) DO UPDATE SET
                fraud_probability = excluded.fraud_probability,
                is_fraud = excluded.is_fraud,
                model_version = excluded.model_version,
                flagged_reasons = excluded.flagged_reasons,
                scored_at = excluded.scored_at
            """,
            (
                event.transaction_id,
                event.fraud_probability,
                True,
                event.model_version,
                json.dumps(event.flagged_reasons),
                event.timestamp.isoformat()
            )
        )

        logger.debug(f"Transaction flagged: {event.transaction_id}")
