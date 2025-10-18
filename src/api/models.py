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
