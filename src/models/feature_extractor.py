"""
Feature Extraction for Fraud Detection ML Model

CONCEPTS:
- Features: Numerical inputs the ML model uses to make predictions
- Feature Engineering: Converting raw data into meaningful features
- Good features capture patterns that distinguish fraud from legitimate transactions
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
import math
from ..database import Database

logger = logging.getLogger(__name__)


class FraudFeatureExtractor:
    """
    Extracts features from transaction data for ML model.

    Features we extract:
    1. Transaction-level: amount, time of day, merchant category
    2. User behavior: deviation from normal patterns
    3. Geographic: location changes, impossible travel
    4. Velocity: transaction frequency
    """

    @staticmethod
    def extract_features(transaction_id: str) -> Optional[Dict[str, float]]:
        """
        Extract features for a specific transaction.

        Returns a dictionary of feature_name -> feature_value (all floats)
        Returns None if transaction not found.
        """
        # Get transaction details from database
        txn = Database.fetch_one(
            """
            SELECT t.*, a.account_id, a.total_transactions, a.total_volume
            FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
            WHERE t.transaction_id = ?
            """,
            (transaction_id,)
        )

        if not txn:
            logger.warning(f"Transaction {transaction_id} not found")
            return None

        account_id = txn['account_id']
        features = {}

        # ====================================================================
        # FEATURE 1: Transaction Amount (normalized)
        # WHY: Fraudsters often make unusually large purchases
        # ====================================================================
        features['amount'] = float(txn['amount'])

        # ====================================================================
        # FEATURE 2: Hour of Day (0-23)
        # WHY: Fraud often happens at unusual times (e.g., 3 AM)
        # ====================================================================
        initiated_at = datetime.fromisoformat(txn['initiated_at'])
        features['hour_of_day'] = float(initiated_at.hour)

        # ====================================================================
        # FEATURE 3: Day of Week (0=Monday, 6=Sunday)
        # WHY: Fraud patterns may differ on weekends vs weekdays
        # ====================================================================
        features['day_of_week'] = float(initiated_at.weekday())

        # ====================================================================
        # FEATURE 4: Merchant Category (encoded as number)
        # WHY: Certain categories (electronics, travel) are fraud-prone
        # ====================================================================
        category_mapping = {
            'grocery': 1, 'gas': 2, 'restaurant': 3, 'coffee_shop': 4,
            'retail': 5, 'electronics': 6, 'pharmacy': 7, 'utilities': 8,
            'entertainment': 9, 'travel': 10, 'hotel': 11, 'online_shopping': 12
        }
        features['merchant_category_code'] = float(
            category_mapping.get(txn['merchant_category'], 0)
        )

        # ====================================================================
        # FEATURE 5: Deviation from User's Average Amount
        # WHY: If user normally spends $50 but this is $5000 → suspicious!
        # ====================================================================
        user_avg = Database.fetch_one(
            """
            SELECT
                AVG(amount) as avg_amount,
                COUNT(*) as txn_count
            FROM transactions
            WHERE account_id = ? AND status = 'completed'
                AND transaction_id != ?
            """,
            (account_id, transaction_id)
        )

        if user_avg and user_avg['avg_amount']:
            avg_amount = float(user_avg['avg_amount'])
            # Z-score: How many standard deviations from the mean?
            # High z-score = unusual transaction
            features['amount_deviation_from_avg'] = (
                features['amount'] - avg_amount
            ) / max(avg_amount, 1.0)  # Avoid division by zero
        else:
            # First transaction for user
            features['amount_deviation_from_avg'] = 0.0

        # ====================================================================
        # FEATURE 6: Transaction Velocity (transactions in last hour)
        # WHY: Fraudsters often make rapid successive transactions
        # ====================================================================
        one_hour_ago = initiated_at - timedelta(hours=1)
        velocity = Database.fetch_one(
            """
            SELECT COUNT(*) as count
            FROM transactions
            WHERE account_id = ?
                AND initiated_at > ?
                AND initiated_at < ?
            """,
            (account_id, one_hour_ago.isoformat(), initiated_at.isoformat())
        )
        features['transactions_last_hour'] = float(velocity['count'] if velocity else 0)

        # ====================================================================
        # FEATURE 7: Transactions in Last 24 Hours
        # WHY: High daily volume can indicate account compromise
        # ====================================================================
        one_day_ago = initiated_at - timedelta(days=1)
        daily_velocity = Database.fetch_one(
            """
            SELECT COUNT(*) as count
            FROM transactions
            WHERE account_id = ?
                AND initiated_at > ?
                AND initiated_at < ?
            """,
            (account_id, one_day_ago.isoformat(), initiated_at.isoformat())
        )
        features['transactions_last_24h'] = float(daily_velocity['count'] if daily_velocity else 0)

        # ====================================================================
        # FEATURE 8: Geographic Distance from Last Transaction
        # WHY: Impossible travel (NYC to Tokyo in 30 min) = fraud
        # ====================================================================
        if txn['latitude'] and txn['longitude']:
            last_location = Database.fetch_one(
                """
                SELECT latitude, longitude, timestamp
                FROM location_events
                WHERE account_id = ?
                    AND timestamp < ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (account_id, initiated_at.isoformat())
            )

            if last_location and last_location['latitude']:
                # Calculate distance using Haversine formula
                distance_km = FraudFeatureExtractor._haversine_distance(
                    float(txn['latitude']), float(txn['longitude']),
                    float(last_location['latitude']), float(last_location['longitude'])
                )
                features['distance_from_last_km'] = distance_km

                # Calculate velocity (km/h)
                time_diff = initiated_at - datetime.fromisoformat(last_location['timestamp'])
                hours = max(time_diff.total_seconds() / 3600, 0.01)  # Avoid division by zero
                features['travel_velocity_kmh'] = distance_km / hours
            else:
                features['distance_from_last_km'] = 0.0
                features['travel_velocity_kmh'] = 0.0
        else:
            features['distance_from_last_km'] = 0.0
            features['travel_velocity_kmh'] = 0.0

        # ====================================================================
        # FEATURE 9: Account Age (days since creation)
        # WHY: New accounts are more fraud-prone
        # ====================================================================
        account = Database.fetch_one(
            "SELECT created_at FROM accounts WHERE account_id = ?",
            (account_id,)
        )
        if account:
            created_at = datetime.fromisoformat(account['created_at'])
            account_age_days = (initiated_at - created_at).days
            features['account_age_days'] = float(max(account_age_days, 0))
        else:
            features['account_age_days'] = 0.0

        # ====================================================================
        # FEATURE 10: Is New Device?
        # WHY: Transactions from unknown devices are suspicious
        # ====================================================================
        if txn['device_id']:
            device = Database.fetch_one(
                """
                SELECT first_seen FROM devices
                WHERE device_id = ? AND account_id = ?
                """,
                (txn['device_id'], account_id)
            )

            if device:
                first_seen = datetime.fromisoformat(device['first_seen'])
                device_age_hours = (initiated_at - first_seen).total_seconds() / 3600
                # 1.0 if device is very new (< 1 hour old), 0.0 if old
                features['is_new_device'] = 1.0 if device_age_hours < 1.0 else 0.0
            else:
                features['is_new_device'] = 1.0  # Unknown device
        else:
            features['is_new_device'] = 0.0

        logger.debug(f"Extracted {len(features)} features for transaction {transaction_id}")
        return features

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points on Earth using Haversine formula.

        Returns distance in kilometers.

        CONCEPT: The Haversine formula calculates the great-circle distance
        between two points on a sphere (Earth) given their latitudes and longitudes.
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        # Haversine formula
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))

        # Earth's radius in kilometers
        earth_radius_km = 6371.0

        return earth_radius_km * c

    @staticmethod
    def extract_features_for_all_transactions() -> List[Dict]:
        """
        Extract features for all completed transactions in the database.

        Returns list of dictionaries, each containing:
        - transaction_id
        - features (dict of feature values)
        - is_fraud (boolean, based on status='flagged')
        """
        transactions = Database.fetch_all(
            """
            SELECT transaction_id, status
            FROM transactions
            WHERE status IN ('completed', 'flagged')
            ORDER BY initiated_at
            """
        )

        results = []
        for txn in transactions:
            features = FraudFeatureExtractor.extract_features(txn['transaction_id'])
            if features:
                results.append({
                    'transaction_id': txn['transaction_id'],
                    'features': features,
                    # Label: fraud if status is 'flagged', legitimate otherwise
                    'is_fraud': txn['status'] == 'flagged'
                })

        logger.info(f"Extracted features for {len(results)} transactions")
        return results
