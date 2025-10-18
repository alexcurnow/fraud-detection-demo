"""Device projection - builds devices read model from events."""

import logging
from ..events.event_processor import EventProcessor
from ..events.event_models import BaseEvent, DeviceChanged, FraudFlagRaised
from ..database import Database

logger = logging.getLogger(__name__)


class DeviceProjection(EventProcessor):
    """
    Builds and maintains the devices read model.

    Processes:
    - DeviceChanged: Creates or updates device record
    - FraudFlagRaised: Increments fraud incident counter for device
    """

    def __init__(self):
        super().__init__(projection_name="DeviceProjection")

    def process_event(self, event: BaseEvent) -> None:
        """Process an event and update the devices read model."""

        if isinstance(event, DeviceChanged):
            self._handle_device_changed(event)

        elif isinstance(event, FraudFlagRaised):
            self._handle_fraud_flag_raised(event)

    def can_handle(self, event: BaseEvent) -> bool:
        """Only handle events relevant to devices."""
        return isinstance(event, (DeviceChanged, FraudFlagRaised))

    def _handle_device_changed(self, event: DeviceChanged) -> None:
        """Create or update device record."""
        # Check if device exists
        existing = Database.fetch_one(
            "SELECT device_id FROM devices WHERE device_id = ?",
            (event.new_device_id,)
        )

        if existing:
            # Update last seen
            Database.execute(
                """
                UPDATE devices
                SET last_seen = ?
                WHERE device_id = ?
                """,
                (event.timestamp.isoformat(), event.new_device_id)
            )
        else:
            # Create new device record
            Database.execute(
                """
                INSERT INTO devices (
                    device_id, account_id, first_seen, last_seen,
                    device_type, browser, os, is_trusted, fraud_incidents
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)
                """,
                (
                    event.new_device_id,
                    event.account_id,
                    event.timestamp.isoformat(),
                    event.timestamp.isoformat(),
                    event.device_type,
                    event.browser,
                    event.os
                )
            )
            logger.debug(f"New device registered: {event.new_device_id} for account {event.account_id}")

    def _handle_fraud_flag_raised(self, event: FraudFlagRaised) -> None:
        """Increment fraud incident counter for device if metadata contains device_id."""
        # We need to get device_id from the transaction
        row = Database.fetch_one(
            "SELECT device_id FROM transactions WHERE transaction_id = ?",
            (event.transaction_id,)
        )

        if row and row['device_id']:
            Database.execute(
                """
                UPDATE devices
                SET fraud_incidents = fraud_incidents + 1
                WHERE device_id = ?
                """,
                (row['device_id'],)
            )
