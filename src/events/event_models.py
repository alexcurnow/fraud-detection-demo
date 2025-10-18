"""Event models for the event store."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid


class EventMetadata(BaseModel):
    """Metadata attached to every event."""
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    user_agent: Optional[str] = None


class BaseEvent(BaseModel):
    """Base class for all events."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    aggregate_id: str
    aggregate_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    metadata: EventMetadata = Field(default_factory=EventMetadata)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# ACCOUNT EVENTS
# ============================================================================

class AccountCreated(BaseEvent):
    """Account was created."""
    event_type: str = "AccountCreated"
    aggregate_type: str = "Account"
    email: str
    initial_status: str = "active"


# ============================================================================
# TRANSACTION EVENTS
# ============================================================================

class TransactionInitiated(BaseEvent):
    """Transaction was initiated."""
    event_type: str = "TransactionInitiated"
    aggregate_type: str = "Transaction"
    account_id: str
    amount: float
    currency: str = "USD"
    merchant_category: Optional[str] = None
    merchant_name: Optional[str] = None


class TransactionCompleted(BaseEvent):
    """Transaction completed successfully."""
    event_type: str = "TransactionCompleted"
    aggregate_type: str = "Transaction"
    account_id: str
    amount: float
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class TransactionFailed(BaseEvent):
    """Transaction failed."""
    event_type: str = "TransactionFailed"
    aggregate_type: str = "Transaction"
    account_id: str
    reason: str
    failed_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# LOGIN EVENTS
# ============================================================================

class LoginAttempted(BaseEvent):
    """Login attempt made."""
    event_type: str = "LoginAttempted"
    aggregate_type: str = "Session"
    account_id: str
    success: bool
    failure_reason: Optional[str] = None


# ============================================================================
# DEVICE EVENTS
# ============================================================================

class DeviceChanged(BaseEvent):
    """User changed device."""
    event_type: str = "DeviceChanged"
    aggregate_type: str = "Account"
    account_id: str
    new_device_id: str
    device_type: Optional[str] = None  # mobile, desktop, tablet
    browser: Optional[str] = None
    os: Optional[str] = None
    is_first_seen: bool = True


# ============================================================================
# LOCATION EVENTS
# ============================================================================

class LocationChanged(BaseEvent):
    """User location changed."""
    event_type: str = "LocationChanged"
    aggregate_type: str = "Account"
    account_id: str
    new_latitude: float
    new_longitude: float
    context: str  # "transaction" or "login"
    context_id: str  # transaction_id or login_id


# ============================================================================
# FRAUD EVENTS
# ============================================================================

class FraudFlagRaised(BaseEvent):
    """Fraud flag was raised on a transaction."""
    event_type: str = "FraudFlagRaised"
    aggregate_type: str = "Transaction"
    transaction_id: str
    account_id: str
    fraud_probability: float
    flagged_reasons: list[str]
    model_version: str
    auto_blocked: bool = False

    class Config:
        protected_namespaces = ()  # Allow 'model_' prefix


# ============================================================================
# EVENT REGISTRY
# ============================================================================

EVENT_TYPES = {
    "AccountCreated": AccountCreated,
    "TransactionInitiated": TransactionInitiated,
    "TransactionCompleted": TransactionCompleted,
    "TransactionFailed": TransactionFailed,
    "LoginAttempted": LoginAttempted,
    "DeviceChanged": DeviceChanged,
    "LocationChanged": LocationChanged,
    "FraudFlagRaised": FraudFlagRaised,
}


def deserialize_event(event_type: str, data: dict) -> BaseEvent:
    """Deserialize event from stored data."""
    event_class = EVENT_TYPES.get(event_type)
    if not event_class:
        raise ValueError(f"Unknown event type: {event_type}")
    return event_class(**data)
