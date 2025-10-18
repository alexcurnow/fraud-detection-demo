"""Event Store implementation - append-only event log."""

import json
import logging
from datetime import datetime
from typing import Optional, List
from .event_models import BaseEvent, deserialize_event, EventMetadata
from ..database import Database

logger = logging.getLogger(__name__)


class EventStore:
    """
    Event Store - Append-only log of all domain events.

    Core principles:
    - Events are immutable (never UPDATE or DELETE)
    - Events are the source of truth
    - Current state is derived by replaying events
    """

    @staticmethod
    def append(event: BaseEvent) -> int:
        """
        Append an event to the store.

        Args:
            event: Event to append

        Returns:
            event_id: Auto-generated event ID

        Raises:
            Exception: If append fails (e.g., version conflict)
        """
        # Serialize event data (exclude metadata and base fields)
        event_dict = event.model_dump(
            mode='json',
            exclude={'metadata', 'event_type', 'aggregate_id', 'aggregate_type', 'timestamp', 'version'}
        )
        event_data = json.dumps(event_dict)

        # Serialize metadata
        metadata_json = json.dumps(event.metadata.model_dump(mode='json'))

        query = """
            INSERT INTO events (
                event_type, aggregate_id, aggregate_type,
                event_data, metadata, timestamp, version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            event.event_type,
            event.aggregate_id,
            event.aggregate_type,
            event_data,
            metadata_json,
            event.timestamp.isoformat(),
            event.version
        )

        try:
            cursor = Database.execute(query, params)
            event_id = cursor.lastrowid
            logger.info(
                f"Event appended: {event.event_type} "
                f"[aggregate={event.aggregate_type}:{event.aggregate_id}, id={event_id}]"
            )
            return event_id
        except Exception as e:
            logger.error(f"Failed to append event: {e}")
            raise

    @staticmethod
    def get_events_by_aggregate(
        aggregate_type: str,
        aggregate_id: str,
        from_version: int = 0
    ) -> List[BaseEvent]:
        """
        Get all events for a specific aggregate.

        Args:
            aggregate_type: Type of aggregate (e.g., "Transaction")
            aggregate_id: ID of the aggregate
            from_version: Only return events after this version

        Returns:
            List of events in chronological order
        """
        query = """
            SELECT event_type, aggregate_id, aggregate_type,
                   event_data, metadata, timestamp, version, id
            FROM events
            WHERE aggregate_type = ? AND aggregate_id = ? AND version > ?
            ORDER BY version ASC, id ASC
        """

        rows = Database.fetch_all(query, (aggregate_type, aggregate_id, from_version))

        events = []
        for row in rows:
            event_data = json.loads(row['event_data'])
            metadata_data = json.loads(row['metadata'])

            # Reconstruct event
            event_data.update({
                'event_type': row['event_type'],
                'aggregate_id': row['aggregate_id'],
                'aggregate_type': row['aggregate_type'],
                'timestamp': datetime.fromisoformat(row['timestamp']),
                'version': row['version'],
                'metadata': EventMetadata(**metadata_data)
            })

            event = deserialize_event(row['event_type'], event_data)
            events.append(event)

        return events

    @staticmethod
    def get_events_by_type(
        event_type: str,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[BaseEvent]:
        """
        Get all events of a specific type.

        Args:
            event_type: Type of event to retrieve
            since: Only return events after this timestamp
            limit: Maximum number of events to return

        Returns:
            List of events in chronological order
        """
        query = """
            SELECT event_type, aggregate_id, aggregate_type,
                   event_data, metadata, timestamp, version, id
            FROM events
            WHERE event_type = ?
        """
        params = [event_type]

        if since:
            query += " AND timestamp > ?"
            params.append(since.isoformat())

        query += " ORDER BY timestamp ASC, id ASC"

        if limit:
            query += f" LIMIT {limit}"

        rows = Database.fetch_all(query, tuple(params))

        events = []
        for row in rows:
            event_data = json.loads(row['event_data'])
            metadata_data = json.loads(row['metadata'])

            event_data.update({
                'event_type': row['event_type'],
                'aggregate_id': row['aggregate_id'],
                'aggregate_type': row['aggregate_type'],
                'timestamp': datetime.fromisoformat(row['timestamp']),
                'version': row['version'],
                'metadata': EventMetadata(**metadata_data)
            })

            event = deserialize_event(row['event_type'], event_data)
            events.append(event)

        return events

    @staticmethod
    def get_all_events(
        since_event_id: int = 0,
        limit: Optional[int] = None
    ) -> List[tuple[int, BaseEvent]]:
        """
        Get all events from the store.

        Args:
            since_event_id: Only return events after this event ID
            limit: Maximum number of events to return

        Returns:
            List of (event_id, event) tuples in chronological order
        """
        query = """
            SELECT id, event_type, aggregate_id, aggregate_type,
                   event_data, metadata, timestamp, version
            FROM events
            WHERE id > ?
            ORDER BY id ASC
        """

        if limit:
            query += f" LIMIT {limit}"

        rows = Database.fetch_all(query, (since_event_id,))

        events = []
        for row in rows:
            event_data = json.loads(row['event_data'])
            metadata_data = json.loads(row['metadata'])

            event_data.update({
                'event_type': row['event_type'],
                'aggregate_id': row['aggregate_id'],
                'aggregate_type': row['aggregate_type'],
                'timestamp': datetime.fromisoformat(row['timestamp']),
                'version': row['version'],
                'metadata': EventMetadata(**metadata_data)
            })

            event = deserialize_event(row['event_type'], event_data)
            events.append((row['id'], event))

        return events

    @staticmethod
    def get_event_count() -> int:
        """Get total number of events in the store."""
        row = Database.fetch_one("SELECT COUNT(*) as count FROM events")
        return row['count'] if row else 0

    @staticmethod
    def get_latest_event_id() -> int:
        """Get the ID of the most recent event."""
        row = Database.fetch_one("SELECT MAX(id) as max_id FROM events")
        return row['max_id'] if row and row['max_id'] else 0
