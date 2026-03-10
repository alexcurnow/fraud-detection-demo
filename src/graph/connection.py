"""Neo4j database connection management."""

import os
import logging
from typing import Optional, Any, List, Dict
from neo4j import GraphDatabase as Neo4jDriver, Driver, Result

logger = logging.getLogger(__name__)


class GraphDatabase:
    """
    Singleton Neo4j connection manager.

    Manages connection to Neo4j graph database for fraud network analysis.
    """

    _driver: Optional[Driver] = None

    @classmethod
    def get_driver(cls) -> Driver:
        """Get or create Neo4j driver instance."""
        if cls._driver is None:
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = os.getenv("NEO4J_USER", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "frauddetection123")

            logger.info(f"Connecting to Neo4j at {uri}...")
            cls._driver = Neo4jDriver.driver(uri, auth=(user, password))

            # Verify connectivity
            try:
                cls._driver.verify_connectivity()
                logger.info("✓ Neo4j connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise

        return cls._driver

    @classmethod
    def close(cls):
        """Close Neo4j driver connection."""
        if cls._driver:
            cls._driver.close()
            cls._driver = None
            logger.info("Neo4j connection closed")

    @classmethod
    def execute_query(cls, query: str, parameters: Optional[Dict[str, Any]] = None) -> Result:
        """
        Execute a Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters dictionary

        Returns:
            Query result
        """
        driver = cls.get_driver()
        with driver.session() as session:
            result = session.run(query, parameters or {})
            return result.data()

    @classmethod
    def execute_write(cls, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a write transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters dictionary

        Returns:
            Transaction result
        """
        driver = cls.get_driver()

        def _write_transaction(tx):
            return tx.run(query, parameters or {}).data()

        with driver.session() as session:
            return session.execute_write(_write_transaction)

    @classmethod
    def clear_database(cls):
        """Clear all nodes and relationships (use with caution!)."""
        logger.warning("Clearing Neo4j database...")
        cls.execute_write("MATCH (n) DETACH DELETE n")
        logger.info("✓ Neo4j database cleared")

    @classmethod
    def create_constraints(cls):
        """
        Create uniqueness constraints and indexes for performance.

        Constraints ensure data integrity and create indexes automatically.
        """
        logger.info("Creating Neo4j constraints and indexes...")

        constraints = [
            "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.account_id IS UNIQUE",
            "CREATE CONSTRAINT transaction_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.transaction_id IS UNIQUE",
            "CREATE CONSTRAINT device_id IF NOT EXISTS FOR (d:Device) REQUIRE d.device_id IS UNIQUE",
            "CREATE CONSTRAINT merchant_id IF NOT EXISTS FOR (m:Merchant) REQUIRE m.merchant_id IS UNIQUE",
            "CREATE CONSTRAINT location_id IF NOT EXISTS FOR (l:Location) REQUIRE l.location_id IS UNIQUE",
        ]

        for constraint in constraints:
            try:
                cls.execute_write(constraint)
                logger.debug(f"Created constraint: {constraint[:50]}...")
            except Exception as e:
                # Constraint might already exist
                if "EquivalentSchemaRuleAlreadyExists" not in str(e):
                    logger.warning(f"Constraint creation warning: {e}")

        logger.info("✓ Constraints and indexes created")
