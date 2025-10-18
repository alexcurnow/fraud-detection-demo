"""Event processor for building read model projections."""

import logging
from abc import ABC, abstractmethod
from typing import Optional
from .event_models import BaseEvent
from .event_store import EventStore
from ..database import Database

logger = logging.getLogger(__name__)


class EventProcessor(ABC):
    """
    Base class for event processors that build read model projections.

    Event processors subscribe to events and update read models accordingly.
    They maintain a checkpoint of the last processed event for idempotency.
    """

    def __init__(self, projection_name: str):
        """
        Initialize event processor.

        Args:
            projection_name: Unique name for this projection
        """
        self.projection_name = projection_name
        self.last_event_id = self._load_checkpoint()

    def _load_checkpoint(self) -> int:
        """Load the last processed event ID from projection_state."""
        row = Database.fetch_one(
            "SELECT last_event_id FROM projection_state WHERE projection_name = ?",
            (self.projection_name,)
        )
        return row['last_event_id'] if row else 0

    def _save_checkpoint(self, event_id: int) -> None:
        """Save the last processed event ID."""
        Database.execute(
            """
            INSERT INTO projection_state (projection_name, last_event_id, last_processed_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(projection_name)
            DO UPDATE SET
                last_event_id = excluded.last_event_id,
                last_processed_at = excluded.last_processed_at
            """,
            (self.projection_name, event_id)
        )

    @abstractmethod
    def process_event(self, event: BaseEvent) -> None:
        """
        Process a single event and update the read model.

        Args:
            event: Event to process
        """
        pass

    def can_handle(self, event: BaseEvent) -> bool:
        """
        Determine if this processor can handle the given event.

        Override this method to filter events.

        Args:
            event: Event to check

        Returns:
            True if this processor should handle the event
        """
        return True

    def process_all_events(self, batch_size: int = 100) -> int:
        """
        Process all unprocessed events from the event store.

        Args:
            batch_size: Number of events to process in each batch

        Returns:
            Number of events processed
        """
        processed_count = 0

        while True:
            events = EventStore.get_all_events(
                since_event_id=self.last_event_id,
                limit=batch_size
            )

            if not events:
                break

            for event_id, event in events:
                if self.can_handle(event):
                    try:
                        self.process_event(event)
                        processed_count += 1
                    except Exception as e:
                        logger.error(
                            f"Error processing event {event_id} in {self.projection_name}: {e}"
                        )
                        raise

                # Update checkpoint after each event
                self.last_event_id = event_id
                self._save_checkpoint(event_id)

            logger.info(
                f"{self.projection_name}: Processed batch of {len(events)} events "
                f"(last_event_id={self.last_event_id})"
            )

        if processed_count > 0:
            logger.info(
                f"{self.projection_name}: Completed processing {processed_count} events"
            )

        return processed_count

    def rebuild(self) -> int:
        """
        Rebuild the projection from scratch by resetting checkpoint and reprocessing all events.

        Returns:
            Number of events processed
        """
        logger.warning(f"Rebuilding projection: {self.projection_name}")
        self.last_event_id = 0
        self._save_checkpoint(0)
        return self.process_all_events()


class EventHandler:
    """
    Event handler registry for managing multiple processors.

    Coordinates processing of events across multiple projections.
    """

    def __init__(self):
        self.processors: list[EventProcessor] = []

    def register(self, processor: EventProcessor) -> None:
        """Register an event processor."""
        self.processors.append(processor)
        logger.info(f"Registered processor: {processor.projection_name}")

    def process_new_events(self) -> dict[str, int]:
        """
        Process new events for all registered processors.

        Returns:
            Dictionary mapping processor names to number of events processed
        """
        results = {}
        for processor in self.processors:
            count = processor.process_all_events()
            results[processor.projection_name] = count
        return results

    def rebuild_all(self) -> dict[str, int]:
        """
        Rebuild all projections from scratch.

        Returns:
            Dictionary mapping processor names to number of events processed
        """
        results = {}
        for processor in self.processors:
            count = processor.rebuild()
            results[processor.projection_name] = count
        return results
