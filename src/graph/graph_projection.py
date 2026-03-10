"""Graph projection - builds Neo4j graph from events."""

import logging
import hashlib
from ..events.event_processor import EventProcessor
from ..events.event_models import (
    BaseEvent,
    AccountCreated,
    TransactionInitiated,
    TransactionCompleted,
    DeviceChanged,
    LocationChanged,
    FundsTransferred,
    FraudFlagRaised
)
from .connection import GraphDatabase

logger = logging.getLogger(__name__)


class GraphProjection(EventProcessor):
    """
    Projects events into Neo4j graph database.

    Creates nodes and relationships representing the fraud detection network:
    - (User)-[:OWNS]->(Device)
    - (User)-[:MAKES]->(Transaction)
    - (Transaction)-[:AT]->(Merchant)
    - (Transaction)-[:FROM]->(Location)
    - (User)-[:TRANSFERS_TO]->(User)
    - (User)-[:SHARES_DEVICE_WITH]->(User) [derived]
    """

    def __init__(self):
        super().__init__(projection_name="GraphProjection")
        # Ensure constraints exist
        GraphDatabase.create_constraints()

    def process_event(self, event: BaseEvent) -> None:
        """Process an event and update the graph."""

        if isinstance(event, AccountCreated):
            self._handle_account_created(event)

        elif isinstance(event, TransactionInitiated):
            self._handle_transaction_initiated(event)

        elif isinstance(event, TransactionCompleted):
            self._handle_transaction_completed(event)

        elif isinstance(event, DeviceChanged):
            self._handle_device_changed(event)

        elif isinstance(event, LocationChanged):
            self._handle_location_changed(event)

        elif isinstance(event, FundsTransferred):
            self._handle_funds_transferred(event)

        elif isinstance(event, FraudFlagRaised):
            self._handle_fraud_flag_raised(event)

    def can_handle(self, event: BaseEvent) -> bool:
        """Only handle events relevant to graph."""
        return isinstance(event, (
            AccountCreated,
            TransactionInitiated,
            TransactionCompleted,
            DeviceChanged,
            LocationChanged,
            FundsTransferred,
            FraudFlagRaised
        ))

    def _handle_account_created(self, event: AccountCreated) -> None:
        """Create User node."""
        query = """
        MERGE (u:User {account_id: $account_id})
        SET u.email = $email,
            u.status = $status,
            u.created_at = datetime($created_at)
        """
        GraphDatabase.execute_write(query, {
            'account_id': event.aggregate_id,
            'email': event.email,
            'status': event.initial_status,
            'created_at': event.timestamp.isoformat()
        })
        logger.debug(f"Created User node: {event.aggregate_id}")

    def _handle_transaction_initiated(self, event: TransactionInitiated) -> None:
        """
        Create Transaction node and relationships.

        Creates:
        - Transaction node
        - (User)-[:MAKES]->(Transaction)
        - (Transaction)-[:AT]->(Merchant)
        - (Transaction)-[:FROM]->(Location)
        """
        # Create merchant_id from merchant name (hash for uniqueness)
        merchant_id = hashlib.md5(
            f"{event.merchant_name}:{event.merchant_category}".encode()
        ).hexdigest()[:12]

        # Create location_id from coordinates
        location_id = None
        if event.metadata.latitude and event.metadata.longitude:
            location_id = hashlib.md5(
                f"{event.metadata.latitude:.4f},{event.metadata.longitude:.4f}".encode()
            ).hexdigest()[:12]

        query = """
        // Create or update User
        MERGE (u:User {account_id: $account_id})

        // Create Transaction
        MERGE (t:Transaction {transaction_id: $transaction_id})
        SET t.amount = $amount,
            t.currency = $currency,
            t.status = 'initiated',
            t.timestamp = datetime($timestamp)

        // Create Merchant
        MERGE (m:Merchant {merchant_id: $merchant_id})
        SET m.name = $merchant_name,
            m.category = $merchant_category

        // Create relationships
        MERGE (u)-[:MAKES]->(t)
        MERGE (t)-[:AT]->(m)
        """

        params = {
            'account_id': event.account_id,
            'transaction_id': event.aggregate_id,
            'amount': event.amount,
            'currency': event.currency,
            'timestamp': event.timestamp.isoformat(),
            'merchant_id': merchant_id,
            'merchant_name': event.merchant_name,
            'merchant_category': event.merchant_category
        }

        # Add location relationship if coordinates available
        if location_id:
            query += """
            // Create Location
            WITH t, $latitude as lat, $longitude as lon
            MERGE (l:Location {location_id: $location_id})
            SET l.latitude = lat,
                l.longitude = lon
            MERGE (t)-[:FROM]->(l)
            """
            params['location_id'] = location_id
            params['latitude'] = event.metadata.latitude
            params['longitude'] = event.metadata.longitude

        GraphDatabase.execute_write(query, params)
        logger.debug(f"Created Transaction node: {event.aggregate_id}")

    def _handle_transaction_completed(self, event: TransactionCompleted) -> None:
        """Update transaction status to completed."""
        query = """
        MATCH (t:Transaction {transaction_id: $transaction_id})
        SET t.status = 'completed',
            t.completed_at = datetime($completed_at)
        """
        GraphDatabase.execute_write(query, {
            'transaction_id': event.aggregate_id,
            'completed_at': event.completed_at.isoformat()
        })
        logger.debug(f"Transaction completed: {event.aggregate_id}")

    def _handle_device_changed(self, event: DeviceChanged) -> None:
        """
        Create device relationship.

        Creates:
        - Device node
        - (User)-[:OWNS]->(Device)
        - (User)-[:SHARES_DEVICE_WITH]->(User) [if device shared]
        """
        query = """
        // Get or create User and Device
        MERGE (u:User {account_id: $account_id})
        MERGE (d:Device {device_id: $device_id})
        SET d.type = $device_type,
            d.browser = $browser,
            d.os = $os

        // Create OWNS relationship
        MERGE (u)-[r:OWNS]->(d)
        SET r.first_seen = COALESCE(r.first_seen, datetime($timestamp)),
            r.last_seen = datetime($timestamp)

        // Find other users who own this device (device sharing)
        WITH u, d
        MATCH (other:User)-[:OWNS]->(d)
        WHERE other.account_id <> u.account_id
        MERGE (u)-[:SHARES_DEVICE_WITH]->(other)
        MERGE (other)-[:SHARES_DEVICE_WITH]->(u)
        """
        GraphDatabase.execute_write(query, {
            'account_id': event.account_id,
            'device_id': event.new_device_id,
            'device_type': event.device_type,
            'browser': event.browser,
            'os': event.os,
            'timestamp': event.timestamp.isoformat()
        })
        logger.debug(f"User {event.account_id} owns device {event.new_device_id}")

    def _handle_location_changed(self, event: LocationChanged) -> None:
        """Track location changes for geographic analysis."""
        location_id = hashlib.md5(
            f"{event.new_latitude:.4f},{event.new_longitude:.4f}".encode()
        ).hexdigest()[:12]

        query = """
        MERGE (u:User {account_id: $account_id})
        MERGE (l:Location {location_id: $location_id})
        SET l.latitude = $latitude,
            l.longitude = $longitude
        MERGE (u)-[r:VISITED]->(l)
        ON CREATE SET r.first_seen = datetime($timestamp), r.visit_count = 1
        ON MATCH SET r.last_seen = datetime($timestamp), r.visit_count = r.visit_count + 1
        """
        GraphDatabase.execute_write(query, {
            'account_id': event.account_id,
            'location_id': location_id,
            'latitude': event.new_latitude,
            'longitude': event.new_longitude,
            'timestamp': event.timestamp.isoformat()
        })
        logger.debug(f"User {event.account_id} visited location {location_id}")

    def _handle_funds_transferred(self, event: FundsTransferred) -> None:
        """
        Create money transfer relationship.

        Creates:
        - (FromUser)-[:TRANSFERS_TO]->(ToUser) with amount and timestamp
        """
        query = """
        MERGE (from:User {account_id: $from_account_id})
        MERGE (to:User {account_id: $to_account_id})
        CREATE (from)-[t:TRANSFERS_TO]->(to)
        SET t.amount = $amount,
            t.currency = $currency,
            t.transfer_type = $transfer_type,
            t.timestamp = datetime($timestamp),
            t.transfer_id = $transfer_id
        """
        GraphDatabase.execute_write(query, {
            'from_account_id': event.from_account_id,
            'to_account_id': event.to_account_id,
            'amount': event.amount,
            'currency': event.currency,
            'transfer_type': event.transfer_type,
            'timestamp': event.timestamp.isoformat(),
            'transfer_id': event.aggregate_id
        })
        logger.debug(f"Transfer: {event.from_account_id} → {event.to_account_id} (${event.amount})")

    def _handle_fraud_flag_raised(self, event: FraudFlagRaised) -> None:
        """Mark transaction as fraudulent in graph."""
        query = """
        MATCH (t:Transaction {transaction_id: $transaction_id})
        SET t.is_fraud = true,
            t.fraud_probability = $fraud_probability,
            t.flagged_reasons = $flagged_reasons
        """
        GraphDatabase.execute_write(query, {
            'transaction_id': event.transaction_id,
            'fraud_probability': event.fraud_probability,
            'flagged_reasons': event.flagged_reasons
        })
        logger.debug(f"Transaction {event.transaction_id} marked as fraud in graph")
