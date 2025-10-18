"""Account projection - builds accounts read model from events."""

import logging
from datetime import datetime
from ..events.event_processor import EventProcessor
from ..events.event_models import (
    BaseEvent,
    AccountCreated,
    TransactionCompleted,
    TransactionFailed,
    LoginAttempted,
    FraudFlagRaised
)
from ..database import Database

logger = logging.getLogger(__name__)


class AccountProjection(EventProcessor):
    """
    Builds and maintains the accounts read model.

    Processes:
    - AccountCreated: Creates account record
    - TransactionCompleted: Updates transaction counts and volume
    - FraudFlagRaised: Increments fraud flag counter
    - LoginAttempted: Updates last login timestamp
    """

    def __init__(self):
        super().__init__(projection_name="AccountProjection")

    def process_event(self, event: BaseEvent) -> None:
        """Process an event and update the accounts read model."""

        if isinstance(event, AccountCreated):
            self._handle_account_created(event)

        elif isinstance(event, TransactionCompleted):
            self._handle_transaction_completed(event)

        elif isinstance(event, FraudFlagRaised):
            self._handle_fraud_flag_raised(event)

        elif isinstance(event, LoginAttempted):
            self._handle_login_attempted(event)

    def can_handle(self, event: BaseEvent) -> bool:
        """Only handle events relevant to accounts."""
        return isinstance(event, (
            AccountCreated,
            TransactionCompleted,
            FraudFlagRaised,
            LoginAttempted
        ))

    def _handle_account_created(self, event: AccountCreated) -> None:
        """Create a new account record."""
        Database.execute(
            """
            INSERT INTO accounts (
                account_id, user_email, created_at, status,
                total_transactions, total_volume, fraud_flags
            )
            VALUES (?, ?, ?, ?, 0, 0.0, 0)
            """,
            (event.aggregate_id, event.email, event.timestamp.isoformat(), event.initial_status)
        )
        logger.debug(f"Account created: {event.aggregate_id} ({event.email})")

    def _handle_transaction_completed(self, event: TransactionCompleted) -> None:
        """Update account statistics when transaction completes."""
        Database.execute(
            """
            UPDATE accounts
            SET total_transactions = total_transactions + 1,
                total_volume = total_volume + ?,
                last_transaction = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE account_id = ?
            """,
            (event.amount, event.completed_at.isoformat(), event.account_id)
        )

    def _handle_fraud_flag_raised(self, event: FraudFlagRaised) -> None:
        """Increment fraud flag counter."""
        Database.execute(
            """
            UPDATE accounts
            SET fraud_flags = fraud_flags + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE account_id = ?
            """,
            (event.account_id,)
        )

    def _handle_login_attempted(self, event: LoginAttempted) -> None:
        """Update last login timestamp if successful."""
        if event.success:
            Database.execute(
                """
                UPDATE accounts
                SET last_login = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE account_id = ?
                """,
                (event.timestamp.isoformat(), event.account_id)
            )
