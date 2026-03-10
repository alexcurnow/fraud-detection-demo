"""API request/response models using Pydantic."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class UserPattern(BaseModel):
    """User's typical transaction patterns."""
    account_id: str
    email: str
    total_transactions: int
    total_volume: float
    avg_transaction_amount: float
    common_merchants: List[str]
    typical_hours: List[int] = Field(description="Hours of day user typically transacts (0-23)")
    home_location: dict = Field(description="Typical geographic location")
    fraud_flags: int


class UserResponse(BaseModel):
    """Response for GET /users/{user_id}"""
    account_id: str
    email: str
    created_at: datetime
    status: str
    patterns: UserPattern
    recent_transactions: List[dict]


class UserListResponse(BaseModel):
    """Response for GET /users"""
    total: int
    users: List[UserPattern]


class CreateTransactionRequest(BaseModel):
    """Request body for POST /users/{user_id}/transactions"""
    amount: float = Field(gt=0, description="Transaction amount in USD")
    merchant_name: str = Field(min_length=1)
    merchant_category: str = Field(description="e.g., grocery, electronics, restaurant")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    timestamp: Optional[datetime] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None


class FraudAnalysis(BaseModel):
    """Fraud detection analysis results."""
    risk_score: float = Field(ge=0, le=1, description="Fraud probability (0-1)")
    is_flagged: bool
    flagged_reasons: List[str]
    model_version: str
    features_analyzed: dict = Field(description="Features used in fraud detection")


class TransactionResponse(BaseModel):
    """Response for POST /users/{user_id}/transactions"""
    transaction_id: str
    account_id: str
    amount: float
    merchant_name: str
    merchant_category: str
    timestamp: datetime
    status: str
    fraud_analysis: FraudAnalysis


class FlaggedTransactionResponse(BaseModel):
    """Single flagged transaction with details."""
    transaction_id: str
    account_id: str
    user_email: str
    amount: float
    merchant_category: str
    merchant_name: str
    initiated_at: datetime
    risk_score: float
    flagged_reasons: List[str]


class FlaggedTransactionsListResponse(BaseModel):
    """Response for GET /transactions/flagged"""
    total: int
    transactions: List[FlaggedTransactionResponse]


# ============================================================================
# NETWORK ANALYSIS MODELS (Phase 2)
# ============================================================================

class FraudRingResponse(BaseModel):
    """A detected fraud ring pattern."""
    ring_type: str = Field(description="Type: device_sharing, money_mule, merchant_collusion, etc.")
    confidence: str = Field(default="high", description="Confidence level: low, medium, high")
    accounts: List[str] = Field(description="Account IDs involved in ring")
    account_count: int
    metadata: dict = Field(description="Ring-specific details")


class FraudRingsResponse(BaseModel):
    """Response for GET /network/rings"""
    total_rings: int
    rings_by_type: dict = Field(description="Rings grouped by type")
    all_rings: List[FraudRingResponse]


class NetworkNode(BaseModel):
    """Graph node for visualization."""
    id: str
    label: str = Field(description="Node type: User, Device, Merchant, Transaction, Location")
    properties: dict


class NetworkEdge(BaseModel):
    """Graph edge/relationship for visualization."""
    source: str
    target: str
    type: str = Field(description="Relationship type: OWNS, MAKES, TRANSFERS_TO, etc.")
    properties: dict = Field(default_factory=dict)


class NetworkGraphResponse(BaseModel):
    """Response for GET /network/visualize/{user_id}"""
    account_id: str
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]
    node_count: int
    edge_count: int


# ============================================================================
# LLM EXPLANATION MODELS (Phase 2)
# ============================================================================

class ExplanationResponse(BaseModel):
    """LLM-generated explanation."""
    explanation: str = Field(description="Natural language explanation")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    model: str = Field(default="llama3.2")


class ExecutiveSummaryResponse(BaseModel):
    """Executive summary of fraud activity."""
    summary: str
    total_flagged_transactions: int
    total_fraud_rings: int
    total_risk_exposure: float
    priority_actions: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
