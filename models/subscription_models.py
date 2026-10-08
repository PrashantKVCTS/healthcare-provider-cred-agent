"""
Subscription data models for Agent Credentialing Service.
Defines schemas for webhook subscriptions, event notification payloads,
and continuous monitoring alerts for Appian and external PMS consumers.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class SubscriptionEventType(str, Enum):
    ALL = "*"
    BATCH_COMPLETED = "BATCH_COMPLETED"
    CREDENTIALING_COMPLETED = "CREDENTIALING_COMPLETED"
    RECREDENTIALING_ALERT = "RECREDENTIALING_ALERT"
    CAQH_EXPIRATION_ALERT = "CAQH_EXPIRATION_ALERT"
    SANCTION_DETECTED = "SANCTION_DETECTED"


class SubscriptionRequest(BaseModel):
    client_name: str = Field(
        ...,
        description="Name of the subscribing client system or Appian process",
        json_schema_extra={"example": "Appian Healthcare PDM Orchestration"}
    )
    webhook_url: str = Field(
        ...,
        description="Target HTTP/HTTPS webhook URL (e.g. Appian Web API endpoint)",
        json_schema_extra={"example": "https://myhealthplan.appiancloud.com/suite/webapi/credentialing-callback"}
    )
    subscribed_events: List[SubscriptionEventType] = Field(
        default_factory=lambda: [SubscriptionEventType.ALL],
        description="List of credentialing event types to receive",
        json_schema_extra={"example": ["BATCH_COMPLETED", "RECREDENTIALING_ALERT"]}
    )
    auth_token: Optional[str] = Field(
        None,
        description="Optional Bearer token for authenticating against the target webhook",
        json_schema_extra={"example": "appian_api_key_xyz_789"}
    )
    secret_key: Optional[str] = Field(
        None,
        description="Shared secret used to generate HMAC-SHA256 header 'X-CredAgent-Signature'",
        json_schema_extra={"example": "cred-secret-key-42"}
    )
    is_active: bool = Field(True, description="Whether the subscription is currently active")


class SubscriptionModel(BaseModel):
    subscription_id: str = Field(default_factory=lambda: f"SUB-{uuid.uuid4().hex[:8].upper()}")
    client_name: str
    webhook_url: str
    subscribed_events: List[SubscriptionEventType]
    auth_token: Optional[str] = None
    secret_key: Optional[str] = None
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_notified_at: Optional[str] = None
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    last_delivery_status: Optional[str] = None


class WebhookEventPayload(BaseModel):
    event_id: str = Field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:12].upper()}")
    event_type: SubscriptionEventType
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    subscription_id: str
    client_name: str
    data: Dict[str, Any]


class TestWebhookRequest(BaseModel):
    event_type: SubscriptionEventType = Field(
        default=SubscriptionEventType.CREDENTIALING_COMPLETED,
        description="Simulated event type for the test ping"
    )


class AlertScanResponse(BaseModel):
    scan_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    providers_evaluated: int
    recred_alerts_dispatched: int
    caqh_alerts_dispatched: int
    sanction_alerts_dispatched: int
    total_notifications_sent: int
    details: List[Dict[str, Any]] = Field(default_factory=list)
