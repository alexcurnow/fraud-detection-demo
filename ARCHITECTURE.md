# Fraud Detection Demo - Architecture

## Event Sourcing Pattern

### Core Concept
All state changes are captured as immutable events in an append-only log. Current state is derived by replaying events through projections.

### Event Store
**Table: `events`**
- Single source of truth
- Append-only (never UPDATE or DELETE)
- Contains all business events with full context

**Event Types:**
- `TransactionInitiated`, `TransactionCompleted`, `TransactionFailed`
- `AccountCreated`, `LoginAttempted`
- `DeviceChanged`, `LocationChanged`
- `FraudFlagRaised`

### Read Models (Projections)

Read models are built by processing events and are optimized for queries:

1. **accounts** - Current account state and aggregates
2. **transactions** - Current transaction status
3. **fraud_scores** - ML-generated fraud predictions
4. **user_profiles** - Behavioral patterns for anomaly detection
5. **devices** - Device fingerprinting
6. **login_attempts** - Authentication history
7. **location_events** - Geographic tracking for impossibility detection

### Fraud Detection Features

The schema supports detection of:

1. **Geographic Impossibility**
   - Track location changes via `location_events`
   - Calculate velocity between events
   - Compare to `user_profiles.max_velocity_kmh`

2. **Velocity Anomalies**
   - Rapid transactions in `transactions` table
   - High-frequency login attempts in `login_attempts`

3. **Amount Anomalies**
   - Compare to `user_profiles.avg_transaction_amount`, `median_transaction_amount`, `std_transaction_amount`
   - Flag transactions outside normal range

4. **Merchant Category Anomalies**
   - Compare to `user_profiles.typical_merchant_categories`

5. **Temporal Anomalies**
   - Compare to `user_profiles.typical_transaction_hours`
   - Flag 3 AM transactions for 9-5 users

6. **Device Changes**
   - Track via `devices` table
   - Flag unknown devices

### ML Model Pipeline

1. Extract features from read models
2. Train model on labeled data (2-5% fraud rate)
3. Store model metadata in `ml_models` table
4. Score new transactions, store in `fraud_scores`

### Projection Rebuilding

The `projection_state` table tracks which events have been processed. This allows:
- Rebuilding projections from events if corrupted
- Creating new projections from historical events
- Temporal queries ("what was the state on date X?")

## Data Flow

```
User Action → Event Store → Projections → ML Model → Fraud Score
                   ↓
              Immutable Log
```

1. Action occurs (transaction, login, etc.)
2. Event appended to `events` table
3. Event processors update read models
4. ML model scores transaction using read model data
5. Fraud score stored in `fraud_scores`
6. API returns result
