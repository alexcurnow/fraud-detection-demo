#!/usr/bin/env python3
"""Sync SQLite events to Neo4j graph database."""

import logging
from src.database import Database
from src.graph import GraphDatabase, GraphProjection
from src.events import EventHandler

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Sync all events to Neo4j."""
    logger.info("Connecting to databases...")

    # Initialize SQLite
    Database.get_connection()

    # Initialize Neo4j
    GraphDatabase.get_driver()
    GraphDatabase.create_constraints()

    logger.info("Syncing events to Neo4j graph...")

    # Create event handler with graph projection
    handler = EventHandler()
    handler.register(GraphProjection())

    # Process all new events
    handler.process_new_events()

    logger.info("✓ Sync complete!")

    # Show some stats
    with GraphDatabase.get_driver().session() as session:
        user_count = session.run("MATCH (u:User) RETURN count(u) as count").single()["count"]
        txn_count = session.run("MATCH (t:Transaction) RETURN count(t) as count").single()["count"]
        device_count = session.run("MATCH (d:Device) RETURN count(d) as count").single()["count"]
        transfer_count = session.run("MATCH ()-[t:TRANSFERS_TO]->() RETURN count(t) as count").single()["count"]

        logger.info(f"Neo4j graph contains:")
        logger.info(f"  - {user_count} Users")
        logger.info(f"  - {txn_count} Transactions")
        logger.info(f"  - {device_count} Devices")
        logger.info(f"  - {transfer_count} Transfers")


if __name__ == "__main__":
    main()
