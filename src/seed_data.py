"""Seed data generator with realistic transaction patterns and fraud anomalies."""

import random
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from faker import Faker
import uuid

from .events import (
    EventStore,
    AccountCreated,
    TransactionInitiated,
    TransactionCompleted,
    TransactionFailed,
    LoginAttempted,
    DeviceChanged,
    EventMetadata
)
from .init_system import initialize_system

logger = logging.getLogger(__name__)
fake = Faker()

# Merchant categories with typical spending ranges
MERCHANT_CATEGORIES = {
    'grocery': (20, 200),
    'gas': (30, 80),
    'restaurant': (15, 150),
    'coffee_shop': (3, 15),
    'retail': (25, 300),
    'electronics': (50, 2000),
    'pharmacy': (10, 100),
    'utilities': (50, 300),
    'entertainment': (15, 100),
    'travel': (100, 1500),
    'hotel': (100, 500),
    'online_shopping': (20, 500),
}

# Device types for fingerprinting
DEVICE_TYPES = ['mobile', 'desktop', 'tablet']
BROWSERS = ['Chrome', 'Firefox', 'Safari', 'Edge']
OPERATING_SYSTEMS = ['iOS', 'Android', 'Windows', 'macOS', 'Linux']


class UserProfile:
    """Represents a user with behavioral patterns."""

    def __init__(self, account_id: str, email: str, is_fraudster: bool = False):
        self.account_id = account_id
        self.email = email
        self.is_fraudster = is_fraudster

        # Home location (used for geographic baseline)
        self.home_lat = float(fake.latitude())
        self.home_lon = float(fake.longitude())

        # Typical transaction patterns
        self.avg_transaction_amount = random.uniform(30, 150)
        self.std_transaction_amount = self.avg_transaction_amount * 0.4

        # Preferred merchant categories (2-4 categories)
        self.preferred_categories = random.sample(
            list(MERCHANT_CATEGORIES.keys()),
            k=random.randint(2, 4)
        )

        # Typical transaction hours (business hours 9-5 vs night owl)
        if random.random() < 0.7:  # 70% business hours users
            self.typical_hours = list(range(9, 22))  # 9 AM to 10 PM
        else:  # 30% night owls
            self.typical_hours = list(range(0, 24))

        # Devices
        self.primary_device = self._generate_device_id()
        self.known_devices = [self.primary_device]

        # IP addresses (simulate home and work)
        self.home_ip = fake.ipv4()
        self.work_ip = fake.ipv4()

        # Transaction velocity (transactions per day)
        self.daily_transaction_rate = random.uniform(1, 5)

    def _generate_device_id(self) -> str:
        """Generate a device fingerprint."""
        return f"device_{uuid.uuid4().hex[:12]}"

    def get_typical_location(self) -> Tuple[float, float]:
        """Get a location near home (within ~50km radius)."""
        # Add some noise to home location
        lat_offset = random.uniform(-0.5, 0.5)  # ~55km at equator
        lon_offset = random.uniform(-0.5, 0.5)
        return (
            self.home_lat + lat_offset,
            self.home_lon + lon_offset
        )

    def get_typical_amount(self) -> float:
        """Get a typical transaction amount based on user's pattern."""
        amount = random.gauss(self.avg_transaction_amount, self.std_transaction_amount)
        return max(5.0, round(amount, 2))  # Minimum $5

    def get_typical_category(self) -> str:
        """Get a merchant category the user typically shops at."""
        return random.choice(self.preferred_categories)


class SeedDataGenerator:
    """Generates realistic seed data with fraud patterns."""

    def __init__(self, num_users: int = 100, fraud_rate: float = 0.03):
        """
        Initialize seed data generator.

        Args:
            num_users: Number of user accounts to create
            fraud_rate: Percentage of fraudulent transactions (0.02-0.05 recommended)
        """
        self.num_users = num_users
        self.fraud_rate = fraud_rate
        self.users: List[UserProfile] = []
        self.start_date = datetime.now(timezone.utc) - timedelta(days=30)  # 30 days of history (faster seed generation)

    def generate_all(self):
        """Generate complete dataset: users, transactions, and fraud."""
        logger.info(f"Generating seed data: {self.num_users} users, {self.fraud_rate*100}% fraud rate")

        # Create user accounts
        self._create_accounts()

        # Generate normal transactions
        self._generate_normal_transactions()

        # Inject fraudulent transactions
        self._generate_fraud_transactions()

        logger.info("Seed data generation complete!")

    def _create_accounts(self):
        """Create user accounts."""
        logger.info(f"Creating {self.num_users} user accounts...")

        for i in range(self.num_users):
            account_id = f"acc_{uuid.uuid4().hex[:12]}"
            email = fake.email()

            # 3% of users will be fraudsters (for later fraud injection)
            is_fraudster = random.random() < 0.03

            user = UserProfile(account_id, email, is_fraudster)
            self.users.append(user)

            # Create account event
            account_event = AccountCreated(
                aggregate_id=account_id,
                email=email,
                timestamp=self.start_date + timedelta(days=random.randint(0, 30)),
                metadata=EventMetadata(
                    ip_address=user.home_ip,
                    device_id=user.primary_device,
                    latitude=user.home_lat,
                    longitude=user.home_lon
                )
            )
            EventStore.append(account_event)

            # Register primary device
            device_event = DeviceChanged(
                aggregate_id=account_id,
                account_id=account_id,
                new_device_id=user.primary_device,
                device_type=random.choice(['mobile', 'desktop', 'tablet']),
                browser=random.choice(['Chrome', 'Firefox', 'Safari']),
                os=random.choice(['Windows', 'macOS', 'iOS', 'Android']),
                timestamp=account_event.timestamp,
                metadata=EventMetadata(
                    ip_address=user.home_ip,
                    device_id=user.primary_device
                )
            )
            EventStore.append(device_event)

            # Initial login
            login_event = LoginAttempted(
                aggregate_id=f"session_{uuid.uuid4().hex[:8]}",
                account_id=account_id,
                success=True,
                timestamp=account_event.timestamp + timedelta(minutes=1),
                metadata=EventMetadata(
                    ip_address=user.home_ip,
                    device_id=user.primary_device,
                    latitude=user.home_lat,
                    longitude=user.home_lon
                )
            )
            EventStore.append(login_event)

        logger.info(f"Created {len(self.users)} accounts ({sum(1 for u in self.users if u.is_fraudster)} flagged as potential fraudsters)")

    def _generate_normal_transactions(self):
        """Generate normal, legitimate transactions."""
        logger.info("Generating normal transactions...")

        transaction_count = 0
        current_date = self.start_date + timedelta(days=7)  # Start 7 days after accounts created
        end_date = datetime.now(timezone.utc)

        while current_date < end_date:
            # Each day, some users make transactions
            for user in self.users:
                if user.is_fraudster:
                    continue  # Skip fraudsters for normal transactions

                # Probability of transaction on this day
                if random.random() < (user.daily_transaction_rate / 7):  # Avg rate per week
                    num_transactions = random.randint(1, 3)

                    for _ in range(num_transactions):
                        self._create_normal_transaction(user, current_date)
                        transaction_count += 1

            current_date += timedelta(days=1)

        logger.info(f"Generated {transaction_count} normal transactions")

    def _create_normal_transaction(self, user: UserProfile, base_date: datetime):
        """Create a single normal transaction for a user."""
        # Pick a typical hour
        hour = random.choice(user.typical_hours)
        timestamp = base_date.replace(
            hour=hour,
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )

        # Typical location, amount, and category
        lat, lon = user.get_typical_location()
        category = user.get_typical_category()
        min_amount, max_amount = MERCHANT_CATEGORIES[category]
        amount = round(random.uniform(min_amount, max_amount), 2)

        # Use primary device 90% of the time
        device_id = user.primary_device if random.random() < 0.9 else random.choice(user.known_devices)
        ip_address = user.home_ip if random.random() < 0.7 else user.work_ip

        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

        # Transaction initiated
        txn_initiated = TransactionInitiated(
            aggregate_id=transaction_id,
            account_id=user.account_id,
            amount=amount,
            currency="USD",
            merchant_category=category,
            merchant_name=fake.company(),
            timestamp=timestamp,
            metadata=EventMetadata(
                latitude=lat,
                longitude=lon,
                device_id=device_id,
                ip_address=ip_address
            )
        )
        EventStore.append(txn_initiated)

        # 95% of transactions complete successfully
        if random.random() < 0.95:
            txn_completed = TransactionCompleted(
                aggregate_id=transaction_id,
                account_id=user.account_id,
                amount=amount,
                timestamp=timestamp + timedelta(seconds=random.randint(1, 5)),
                completed_at=timestamp + timedelta(seconds=random.randint(1, 5))
            )
            EventStore.append(txn_completed)
        else:
            # Failed transaction
            txn_failed = TransactionFailed(
                aggregate_id=transaction_id,
                account_id=user.account_id,
                reason=random.choice(['insufficient_funds', 'card_declined', 'timeout']),
                timestamp=timestamp + timedelta(seconds=random.randint(1, 5)),
                failed_at=timestamp + timedelta(seconds=random.randint(1, 5))
            )
            EventStore.append(txn_failed)

    def _generate_fraud_transactions(self):
        """Generate fraudulent transactions with various patterns."""
        logger.info("Injecting fraudulent transactions...")

        fraud_count = 0
        total_transactions = EventStore.get_event_count()
        target_fraud_count = int(total_transactions * self.fraud_rate)

        fraud_patterns = [
            self._fraud_geographic_impossibility,
            self._fraud_velocity_anomaly,
            self._fraud_unusual_amount,
            self._fraud_unusual_merchant,
            self._fraud_suspicious_timing,
        ]

        while fraud_count < target_fraud_count:
            # Pick random user
            user = random.choice(self.users)

            # Pick random fraud pattern
            fraud_pattern = random.choice(fraud_patterns)
            fraud_pattern(user)

            fraud_count += 1

        logger.info(f"Injected {fraud_count} fraudulent transactions")

    def _fraud_geographic_impossibility(self, user: UserProfile):
        """Create transaction in impossible geographic location."""
        # Last transaction location
        base_time = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 6))

        # Transaction from home location
        self._create_normal_transaction(user, base_time)

        # Impossible transaction (across the world) 30 minutes later
        impossible_time = base_time + timedelta(minutes=30)

        # Random location on opposite side of earth
        impossible_lat = fake.latitude()
        impossible_lon = fake.longitude()

        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        category = random.choice(list(MERCHANT_CATEGORIES.keys()))
        min_amount, max_amount = MERCHANT_CATEGORIES[category]
        amount = round(random.uniform(min_amount, max_amount), 2)

        txn = TransactionInitiated(
            aggregate_id=transaction_id,
            account_id=user.account_id,
            amount=amount,
            merchant_category=category,
            merchant_name=fake.company(),
            timestamp=impossible_time,
            metadata=EventMetadata(
                latitude=impossible_lat,
                longitude=impossible_lon,
                device_id=user.primary_device,
                ip_address=fake.ipv4()
            )
        )
        EventStore.append(txn)

        # Complete transaction
        EventStore.append(TransactionCompleted(
            aggregate_id=transaction_id,
            account_id=user.account_id,
            amount=amount,
            timestamp=impossible_time + timedelta(seconds=2)
        ))

    def _fraud_velocity_anomaly(self, user: UserProfile):
        """Create rapid succession of transactions."""
        base_time = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 12))

        # 5-10 transactions in 10 minutes
        num_transactions = random.randint(5, 10)

        for i in range(num_transactions):
            timestamp = base_time + timedelta(minutes=i * 2)
            lat, lon = user.get_typical_location()

            category = random.choice(list(MERCHANT_CATEGORIES.keys()))
            min_amount, max_amount = MERCHANT_CATEGORIES[category]
            amount = round(random.uniform(min_amount, max_amount), 2)

            transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

            txn = TransactionInitiated(
                aggregate_id=transaction_id,
                account_id=user.account_id,
                amount=amount,
                merchant_category=category,
                merchant_name=fake.company(),
                timestamp=timestamp,
                metadata=EventMetadata(
                    latitude=lat,
                    longitude=lon,
                    device_id=user.primary_device,
                    ip_address=user.home_ip
                )
            )
            EventStore.append(txn)
            EventStore.append(TransactionCompleted(
                aggregate_id=transaction_id,
                account_id=user.account_id,
                amount=amount,
                timestamp=timestamp + timedelta(seconds=1)
            ))

    def _fraud_unusual_amount(self, user: UserProfile):
        """Create transaction with unusually large amount."""
        timestamp = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 24))
        lat, lon = user.get_typical_location()

        # 10-50x normal amount
        amount = round(user.avg_transaction_amount * random.uniform(10, 50), 2)

        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        category = 'electronics'  # Large purchases often electronics

        txn = TransactionInitiated(
            aggregate_id=transaction_id,
            account_id=user.account_id,
            amount=amount,
            merchant_category=category,
            merchant_name=fake.company(),
            timestamp=timestamp,
            metadata=EventMetadata(
                latitude=lat,
                longitude=lon,
                device_id=user.primary_device,
                ip_address=user.home_ip
            )
        )
        EventStore.append(txn)
        EventStore.append(TransactionCompleted(
            aggregate_id=transaction_id,
            account_id=user.account_id,
            amount=amount,
            timestamp=timestamp + timedelta(seconds=2)
        ))

    def _fraud_unusual_merchant(self, user: UserProfile):
        """Create transaction in unusual merchant category."""
        timestamp = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 24))
        lat, lon = user.get_typical_location()

        # Pick category NOT in user's preferred list
        unusual_categories = [c for c in MERCHANT_CATEGORIES.keys() if c not in user.preferred_categories]
        category = random.choice(unusual_categories)
        min_amount, max_amount = MERCHANT_CATEGORIES[category]
        amount = round(random.uniform(min_amount, max_amount), 2)

        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

        txn = TransactionInitiated(
            aggregate_id=transaction_id,
            account_id=user.account_id,
            amount=amount * 2,  # Also make it higher than typical
            merchant_category=category,
            merchant_name=fake.company(),
            timestamp=timestamp,
            metadata=EventMetadata(
                latitude=lat,
                longitude=lon,
                device_id=user.primary_device,
                ip_address=user.home_ip
            )
        )
        EventStore.append(txn)
        EventStore.append(TransactionCompleted(
            aggregate_id=transaction_id,
            account_id=user.account_id,
            amount=amount * 2,
            timestamp=timestamp + timedelta(seconds=2)
        ))

    def _fraud_suspicious_timing(self, user: UserProfile):
        """Create transaction at 3 AM for a business-hours user."""
        if 3 in user.typical_hours:
            # User is already a night owl, pick different pattern
            self._fraud_velocity_anomaly(user)
            return

        # 3 AM transaction
        base_date = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 5))
        timestamp = base_date.replace(hour=3, minute=random.randint(0, 59))

        lat, lon = user.get_typical_location()
        category = random.choice(list(MERCHANT_CATEGORIES.keys()))
        min_amount, max_amount = MERCHANT_CATEGORIES[category]
        amount = round(random.uniform(min_amount, max_amount), 2)

        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

        txn = TransactionInitiated(
            aggregate_id=transaction_id,
            account_id=user.account_id,
            amount=amount,
            merchant_category=category,
            merchant_name=fake.company(),
            timestamp=timestamp,
            metadata=EventMetadata(
                latitude=lat,
                longitude=lon,
                device_id=user.primary_device,
                ip_address=fake.ipv4()  # Different IP at 3 AM
            )
        )
        EventStore.append(txn)
        EventStore.append(TransactionCompleted(
            aggregate_id=transaction_id,
            account_id=user.account_id,
            amount=amount,
            timestamp=timestamp + timedelta(seconds=2)
        ))


def seed_database(num_users: int = 100, fraud_rate: float = 0.03, rebuild: bool = True):
    """
    Seed the database with realistic data.

    Args:
        num_users: Number of user accounts to create
        fraud_rate: Percentage of fraudulent transactions (0.02-0.05)
        rebuild: If True, rebuild database from scratch
    """
    # Initialize system
    event_handler = initialize_system(force_rebuild=rebuild)

    # Generate seed data
    generator = SeedDataGenerator(num_users=num_users, fraud_rate=fraud_rate)
    generator.generate_all()

    # Process all events to build read models
    logger.info("Building read models from events...")
    results = event_handler.process_new_events()

    for projection_name, count in results.items():
        logger.info(f"{projection_name}: Processed {count} events")

    # Summary statistics
    from .database import Database

    total_accounts = Database.fetch_one("SELECT COUNT(*) as count FROM accounts")['count']
    total_transactions = Database.fetch_one("SELECT COUNT(*) as count FROM transactions")['count']
    completed_transactions = Database.fetch_one("SELECT COUNT(*) as count FROM transactions WHERE status = 'completed'")['count']

    logger.info("\n" + "=" * 80)
    logger.info("SEED DATA SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Accounts created: {total_accounts}")
    logger.info(f"Total transactions: {total_transactions}")
    logger.info(f"Completed transactions: {completed_transactions}")
    logger.info(f"Target fraud rate: {fraud_rate * 100}%")
    logger.info("=" * 80)


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Parse arguments
    num_users = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    fraud_rate = float(sys.argv[2]) if len(sys.argv) > 2 else 0.03

    seed_database(num_users=num_users, fraud_rate=fraud_rate, rebuild=True)
