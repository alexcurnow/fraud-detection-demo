"""Update fraud_scores table by reprocessing FraudFlagRaised events."""

import logging
from src.database import Database
from src.events import EventStore, EventHandler
from src.projections import TransactionProjection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
Database.get_connection()

# Get all FraudFlagRaised events
all_events = EventStore.get_all_events()
fraud_events = [(event_id, event) for event_id, event in all_events if event.event_type == 'FraudFlagRaised']

logger.info(f"Found {len(fraud_events)} FraudFlagRaised events to reprocess")

# Create transaction projection
projection = TransactionProjection()

# Reprocess all fraud events
for event_id, event in fraud_events:
    projection.process_event(event)

logger.info("Fraud scores updated successfully!")
