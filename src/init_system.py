"""System initialization - sets up database and event processors."""

import logging
from .database import Database
from .events import EventHandler
from .projections import (
    AccountProjection,
    TransactionProjection,
    DeviceProjection,
    LocationProjection
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def initialize_system(force_rebuild: bool = False) -> EventHandler:
    """
    Initialize the fraud detection system.

    Args:
        force_rebuild: If True, drops existing database and rebuilds from scratch

    Returns:
        EventHandler with all projections registered
    """
    logger.info("Initializing fraud detection system...")

    # Initialize database schema
    Database.initialize_schema(force=force_rebuild)

    # Create event handler and register projections
    event_handler = EventHandler()

    # Register all projections
    event_handler.register(AccountProjection())
    event_handler.register(TransactionProjection())
    event_handler.register(DeviceProjection())
    event_handler.register(LocationProjection())

    logger.info(f"Registered {len(event_handler.processors)} event processors")

    # Process any existing events (in case of restart)
    if not force_rebuild:
        logger.info("Processing any unprocessed events...")
        results = event_handler.process_new_events()
        total = sum(results.values())
        if total > 0:
            logger.info(f"Processed {total} events across all projections")

    logger.info("System initialization complete!")
    return event_handler


def rebuild_projections() -> None:
    """Rebuild all projections from scratch."""
    logger.warning("Rebuilding all projections from event store...")

    event_handler = EventHandler()
    event_handler.register(AccountProjection())
    event_handler.register(TransactionProjection())
    event_handler.register(DeviceProjection())
    event_handler.register(LocationProjection())

    results = event_handler.rebuild_all()

    for projection_name, count in results.items():
        logger.info(f"{projection_name}: Processed {count} events")

    logger.info("Projection rebuild complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--rebuild":
        rebuild_projections()
    else:
        initialize_system(force_rebuild="--force" in sys.argv)
