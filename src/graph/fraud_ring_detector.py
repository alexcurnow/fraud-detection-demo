"""Fraud ring detection using Neo4j graph queries."""

import logging
from typing import List, Dict, Any
from .connection import GraphDatabase

logger = logging.getLogger(__name__)


class FraudRingDetector:
    """
    Detects organized fraud patterns using graph analysis.

    Fraud Ring Types:
    1. Device Sharing Ring - Multiple accounts using same device
    2. Money Mule Network - Chain of rapid transfers
    3. Account Takeover Ring - Coordinated device/location changes
    4. Merchant Collusion - Multiple users with suspicious merchant patterns
    5. Synthetic Identity Ring - Accounts created together with similar attributes
    """

    @staticmethod
    def detect_device_sharing_rings(min_accounts: int = 3) -> List[Dict[str, Any]]:
        """
        Detect device sharing rings.

        Finds devices shared by multiple accounts with rapid transaction succession.

        Args:
            min_accounts: Minimum number of accounts sharing device

        Returns:
            List of detected rings with device_id, accounts, and confidence
        """
        query = """
        MATCH (u:User)-[:OWNS]->(d:Device)<-[:OWNS]-(other:User)
        WHERE u.account_id < other.account_id  // Avoid duplicates
        WITH d, COLLECT(DISTINCT u.account_id) + COLLECT(DISTINCT other.account_id) as accounts
        WHERE SIZE(accounts) >= $min_accounts

        // Get transactions from these accounts
        MATCH (sharer:User)-[:MAKES]->(t:Transaction)
        WHERE sharer.account_id IN accounts
        WITH d, accounts, COLLECT(t) as transactions
        ORDER BY SIZE(accounts) DESC

        RETURN d.device_id as device_id,
               accounts,
               SIZE(accounts) as account_count,
               SIZE(transactions) as transaction_count,
               'device_sharing' as ring_type
        LIMIT 10
        """

        results = GraphDatabase.execute_query(query, {'min_accounts': min_accounts})
        logger.info(f"Found {len(results)} device sharing rings")
        return results

    @staticmethod
    def detect_money_mule_chains(min_hops: int = 3, time_window_hours: int = 24) -> List[Dict[str, Any]]:
        """
        Detect money mule chains (sequential transfers).

        Finds chains of transfers: A → B → C → D within time window.

        Args:
            min_hops: Minimum number of transfer hops
            time_window_hours: Maximum hours for entire chain

        Returns:
            List of detected chains
        """
        query = """
        MATCH path = (start:User)-[:TRANSFERS_TO*%d..5]->(end:User)
        WHERE start <> end

        // Get all transfer relationships in path
        WITH path, relationships(path) as transfers
        WHERE ALL(t IN transfers WHERE t.timestamp IS NOT NULL)

        // Calculate time span
        WITH path, transfers,
             [t IN transfers | datetime(t.timestamp)] as timestamps
        WITH path, transfers,
             timestamps[0] as first_transfer,
             timestamps[SIZE(timestamps)-1] as last_transfer
        WHERE duration.between(first_transfer, last_transfer).hours <= $time_window_hours

        // Calculate total amount
        WITH path, transfers, first_transfer, last_transfer,
             [t IN transfers | t.amount] as amounts
        WITH path, transfers, first_transfer, last_transfer,
             REDUCE(total = 0.0, amt IN amounts | total + amt) as total_amount

        RETURN [n IN nodes(path) | n.account_id] as chain,
               LENGTH(path) as hops,
               total_amount,
               first_transfer,
               last_transfer,
               'money_mule' as ring_type
        ORDER BY hops DESC, total_amount DESC
        LIMIT 10
        """ % min_hops

        results = GraphDatabase.execute_query(query, {'time_window_hours': time_window_hours})
        logger.info(f"Found {len(results)} money mule chains")
        return results

    @staticmethod
    def detect_merchant_collusion(min_users: int = 5, min_amount: float = 9000) -> List[Dict[str, Any]]:
        """
        Detect merchant collusion patterns.

        Finds merchants with multiple high-value transactions from different users.

        Args:
            min_users: Minimum distinct users
            min_amount: Minimum transaction amount

        Returns:
            List of suspicious merchant patterns
        """
        query = """
        MATCH (u:User)-[:MAKES]->(t:Transaction)-[:AT]->(m:Merchant)
        WHERE t.amount >= $min_amount

        WITH m, COLLECT(DISTINCT u.account_id) as users, COLLECT(t) as transactions
        WHERE SIZE(users) >= $min_users

        RETURN m.merchant_id as merchant_id,
               m.name as merchant_name,
               m.category as merchant_category,
               users,
               SIZE(users) as user_count,
               SIZE(transactions) as transaction_count,
               REDUCE(total = 0.0, t IN transactions | total + t.amount) as total_amount,
               'merchant_collusion' as ring_type
        ORDER BY user_count DESC
        LIMIT 10
        """

        results = GraphDatabase.execute_query(query, {
            'min_users': min_users,
            'min_amount': min_amount
        })
        logger.info(f"Found {len(results)} merchant collusion patterns")
        return results

    @staticmethod
    def detect_account_takeover_rings(time_window_hours: int = 2) -> List[Dict[str, Any]]:
        """
        Detect coordinated account takeover.

        Finds multiple accounts changing devices around the same time.

        Args:
            time_window_hours: Time window for coordinated changes

        Returns:
            List of suspicious device change clusters
        """
        query = """
        // Find accounts that changed devices
        MATCH (u:User)-[r:OWNS]->(d:Device)
        WHERE r.first_seen IS NOT NULL

        // Group by device change time window
        WITH u, d, r.first_seen as change_time
        WITH datetime(change_time) as device_change_dt,
             COLLECT({account: u.account_id, device: d.device_id}) as changes

        // Find clusters of device changes within time window
        WITH device_change_dt, changes
        WHERE SIZE(changes) >= 2

        // Find overlapping time windows
        WITH changes, device_change_dt
        UNWIND changes as change
        WITH change.account as account, change.device as device, device_change_dt
        ORDER BY device_change_dt

        // Group accounts with device changes within N hours
        WITH COLLECT({account: account, device: device, timestamp: device_change_dt}) as all_changes
        UNWIND RANGE(0, SIZE(all_changes)-1) as idx
        WITH all_changes[idx] as change, all_changes

        // Find other changes within time window
        WITH change, [other IN all_changes
                      WHERE duration.between(
                          datetime(other.timestamp),
                          datetime(change.timestamp)
                      ).hours <= $time_window_hours
                      AND other.account <> change.account] as nearby_changes

        WHERE SIZE(nearby_changes) >= 1

        WITH change, nearby_changes
        RETURN [change.account] + [n IN nearby_changes | n.account] as accounts,
               SIZE(nearby_changes) + 1 as account_count,
               change.timestamp as timestamp,
               'account_takeover' as ring_type
        ORDER BY account_count DESC
        LIMIT 10
        """

        results = GraphDatabase.execute_query(query, {'time_window_hours': time_window_hours})
        logger.info(f"Found {len(results)} account takeover clusters")
        return results

    @staticmethod
    def detect_synthetic_identity_rings(age_window_days: int = 7) -> List[Dict[str, Any]]:
        """
        Detect synthetic identity rings.

        Finds accounts created within same time period with similar patterns.

        Args:
            age_window_days: Days for account creation window

        Returns:
            List of suspicious account clusters
        """
        query = """
        // Find accounts created around same time
        MATCH (u:User)
        WHERE u.created_at IS NOT NULL

        WITH u, datetime(u.created_at) as created_dt
        WITH u, created_dt
        ORDER BY created_dt

        // Group by creation week
        WITH u, created_dt,
             created_dt.year * 100 + created_dt.week as creation_week

        WITH creation_week, COLLECT(u) as users
        WHERE SIZE(users) >= 3

        // Check if they share devices or locations
        WITH creation_week, users
        UNWIND users as u
        OPTIONAL MATCH (u)-[:OWNS]->(d:Device)<-[:OWNS]-(other:User)
        WHERE other IN users AND u.account_id <> other.account_id

        WITH creation_week, users, COUNT(DISTINCT d) as shared_devices
        WHERE shared_devices > 0

        RETURN [u IN users | u.account_id] as accounts,
               SIZE(users) as account_count,
               shared_devices,
               creation_week,
               'synthetic_identity' as ring_type
        ORDER BY account_count DESC
        LIMIT 10
        """

        results = GraphDatabase.execute_query(query, {'age_window_days': age_window_days})
        logger.info(f"Found {len(results)} synthetic identity rings")
        return results

    @staticmethod
    def detect_all_rings() -> Dict[str, List[Dict[str, Any]]]:
        """
        Run all fraud ring detection algorithms.

        Returns:
            Dictionary mapping ring type to detected patterns
        """
        logger.info("Running all fraud ring detection algorithms...")

        results = {
            'device_sharing': FraudRingDetector.detect_device_sharing_rings(),
            'money_mule': FraudRingDetector.detect_money_mule_chains(),
            'merchant_collusion': FraudRingDetector.detect_merchant_collusion(),
            'account_takeover': FraudRingDetector.detect_account_takeover_rings(),
            'synthetic_identity': FraudRingDetector.detect_synthetic_identity_rings()
        }

        total_rings = sum(len(rings) for rings in results.values())
        logger.info(f"Total fraud rings detected: {total_rings}")

        return results

    @staticmethod
    def get_user_network(account_id: str, depth: int = 2) -> Dict[str, Any]:
        """
        Get network graph for a specific user.

        Returns nodes and edges for visualization.

        Args:
            account_id: User account ID
            depth: How many relationship hops to traverse

        Returns:
            Graph data with nodes and edges
        """
        query = """
        MATCH path = (u:User {account_id: $account_id})-[*1..%d]-(connected)
        WITH u, COLLECT(DISTINCT connected) as connected_nodes, COLLECT(path) as paths

        // Extract all nodes and relationships
        WITH u, connected_nodes,
             REDUCE(nodes = [u], path IN paths |
                nodes + [n IN nodes(path) WHERE NOT n IN nodes]) as all_nodes,
             REDUCE(rels = [], path IN paths |
                rels + relationships(path)) as all_relationships

        RETURN [n IN all_nodes | {
                   id: COALESCE(n.account_id, n.device_id, n.merchant_id, n.location_id),
                   label: HEAD(labels(n)),
                   properties: properties(n)
               }] as nodes,
               [r IN all_relationships | {
                   source: COALESCE(startNode(r).account_id,
                                    startNode(r).device_id,
                                    startNode(r).merchant_id),
                   target: COALESCE(endNode(r).account_id,
                                    endNode(r).device_id,
                                    endNode(r).merchant_id),
                   type: type(r),
                   properties: properties(r)
               }] as edges
        """ % depth

        result = GraphDatabase.execute_query(query, {'account_id': account_id})

        if result:
            return result[0]
        return {'nodes': [], 'edges': []}
