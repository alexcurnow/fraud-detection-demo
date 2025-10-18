"""Location projection - builds location_events read model from events."""

import logging
from ..events.event_processor import EventProcessor
from ..events.event_models import (
    BaseEvent,
    TransactionInitiated,
    LoginAttempted,
    LocationChanged
)
from ..database import Database

logger = logging.getLogger(__name__)


class LocationProjection(EventProcessor):
    """
    Builds and maintains the location_events read model.

    Processes:
    - TransactionInitiated: Records location if metadata contains lat/lon
    - LoginAttempted: Records location if metadata contains lat/lon
    - LocationChanged: Explicitly records location change
    """

    def __init__(self):
        super().__init__(projection_name="LocationProjection")

    def process_event(self, event: BaseEvent) -> None:
        """Process an event and update the location_events read model."""

        if isinstance(event, TransactionInitiated):
            self._handle_transaction_initiated(event)

        elif isinstance(event, LoginAttempted):
            self._handle_login_attempted(event)

        elif isinstance(event, LocationChanged):
            self._handle_location_changed(event)

    def can_handle(self, event: BaseEvent) -> bool:
        """Only handle events relevant to location tracking."""
        return isinstance(event, (
            TransactionInitiated,
            LoginAttempted,
            LocationChanged
        ))

    def _handle_transaction_initiated(self, event: TransactionInitiated) -> None:
        """Record transaction location if available."""
        if event.metadata.latitude is not None and event.metadata.longitude is not None:
            Database.execute(
                """
                INSERT INTO location_events (
                    account_id, latitude, longitude,
                    event_type, event_id, timestamp
                )
                VALUES (?, ?, ?, 'transaction', ?, ?)
                """,
                (
                    event.account_id,
                    event.metadata.latitude,
                    event.metadata.longitude,
                    event.aggregate_id,
                    event.timestamp.isoformat()
                )
            )

    def _handle_login_attempted(self, event: LoginAttempted) -> None:
        """Record login location if available."""
        if event.metadata.latitude is not None and event.metadata.longitude is not None:
            # Insert into location_events
            Database.execute(
                """
                INSERT INTO location_events (
                    account_id, latitude, longitude,
                    event_type, event_id, timestamp
                )
                VALUES (?, ?, ?, 'login', ?, ?)
                """,
                (
                    event.account_id,
                    event.metadata.latitude,
                    event.metadata.longitude,
                    event.aggregate_id,  # session/login ID
                    event.timestamp.isoformat()
                )
            )

            # Also insert into login_attempts table
            Database.execute(
                """
                INSERT INTO login_attempts (
                    account_id, attempted_at, success,
                    ip_address, device_id, latitude, longitude
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.account_id,
                    event.timestamp.isoformat(),
                    event.success,
                    event.metadata.ip_address,
                    event.metadata.device_id,
                    event.metadata.latitude,
                    event.metadata.longitude
                )
            )

    def _handle_location_changed(self, event: LocationChanged) -> None:
        """Explicitly record location change."""
        Database.execute(
            """
            INSERT INTO location_events (
                account_id, latitude, longitude,
                event_type, event_id, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event.account_id,
                event.new_latitude,
                event.new_longitude,
                event.context,
                event.context_id,
                event.timestamp.isoformat()
            )
        )
