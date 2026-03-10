#!/usr/bin/env python3
"""
Generate fraud ring patterns (Phase 2).

This script adds organized fraud patterns on top of existing seed data:
- Device sharing rings (3-5 accounts using same device)
- Money mule networks (transfer chains)
- Merchant collusion (multiple users with obscure merchant)
- Synthetic identity rings (accounts created together)
"""

import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from faker import Faker

from src.database import Database
from src.events import (
    EventStore,
    AccountCreated,
    TransactionInitiated,
    TransactionCompleted,
    FundsTransferred,
    DeviceChanged,
    FraudFlagRaised,
    EventMetadata
)

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
fake = Faker()


class FraudRingGenerator:
    """Generates organized fraud ring patterns."""

    def __init__(self):
        # Get existing users
        self.existing_users = Database.fetch_all(
            "SELECT account_id, user_email FROM accounts ORDER BY created_at LIMIT 50"
        )
        logger.info(f"Found {len(self.existing_users)} existing accounts")

    def generate_all_rings(self):
        """Generate all types of fraud rings."""
        logger.info("=" * 80)
        logger.info("GENERATING FRAUD RINGS")
        logger.info("=" * 80)

        self.generate_device_sharing_ring()
        self.generate_money_mule_chain()
        self.generate_merchant_collusion_ring()
        self.generate_synthetic_identity_ring()

        logger.info("=" * 80)
        logger.info("Fraud ring generation complete!")
        logger.info("=" * 80)

    def generate_device_sharing_ring(self):
        """
        Device Sharing Ring: 3 accounts using same device for fraud.

        Pattern:
        - 3 different users
        - Same device_id
        - Transactions within minutes of each other
        - All suspicious amounts
        """
        logger.info("\n1. Creating Device Sharing Ring...")

        # Select 3 random accounts
        ring_accounts = random.sample(self.existing_users, 3)
        shared_device = f"device_fraud_{uuid.uuid4().hex[:12]}"
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)

        logger.info(f"   Ring members: {[u['account_id'] for u in ring_accounts]}")
        logger.info(f"   Shared device: {shared_device}")

        for idx, account in enumerate(ring_accounts):
            # Change device to shared one
            device_event = DeviceChanged(
                aggregate_id=account['account_id'],
                account_id=account['account_id'],
                new_device_id=shared_device,
                device_type="mobile",
                browser="Chrome",
                os="Android",
                is_first_seen=True,
                timestamp=base_time + timedelta(minutes=idx * 2)
            )
            EventStore.append(device_event)

            # Create high-value electronics purchase
            txn_time = base_time + timedelta(minutes=idx * 5 + 10)
            txn_id = f"txn_{uuid.uuid4().hex[:12]}"

            # Transaction initiated
            txn_initiated = TransactionInitiated(
                aggregate_id=txn_id,
                account_id=account['account_id'],
                amount=random.uniform(4500, 5500),
                currency="USD",
                merchant_category="electronics",
                merchant_name="QuickElectronics Online",
                timestamp=txn_time,
                metadata=EventMetadata(
                    device_id=shared_device,
                    latitude=40.7128,
                    longitude=-74.0060
                )
            )
            EventStore.append(txn_initiated)

            # Transaction completed
            txn_completed = TransactionCompleted(
                aggregate_id=txn_id,
                account_id=account['account_id'],
                amount=txn_initiated.amount,
                timestamp=txn_time,
                completed_at=txn_time
            )
            EventStore.append(txn_completed)

        logger.info(f"   ✓ Created device sharing ring with {len(ring_accounts)} accounts")

    def generate_money_mule_chain(self):
        """
        Money Mule Network: A → B → C → D transfer chain.

        Pattern:
        - 4 accounts
        - Sequential transfers within 2 hours
        - Each transfer slightly smaller (taking a cut)
        """
        logger.info("\n2. Creating Money Mule Chain...")

        # Select 4 accounts for the chain
        chain_accounts = random.sample(self.existing_users, 4)
        base_time = datetime.now(timezone.utc) - timedelta(hours=3)
        initial_amount = 25000.00

        logger.info(f"   Chain: {' → '.join([u['account_id'] for u in chain_accounts])}")

        for idx in range(len(chain_accounts) - 1):
            from_account = chain_accounts[idx]
            to_account = chain_accounts[idx + 1]

            # Calculate transfer amount (take 5% cut each time)
            transfer_amount = initial_amount * (0.95 ** idx)
            transfer_time = base_time + timedelta(minutes=idx * 30)

            # Create transfer event
            transfer_id = f"transfer_{uuid.uuid4().hex[:12]}"
            transfer_event = FundsTransferred(
                aggregate_id=transfer_id,
                from_account_id=from_account['account_id'],
                to_account_id=to_account['account_id'],
                amount=round(transfer_amount, 2),
                currency="USD",
                transfer_type="p2p",
                timestamp=transfer_time
            )
            EventStore.append(transfer_event)

            logger.info(f"   ${transfer_amount:,.2f}: {from_account['account_id'][:10]}... → {to_account['account_id'][:10]}...")

        logger.info(f"   ✓ Created money mule chain with {len(chain_accounts)} hops")

    def generate_merchant_collusion_ring(self):
        """
        Merchant Collusion: 5 users transacting with obscure merchant.

        Pattern:
        - 5 different users
        - Same suspicious merchant
        - High amounts just below threshold ($9,500-$9,900)
        - Within 1 week
        """
        logger.info("\n3. Creating Merchant Collusion Ring...")

        # Select 5 accounts
        ring_accounts = random.sample(self.existing_users, 5)
        merchant_name = "Global Trade Solutions LLC"
        base_time = datetime.now(timezone.utc) - timedelta(days=2)

        logger.info(f"   Suspicious merchant: {merchant_name}")
        logger.info(f"   Ring members: {[u['account_id'] for u in ring_accounts]}")

        for idx, account in enumerate(ring_accounts):
            txn_time = base_time + timedelta(hours=idx * 18)
            txn_id = f"txn_{uuid.uuid4().hex[:12]}"
            amount = random.uniform(9500, 9900)

            # Transaction initiated
            txn_initiated = TransactionInitiated(
                aggregate_id=txn_id,
                account_id=account['account_id'],
                amount=amount,
                currency="USD",
                merchant_category="retail",
                merchant_name=merchant_name,
                timestamp=txn_time,
                metadata=EventMetadata(
                    device_id=f"device_{uuid.uuid4().hex[:12]}",
                    latitude=float(fake.latitude()),
                    longitude=float(fake.longitude())
                )
            )
            EventStore.append(txn_initiated)

            # Transaction completed
            txn_completed = TransactionCompleted(
                aggregate_id=txn_id,
                account_id=account['account_id'],
                amount=amount,
                timestamp=txn_time,
                completed_at=txn_time
            )
            EventStore.append(txn_completed)

        logger.info(f"   ✓ Created merchant collusion ring with {len(ring_accounts)} accounts")

    def generate_synthetic_identity_ring(self):
        """
        Synthetic Identity Ring: New accounts created together.

        Pattern:
        - 4 new accounts created within 3 days
        - Sequential email patterns
        - Share similar attributes (same zip code area)
        - 90-day "aging" period with small transactions
        - Then activate with large purchases
        """
        logger.info("\n4. Creating Synthetic Identity Ring...")

        # Create 4 new accounts
        creation_base_time = datetime.now(timezone.utc) - timedelta(days=5)
        shared_device = f"device_synth_{uuid.uuid4().hex[:12]}"
        shared_location = (34.0522, -118.2437)  # LA area

        ring_accounts = []
        for i in range(4):
            account_id = f"acc_{uuid.uuid4().hex[:12]}"
            email = f"user{random.randint(1000, 9999)}_{i}@example.com"

            # Create account
            creation_time = creation_base_time + timedelta(hours=i * 12)
            account_event = AccountCreated(
                aggregate_id=account_id,
                email=email,
                initial_status="active",
                timestamp=creation_time
            )
            EventStore.append(account_event)

            # Register shared device
            device_event = DeviceChanged(
                aggregate_id=account_id,
                account_id=account_id,
                new_device_id=shared_device,
                device_type="desktop",
                browser="Firefox",
                os="Windows",
                is_first_seen=True,
                timestamp=creation_time + timedelta(minutes=5)
            )
            EventStore.append(device_event)

            ring_accounts.append({'account_id': account_id, 'email': email})
            logger.info(f"   Created synthetic account: {account_id}")

        # Create small "aging" transactions
        aging_time = creation_base_time + timedelta(days=1)
        for account in ring_accounts:
            for j in range(2):  # 2 small transactions each
                txn_id = f"txn_{uuid.uuid4().hex[:12]}"
                txn_time = aging_time + timedelta(days=j)

                txn_initiated = TransactionInitiated(
                    aggregate_id=txn_id,
                    account_id=account['account_id'],
                    amount=random.uniform(10, 30),
                    currency="USD",
                    merchant_category="coffee_shop",
                    merchant_name="Starbucks",
                    timestamp=txn_time,
                    metadata=EventMetadata(
                        device_id=shared_device,
                        latitude=shared_location[0],
                        longitude=shared_location[1]
                    )
                )
                EventStore.append(txn_initiated)

                txn_completed = TransactionCompleted(
                    aggregate_id=txn_id,
                    account_id=account['account_id'],
                    amount=txn_initiated.amount,
                    timestamp=txn_time,
                    completed_at=txn_time
                )
                EventStore.append(txn_completed)

        # Now activate with large purchases (today)
        activation_time = datetime.now(timezone.utc) - timedelta(hours=1)
        for account in ring_accounts:
            txn_id = f"txn_{uuid.uuid4().hex[:12]}"

            txn_initiated = TransactionInitiated(
                aggregate_id=txn_id,
                account_id=account['account_id'],
                amount=random.uniform(3000, 4000),
                currency="USD",
                merchant_category="electronics",
                merchant_name="BestBuy",
                timestamp=activation_time,
                metadata=EventMetadata(
                    device_id=shared_device,
                    latitude=shared_location[0],
                    longitude=shared_location[1]
                )
            )
            EventStore.append(txn_initiated)

            txn_completed = TransactionCompleted(
                aggregate_id=txn_id,
                account_id=account['account_id'],
                amount=txn_initiated.amount,
                timestamp=activation_time,
                completed_at=activation_time
            )
            EventStore.append(txn_completed)

        logger.info(f"   ✓ Created synthetic identity ring with {len(ring_accounts)} accounts")


def main():
    # Initialize database connection
    Database.get_connection()

    # Generate fraud rings
    generator = FraudRingGenerator()
    generator.generate_all_rings()

    logger.info("\n✓ Fraud rings added to database")
    logger.info("Run the GraphProjection to sync to Neo4j")


if __name__ == "__main__":
    main()
