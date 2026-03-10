"""Network analysis API endpoints - Phase 2."""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from .models import (
    FraudRingResponse,
    FraudRingsResponse,
    NetworkGraphResponse,
    NetworkNode,
    NetworkEdge
)
from ..graph import FraudRingDetector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/network", tags=["network-analysis"])


@router.get("/rings", response_model=FraudRingsResponse)
async def detect_fraud_rings():
    """
    Detect all fraud ring patterns using graph analysis.

    Returns detected rings grouped by type:
    - device_sharing: Multiple accounts using same device
    - money_mule: Chain of rapid transfers
    - merchant_collusion: Suspicious merchant patterns
    - account_takeover: Coordinated device/location changes
    - synthetic_identity: Accounts created together with similar attributes
    """
    try:
        # Run all detection algorithms
        rings_by_type = FraudRingDetector.detect_all_rings()

        # Convert to response format
        all_rings = []
        for ring_type, rings in rings_by_type.items():
            for ring_data in rings:
                # Extract accounts list based on ring type
                if ring_type == "device_sharing":
                    accounts = ring_data.get("accounts", [])
                    metadata = {
                        "device_id": ring_data.get("device_id"),
                        "transaction_count": ring_data.get("transaction_count", 0)
                    }
                elif ring_type == "money_mule":
                    accounts = ring_data.get("chain", [])
                    metadata = {
                        "hops": ring_data.get("hops", 0),
                        "total_amount": ring_data.get("total_amount", 0.0),
                        "first_transfer": str(ring_data.get("first_transfer", "")),
                        "last_transfer": str(ring_data.get("last_transfer", ""))
                    }
                elif ring_type == "merchant_collusion":
                    accounts = ring_data.get("users", [])
                    metadata = {
                        "merchant_name": ring_data.get("merchant_name"),
                        "merchant_category": ring_data.get("merchant_category"),
                        "transaction_count": ring_data.get("transaction_count", 0),
                        "total_amount": ring_data.get("total_amount", 0.0)
                    }
                elif ring_type == "account_takeover":
                    accounts = ring_data.get("accounts", [])
                    metadata = {
                        "timestamp": str(ring_data.get("timestamp", ""))
                    }
                elif ring_type == "synthetic_identity":
                    accounts = ring_data.get("accounts", [])
                    metadata = {
                        "shared_devices": ring_data.get("shared_devices", 0),
                        "creation_week": ring_data.get("creation_week", 0)
                    }
                else:
                    accounts = []
                    metadata = ring_data

                all_rings.append(FraudRingResponse(
                    ring_type=ring_type,
                    confidence="high",
                    accounts=accounts,
                    account_count=len(accounts),
                    metadata=metadata
                ))

        return FraudRingsResponse(
            total_rings=len(all_rings),
            rings_by_type={k: len(v) for k, v in rings_by_type.items()},
            all_rings=all_rings
        )

    except Exception as e:
        logger.error(f"Error detecting fraud rings: {e}")
        raise HTTPException(status_code=500, detail=f"Fraud ring detection failed: {str(e)}")


@router.get("/suspicious", response_model=Dict[str, Any])
async def get_suspicious_patterns():
    """
    Find specific suspicious network patterns.

    Quick overview of high-priority patterns for monitoring dashboard.
    """
    try:
        # Get high-priority patterns
        device_sharing = FraudRingDetector.detect_device_sharing_rings(min_accounts=3)
        money_mules = FraudRingDetector.detect_money_mule_chains(min_hops=3)

        return {
            "critical_device_sharing": len([r for r in device_sharing if r.get("account_count", 0) >= 5]),
            "active_money_mule_chains": len(money_mules),
            "device_sharing_rings": device_sharing[:5],  # Top 5
            "money_mule_chains": money_mules[:5]
        }

    except Exception as e:
        logger.error(f"Error getting suspicious patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}", response_model=Dict[str, Any])
async def get_user_network(user_id: str):
    """
    Get a user's transaction network.

    Returns connected users, shared devices, common merchants, and relationships.
    Useful for investigating a specific user's fraud connections.
    """
    try:
        graph_data = FraudRingDetector.get_user_network(user_id, depth=2)

        if not graph_data or not graph_data.get("nodes"):
            raise HTTPException(status_code=404, detail=f"No network data found for user {user_id}")

        return {
            "account_id": user_id,
            "network": graph_data,
            "summary": {
                "connected_users": len([n for n in graph_data.get("nodes", []) if n.get("label") == "User"]),
                "devices": len([n for n in graph_data.get("nodes", []) if n.get("label") == "Device"]),
                "merchants": len([n for n in graph_data.get("nodes", []) if n.get("label") == "Merchant"]),
                "transactions": len([n for n in graph_data.get("nodes", []) if n.get("label") == "Transaction"])
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user network for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/visualize/{user_id}", response_model=NetworkGraphResponse)
async def visualize_user_network(user_id: str):
    """
    Get user network in format suitable for graph visualization.

    Returns nodes and edges for rendering in frontend graph libraries (D3.js, Cytoscape, etc.)
    """
    try:
        graph_data = FraudRingDetector.get_user_network(user_id, depth=2)

        if not graph_data or not graph_data.get("nodes"):
            raise HTTPException(status_code=404, detail=f"No network data found for user {user_id}")

        # Convert to response format
        nodes = [
            NetworkNode(
                id=node["id"],
                label=node["label"],
                properties=node["properties"]
            )
            for node in graph_data.get("nodes", [])
        ]

        edges = [
            NetworkEdge(
                source=edge["source"],
                target=edge["target"],
                type=edge["type"],
                properties=edge.get("properties", {})
            )
            for edge in graph_data.get("edges", [])
        ]

        return NetworkGraphResponse(
            account_id=user_id,
            nodes=nodes,
            edges=edges,
            node_count=len(nodes),
            edge_count=len(edges)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error visualizing network for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
