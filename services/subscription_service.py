"""
Subscription and Webhook Dispatch Service.
Manages webhook subscriptions, generates HMAC-SHA256 signatures,
delivers event notifications to Appian and external consumers,
and runs continuous monitoring alert scans (Recredentialing & CAQH Expiration).
"""

import os
import json
import hmac
import hashlib
import requests
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from models.subscription_models import (
    SubscriptionRequest, SubscriptionModel, WebhookEventPayload,
    SubscriptionEventType, AlertScanResponse
)


class SubscriptionService:
    """Manages subscription registrations and dispatches webhooks to Appian."""

    def __init__(self, storage_path: Optional[str] = None):
        if not storage_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage_path = os.path.join(base_dir, "data", "subscriptions.json")
        self.storage_path = storage_path
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensure subscription data directory and JSON file exist."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def _load_subscriptions(self) -> List[SubscriptionModel]:
        """Load subscriptions from JSON file."""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                raw_list = json.load(f)
                return [SubscriptionModel(**item) for item in raw_list]
        except Exception:
            return []

    def _save_subscriptions(self, subs: List[SubscriptionModel]):
        """Persist subscriptions to JSON file."""
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump([s.model_dump() for s in subs], f, indent=2)

    def register_subscription(self, request: SubscriptionRequest) -> SubscriptionModel:
        """Register a new webhook subscription."""
        subs = self._load_subscriptions()
        new_sub = SubscriptionModel(
            client_name=request.client_name,
            webhook_url=request.webhook_url,
            subscribed_events=request.subscribed_events,
            auth_token=request.auth_token,
            secret_key=request.secret_key,
            is_active=request.is_active
        )
        subs.append(new_sub)
        self._save_subscriptions(subs)
        return new_sub

    def list_subscriptions(self) -> List[SubscriptionModel]:
        """Return all registered subscriptions."""
        return self._load_subscriptions()

    def get_subscription(self, subscription_id: str) -> Optional[SubscriptionModel]:
        """Get subscription by ID."""
        subs = self._load_subscriptions()
        for s in subs:
            if s.subscription_id == subscription_id:
                return s
        return None

    def update_subscription(self, subscription_id: str, is_active: Optional[bool] = None, webhook_url: Optional[str] = None) -> Optional[SubscriptionModel]:
        """Update subscription state or URL."""
        subs = self._load_subscriptions()
        target = None
        for s in subs:
            if s.subscription_id == subscription_id:
                if is_active is not None:
                    s.is_active = is_active
                if webhook_url is not None:
                    s.webhook_url = webhook_url
                target = s
                break
        if target:
            self._save_subscriptions(subs)
        return target

    def delete_subscription(self, subscription_id: str) -> bool:
        """Remove a subscription."""
        subs = self._load_subscriptions()
        initial_len = len(subs)
        subs = [s for s in subs if s.subscription_id != subscription_id]
        if len(subs) < initial_len:
            self._save_subscriptions(subs)
            return True
        return False

    def generate_signature(self, secret_key: str, payload_json: str) -> str:
        """Generate HMAC-SHA256 signature for payload verification in Appian."""
        if not secret_key:
            return ""
        return hmac.new(
            secret_key.encode("utf-8"),
            payload_json.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def deliver_event(self, subscription: SubscriptionModel, event_payload: WebhookEventPayload) -> Dict[str, Any]:
        """Deliver webhook payload to subscriber endpoint."""
        headers = {
            "Content-Type": "application/json",
            "X-CredAgent-Event": event_payload.event_type.value,
            "X-CredAgent-Event-Id": event_payload.event_id,
            "X-CredAgent-Timestamp": event_payload.timestamp
        }
        if subscription.auth_token:
            headers["Authorization"] = f"Bearer {subscription.auth_token}"

        payload_json = event_payload.model_dump_json()

        if subscription.secret_key:
            sig = self.generate_signature(subscription.secret_key, payload_json)
            headers["X-CredAgent-Signature"] = f"sha256={sig}"

        subs = self._load_subscriptions()
        delivery_res = {
            "subscription_id": subscription.subscription_id,
            "url": subscription.webhook_url,
            "status": "DISPATCHED"
        }

        try:
            resp = requests.post(
                subscription.webhook_url,
                data=payload_json,
                headers=headers,
                timeout=4.0
            )
            success = 200 <= resp.status_code < 300
            delivery_res["status_code"] = resp.status_code
            delivery_res["success"] = success

            # Update metrics
            for s in subs:
                if s.subscription_id == subscription.subscription_id:
                    s.last_notified_at = datetime.now().isoformat()
                    if success:
                        s.successful_deliveries += 1
                        s.last_delivery_status = f"SUCCESS (HTTP {resp.status_code})"
                    else:
                        s.failed_deliveries += 1
                        s.last_delivery_status = f"FAILED (HTTP {resp.status_code})"
                    break
            self._save_subscriptions(subs)

        except Exception as e:
            delivery_res["status_code"] = None
            delivery_res["success"] = False
            delivery_res["error"] = str(e)

            for s in subs:
                if s.subscription_id == subscription.subscription_id:
                    s.last_notified_at = datetime.now().isoformat()
                    s.failed_deliveries += 1
                    s.last_delivery_status = f"ERROR ({str(e)[:50]})"
                    break
            self._save_subscriptions(subs)

        return delivery_res

    def dispatch_event(self, event_type: SubscriptionEventType, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Dispatch an event to all matching active subscribers."""
        subs = self._load_subscriptions()
        deliveries = []

        for sub in subs:
            if not sub.is_active:
                continue

            matches = (
                SubscriptionEventType.ALL in sub.subscribed_events or
                event_type in sub.subscribed_events or
                any(e.value == event_type.value for e in sub.subscribed_events)
            )

            if matches:
                payload = WebhookEventPayload(
                    event_type=event_type,
                    subscription_id=sub.subscription_id,
                    client_name=sub.client_name,
                    data=data
                )
                res = self.deliver_event(sub, payload)
                deliveries.append(res)

        return deliveries

    def scan_for_credentialing_alerts(self, providers: List[Any]) -> AlertScanResponse:
        """
        Scan providers for upcoming recredentialing deadlines (<= 90 days),
        CAQH attestation expirations (> 90 days old or expired), and sanction flags.
        Dispatches webhooks to all subscribed Appian listeners.
        """
        now = datetime.now().date()
        recred_count = 0
        caqh_count = 0
        sanction_count = 0
        total_notifications = 0
        details = []

        for p in providers:
            npi = getattr(p, "npi", "UNKNOWN")
            name = getattr(p, "provider_name", "Unknown Provider")
            recred_date_str = getattr(p, "recredentialing_due_date", None)
            caqh_prof = getattr(p, "caqh_profile", None)
            decision = getattr(p, "overall_decision", None)

            # 1. Recredentialing Cycle Alert Check
            if recred_date_str:
                try:
                    recred_dt = datetime.strptime(recred_date_str, "%Y-%m-%d").date()
                    days_remaining = (recred_dt - now).days
                    if 0 <= days_remaining <= 90:
                        recred_count += 1
                        alert_data = {
                            "npi": npi,
                            "provider_name": name,
                            "alert_type": "RECREDENTIALING_DUE",
                            "recredentialing_due_date": recred_date_str,
                            "days_remaining": days_remaining,
                            "action_required": "Initiate 36-month NCQA Re-credentialing package in Appian"
                        }
                        self.dispatch_event(SubscriptionEventType.RECREDENTIALING_ALERT, alert_data)
                        total_notifications += 1
                        details.append(alert_data)
                except ValueError:
                    pass

            # 2. CAQH Attestation Currency Alert Check (NCQA 120-day rule)
            if caqh_prof:
                days_since = getattr(caqh_prof, "days_since_attestation", 0)
                is_curr = getattr(caqh_prof, "is_attestation_current", True)
                if not is_curr or days_since >= 90:
                    caqh_count += 1
                    caqh_alert = {
                        "npi": npi,
                        "provider_name": name,
                        "caqh_id": getattr(caqh_prof, "caqh_id", "N/A"),
                        "days_since_attestation": days_since,
                        "attestation_date": getattr(caqh_prof, "attestation_date", "N/A"),
                        "status": "EXPIRED" if not is_curr else "EXPIRING_SOON",
                        "action_required": "Trigger Appian User Task for Provider CAQH Re-Attestation"
                    }
                    self.dispatch_event(SubscriptionEventType.CAQH_EXPIRATION_ALERT, caqh_alert)
                    total_notifications += 1
                    details.append(caqh_alert)

            # 3. Sanction Alert Check
            if decision and getattr(decision, "value", str(decision)) == "DENIED":
                sanction_count += 1
                sanction_alert = {
                    "npi": npi,
                    "provider_name": name,
                    "alert_type": "SANCTION_FLAGGED",
                    "reason": getattr(p, "decision_summary", "Critical PSV Failure"),
                    "action_required": "Initiate Network Termination and Compliance Review in Appian"
                }
                self.dispatch_event(SubscriptionEventType.SANCTION_DETECTED, sanction_alert)
                total_notifications += 1
                details.append(sanction_alert)

        return AlertScanResponse(
            providers_evaluated=len(providers),
            recred_alerts_dispatched=recred_count,
            caqh_alerts_dispatched=caqh_count,
            sanction_alerts_dispatched=sanction_count,
            total_notifications_sent=total_notifications,
            details=details
        )
