"""Test script to verify event store functionality."""

import logging
from datetime import datetime
from src.init_system import initialize_system
from src.events import (
    EventStore,
    AccountCreated,
    TransactionInitiated,
    TransactionCompleted,
    LoginAttempted,
    DeviceChanged,
    FraudFlagRaised,
    EventMetadata
)
from src.database import Database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_event_store():
    """Test the event store with sample events."""

    # Initialize system (fresh start)
    logger.info("=" * 80)
    logger.info("TESTING EVENT STORE")
    logger.info("=" * 80)

    event_handler = initialize_system(force_rebuild=True)

    # Create sample account
    account_id = "acc_test_001"
    account_event = AccountCreated(
        aggregate_id=account_id,
        email="john.doe@example.com",
        metadata=EventMetadata(
            ip_address="192.168.1.1",
            device_id="device_001"
        )
    )

    EventStore.append(account_event)
    logger.info(f"Created account: {account_id}")

    # Process events to update read models
    event_handler.process_new_events()

    # Verify account was created
    account = Database.fetch_one("SELECT * FROM accounts WHERE account_id = ?", (account_id,))
    assert account is not None, "Account not found in read model"
    assert account['user_email'] == "john.doe@example.com"
    logger.info(f"✓ Account read model updated: {dict(account)}")

    # Create sample transaction
    transaction_id = "txn_test_001"
    txn_initiated = TransactionInitiated(
        aggregate_id=transaction_id,
        account_id=account_id,
        amount=99.99,
        currency="USD",
        merchant_category="electronics",
        merchant_name="TechStore",
        metadata=EventMetadata(
            latitude=40.7128,
            longitude=-74.0060,
            device_id="device_001",
            ip_address="192.168.1.1"
        )
    )

    EventStore.append(txn_initiated)
    logger.info(f"Initiated transaction: {transaction_id}")

    # Complete the transaction
    txn_completed = TransactionCompleted(
        aggregate_id=transaction_id,
        account_id=account_id,
        amount=99.99
    )

    EventStore.append(txn_completed)
    logger.info(f"Completed transaction: {transaction_id}")

    # Process events
    event_handler.process_new_events()

    # Verify transaction in read model
    transaction = Database.fetch_one("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
    assert transaction is not None, "Transaction not found in read model"
    assert transaction['status'] == "completed"
    assert transaction['amount'] == 99.99
    logger.info(f"✓ Transaction read model updated: status={transaction['status']}, amount=${transaction['amount']}")

    # Verify account statistics updated
    account = Database.fetch_one("SELECT * FROM accounts WHERE account_id = ?", (account_id,))
    assert account['total_transactions'] == 1
    assert account['total_volume'] == 99.99
    logger.info(f"✓ Account stats updated: {account['total_transactions']} transactions, ${account['total_volume']} total")

    # Test device tracking
    device_event = DeviceChanged(
        aggregate_id=account_id,
        account_id=account_id,
        new_device_id="device_002",
        device_type="mobile",
        browser="Chrome",
        os="iOS",
        metadata=EventMetadata(device_id="device_002")
    )

    EventStore.append(device_event)
    event_handler.process_new_events()

    devices = Database.fetch_all("SELECT * FROM devices WHERE account_id = ?", (account_id,))
    logger.info(f"✓ Device tracking: {len(devices)} devices registered")

    # Test fraud flag
    fraud_event = FraudFlagRaised(
        aggregate_id=transaction_id,
        transaction_id=transaction_id,
        account_id=account_id,
        fraud_probability=0.85,
        flagged_reasons=["unusual_amount", "velocity_anomaly"],
        model_version="v1.0"
    )

    EventStore.append(fraud_event)
    event_handler.process_new_events()

    transaction = Database.fetch_one("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
    assert transaction['status'] == "flagged"
    logger.info(f"✓ Fraud flag raised: status={transaction['status']}")

    account = Database.fetch_one("SELECT * FROM accounts WHERE account_id = ?", (account_id,))
    assert account['fraud_flags'] == 1
    logger.info(f"✓ Account fraud flags: {account['fraud_flags']}")

    # Test event retrieval
    logger.info("\n" + "=" * 80)
    logger.info("TESTING EVENT RETRIEVAL")
    logger.info("=" * 80)

    # Get all events for the transaction
    transaction_events = EventStore.get_events_by_aggregate("Transaction", transaction_id)
    logger.info(f"Transaction {transaction_id} has {len(transaction_events)} events:")
    for event in transaction_events:
        logger.info(f"  - {event.event_type} at {event.timestamp}")

    # Get all events by type
    account_created_events = EventStore.get_events_by_type("AccountCreated")
    logger.info(f"\nTotal AccountCreated events: {len(account_created_events)}")

    # Get event count
    total_events = EventStore.get_event_count()
    logger.info(f"Total events in store: {total_events}")

    logger.info("\n" + "=" * 80)
    logger.info("ALL TESTS PASSED!")
    logger.info("=" * 80)


if __name__ == "__main__":
    test_event_store()
