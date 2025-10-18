# Fraud Detection Demo Application

Event-sourced fraud detection system for demonstration purposes.

## Project Structure

```
fraud-detector/
├── schema.sql                  # Database schema (event store + read models)
├── requirements.txt            # Python dependencies
├── ARCHITECTURE.md            # Architecture documentation
├── test_event_store.py        # Test script for event store
├── src/
│   ├── database.py            # Database connection manager
│   ├── init_system.py         # System initialization
│   ├── events/
│   │   ├── event_models.py    # Event definitions (Pydantic models)
│   │   ├── event_store.py     # Event store implementation
│   │   └── event_processor.py # Event processor base class
│   ├── projections/
│   │   ├── account_projection.py      # Accounts read model
│   │   ├── transaction_projection.py  # Transactions read model
│   │   ├── device_projection.py       # Devices read model
│   │   └── location_projection.py     # Location tracking read model
│   └── models/                # (Future: ML models)
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python -m src.init_system --force
```

This will:
- Create the SQLite database (`fraud_detection.db`)
- Initialize all tables from `schema.sql`
- Register event processors

### 3. Test Event Store

```bash
python test_event_store.py
```

This will create sample events and verify the event sourcing system works correctly.

## Event Sourcing Architecture

### Core Components

1. **Event Store** (`events` table)
   - Append-only log of all domain events
   - Single source of truth
   - Supports event replay and temporal queries

2. **Event Types**
   - `AccountCreated` - New account registration
   - `TransactionInitiated` - Transaction started
   - `TransactionCompleted` - Transaction finished successfully
   - `TransactionFailed` - Transaction failed
   - `LoginAttempted` - Login attempt (success or failure)
   - `DeviceChanged` - User switched devices
   - `LocationChanged` - User location changed
   - `FraudFlagRaised` - Fraud detected by ML model

3. **Read Models** (Projections)
   - Built by processing events
   - Optimized for queries
   - Can be rebuilt from events at any time

   **Tables:**
   - `accounts` - Current account state
   - `transactions` - Transaction records
   - `devices` - Device fingerprints
   - `location_events` - Geographic tracking
   - `login_attempts` - Authentication history

4. **Event Processors**
   - Process events asynchronously
   - Update read models
   - Maintain checkpoints for idempotency

### Usage Example

```python
from src.events import EventStore, AccountCreated, TransactionInitiated, EventMetadata
from src.init_system import initialize_system

# Initialize system
event_handler = initialize_system()

# Create an account
account_event = AccountCreated(
    aggregate_id="acc_001",
    email="user@example.com",
    metadata=EventMetadata(
        ip_address="192.168.1.1",
        device_id="device_001"
    )
)
EventStore.append(account_event)

# Create a transaction
txn_event = TransactionInitiated(
    aggregate_id="txn_001",
    account_id="acc_001",
    amount=100.00,
    merchant_name="Coffee Shop",
    metadata=EventMetadata(
        latitude=40.7128,
        longitude=-74.0060,
        device_id="device_001"
    )
)
EventStore.append(txn_event)

# Process events to update read models
event_handler.process_new_events()
```

## Next Steps

1. ✅ Database schema design
2. ✅ Event store implementation
3. ⏳ Seed data generator (with fraud patterns)
4. ⏳ ML fraud detection model
5. ⏳ FastAPI endpoints
6. ⏳ SvelteKit dashboard (future)

## Testing

The `test_event_store.py` script demonstrates:
- Creating events
- Appending to event store
- Processing events through projections
- Querying read models
- Event retrieval and replay

## Fraud Detection Capabilities

The system is designed to detect:

1. **Geographic Impossibility** - Travel speed exceeds reasonable limits
2. **Velocity Anomalies** - Too many transactions in short time
3. **Amount Anomalies** - Unusual transaction amounts
4. **Merchant Anomalies** - Unexpected merchant categories
5. **Temporal Anomalies** - Transactions at unusual times
6. **Device Changes** - Unrecognized devices

These patterns will be implemented in the ML model and seed data generator.
