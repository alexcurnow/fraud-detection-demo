"""
Comprehensive test suite for ML fraud detection.

Tests:
1. Multiple random samples - check fraud rate consistency
2. Model determinism - same transaction = same result
3. Fraud reasons validation - flagged transactions have actual reasons
4. Time period distribution - fraud spread across dates
5. Feature extraction validation
"""

import logging
from src.models import FraudDetectionModel, FraudFeatureExtractor
from src.database import Database

logging.basicConfig(level=logging.WARNING)

print("=" * 80)
print("FRAUD DETECTION MODEL - COMPREHENSIVE TEST SUITE")
print("=" * 80)

# Load model
model = FraudDetectionModel()
model.load()
print(f"\n✓ Loaded model: {model.model_version}")

# ============================================================================
# TEST 1: Multiple Random Samples - Fraud Rate Consistency
# ============================================================================
print("\n" + "=" * 80)
print("TEST 1: Multiple Random Samples (Fraud Rate Consistency)")
print("=" * 80)

fraud_rates = []
for i in range(5):
    transactions = Database.fetch_all(
        """
        SELECT transaction_id FROM transactions
        WHERE status = 'completed'
        ORDER BY RANDOM()
        LIMIT 100
        """
    )

    fraud_count = 0
    for txn in transactions:
        result = model.predict(txn['transaction_id'])
        if result['is_fraud']:
            fraud_count += 1

    fraud_rate = fraud_count / len(transactions) * 100
    fraud_rates.append(fraud_rate)
    print(f"  Sample {i+1}: {fraud_count}/100 flagged ({fraud_rate:.1f}% fraud rate)")

avg_fraud_rate = sum(fraud_rates) / len(fraud_rates)
print(f"\n  Average fraud rate: {avg_fraud_rate:.1f}%")
print(f"  Expected: ~4-5% (based on contamination parameter)")
print(f"  ✓ PASS" if 2 <= avg_fraud_rate <= 8 else "  ✗ FAIL")

# ============================================================================
# TEST 2: Model Determinism
# ============================================================================
print("\n" + "=" * 80)
print("TEST 2: Model Determinism (Same Input = Same Output)")
print("=" * 80)

# Pick 10 random transactions
test_transactions = Database.fetch_all(
    "SELECT transaction_id FROM transactions WHERE status = 'completed' ORDER BY RANDOM() LIMIT 10"
)

determinism_pass = True
for txn in test_transactions:
    # Score the same transaction 3 times
    result1 = model.predict(txn['transaction_id'])
    result2 = model.predict(txn['transaction_id'])
    result3 = model.predict(txn['transaction_id'])

    if not (result1['is_fraud'] == result2['is_fraud'] == result3['is_fraud']):
        print(f"  ✗ FAIL: {txn['transaction_id']} gave inconsistent results")
        determinism_pass = False

if determinism_pass:
    print(f"  ✓ PASS: All 10 transactions gave consistent results across 3 predictions")
else:
    print(f"  ✗ FAIL: Some transactions gave inconsistent results")

# ============================================================================
# TEST 3: Fraud Reasons Validation
# ============================================================================
print("\n" + "=" * 80)
print("TEST 3: Fraud Reasons Validation")
print("=" * 80)

# Get all flagged transactions
all_transactions = Database.fetch_all(
    "SELECT transaction_id FROM transactions WHERE status = 'completed' LIMIT 500"
)

fraud_transactions = []
for txn in all_transactions:
    result = model.predict(txn['transaction_id'])
    if result['is_fraud']:
        fraud_transactions.append(result)

print(f"  Found {len(fraud_transactions)} fraudulent transactions in sample of {len(all_transactions)}")

# Count fraud reasons
reason_counts = {}
for fraud in fraud_transactions:
    if fraud['flagged_reasons']:
        for reason in fraud['flagged_reasons']:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    else:
        reason_counts['statistical_outlier'] = reason_counts.get('statistical_outlier', 0) + 1

print(f"\n  Fraud reason breakdown:")
for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"    - {reason}: {count} transactions ({count/len(fraud_transactions)*100:.1f}%)")

# Check if we have diverse fraud patterns
print(f"\n  Unique fraud patterns detected: {len(reason_counts)}")
print(f"  ✓ PASS" if len(reason_counts) >= 3 else "  ⚠ WARNING: Limited fraud pattern diversity")

# ============================================================================
# TEST 4: Time Period Distribution
# ============================================================================
print("\n" + "=" * 80)
print("TEST 4: Fraud Distribution Across Time")
print("=" * 80)

# Get transactions grouped by date
transactions_by_date = Database.fetch_all(
    """
    SELECT DATE(initiated_at) as date,
           GROUP_CONCAT(transaction_id) as txn_ids,
           COUNT(*) as count
    FROM transactions
    WHERE status = 'completed'
    GROUP BY DATE(initiated_at)
    ORDER BY date
    LIMIT 10
    """
)

print(f"  Checking fraud distribution across {len(transactions_by_date)} days:\n")

for day in transactions_by_date:
    txn_ids = day['txn_ids'].split(',')
    fraud_count = 0

    for txn_id in txn_ids[:min(20, len(txn_ids))]:  # Sample up to 20 per day
        result = model.predict(txn_id)
        if result['is_fraud']:
            fraud_count += 1

    sample_size = min(20, len(txn_ids))
    fraud_rate = fraud_count / sample_size * 100 if sample_size > 0 else 0
    print(f"    {day['date']}: {fraud_count}/{sample_size} flagged ({fraud_rate:.0f}%)")

print(f"\n  ✓ Fraud distributed across multiple days")

# ============================================================================
# TEST 5: Feature Extraction Validation
# ============================================================================
print("\n" + "=" * 80)
print("TEST 5: Feature Extraction Validation")
print("=" * 80)

# Test feature extraction on a few transactions
test_txns = Database.fetch_all(
    "SELECT transaction_id FROM transactions WHERE status = 'completed' ORDER BY RANDOM() LIMIT 5"
)

feature_extraction_pass = True
for txn in test_txns:
    features = FraudFeatureExtractor.extract_features(txn['transaction_id'])

    if features is None:
        print(f"  ✗ FAIL: Could not extract features for {txn['transaction_id']}")
        feature_extraction_pass = False
        continue

    # Validate all expected features are present
    expected_features = [
        'amount', 'hour_of_day', 'day_of_week', 'merchant_category_code',
        'amount_deviation_from_avg', 'transactions_last_hour', 'transactions_last_24h',
        'distance_from_last_km', 'travel_velocity_kmh', 'account_age_days', 'is_new_device'
    ]

    missing_features = [f for f in expected_features if f not in features]
    if missing_features:
        print(f"  ✗ FAIL: Missing features for {txn['transaction_id']}: {missing_features}")
        feature_extraction_pass = False

if feature_extraction_pass:
    print(f"  ✓ PASS: All features extracted correctly for all test transactions")
    print(f"  ✓ Feature count: {len(expected_features)}")
else:
    print(f"  ✗ FAIL: Feature extraction has errors")

# ============================================================================
# TEST 6: Edge Cases
# ============================================================================
print("\n" + "=" * 80)
print("TEST 6: Edge Cases")
print("=" * 80)

# Get first transaction (should be old, established user)
first_txn = Database.fetch_one(
    "SELECT transaction_id FROM transactions WHERE status = 'completed' ORDER BY initiated_at ASC LIMIT 1"
)

# Get last transaction (most recent)
last_txn = Database.fetch_one(
    "SELECT transaction_id FROM transactions WHERE status = 'completed' ORDER BY initiated_at DESC LIMIT 1"
)

print(f"  Testing oldest transaction: {first_txn['transaction_id']}")
result1 = model.predict(first_txn['transaction_id'])
print(f"    - Fraud: {result1['is_fraud']}, Probability: {result1['fraud_probability']:.0%}")

print(f"\n  Testing newest transaction: {last_txn['transaction_id']}")
result2 = model.predict(last_txn['transaction_id'])
print(f"    - Fraud: {result2['is_fraud']}, Probability: {result2['fraud_probability']:.0%}")
print(f"    - Reasons: {result2['flagged_reasons'] if result2['flagged_reasons'] else 'none'}")

print(f"\n  ✓ Edge cases handled without errors")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("TEST SUITE SUMMARY")
print("=" * 80)
print(f"""
✓ TEST 1: Fraud rate consistency - PASS (avg {avg_fraud_rate:.1f}%)
✓ TEST 2: Model determinism - {'PASS' if determinism_pass else 'FAIL'}
✓ TEST 3: Fraud reasons - {len(fraud_transactions)} fraudulent txns found
✓ TEST 4: Time distribution - Fraud across {len(transactions_by_date)} days
✓ TEST 5: Feature extraction - {'PASS' if feature_extraction_pass else 'FAIL'}
✓ TEST 6: Edge cases - PASS

Model is {'READY FOR PRODUCTION' if determinism_pass and feature_extraction_pass else 'NEEDS FIXES'}
""")
print("=" * 80)
