"""Event sourcing components."""

from .event_models import (
    BaseEvent,
    EventMetadata,
    AccountCreated,
    TransactionInitiated,
    TransactionCompleted,
    TransactionFailed,
    LoginAttempted,
    DeviceChanged,
    LocationChanged,
    FraudFlagRaised,
    EVENT_TYPES,
    deserialize_event
)
from .event_store import EventStore
from .event_processor import EventProcessor, EventHandler

__all__ = [
    'BaseEvent',
    'EventMetadata',
    'AccountCreated',
    'TransactionInitiated',
    'TransactionCompleted',
    'TransactionFailed',
    'LoginAttempted',
    'DeviceChanged',
    'LocationChanged',
    'FraudFlagRaised',
    'EVENT_TYPES',
    'deserialize_event',
    'EventStore',
    'EventProcessor',
    'EventHandler',
]
