"""
Appian REST API Interface for Provider Credentialing Automation & Subscription Service.
Exposes endpoints compatible with Appian Connected Systems, Integration Objects,
Process Models, and Webhook Event Subscriptions.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, status, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import base64
import os
import sys

# Ensure project root is in sys.path when executed directly or via python api/appian_api.py
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import uvicorn

from agents.credentialing_orchestrator import CredentialingOrchestrator
from models.provider_models import RosterProviderItem
from models.credentialing_models import (
    ProviderCredentialingResult, BatchRosterResult
)
from models.subscription_models import (
    SubscriptionRequest, SubscriptionModel, SubscriptionEventType,
    TestWebhookRequest, AlertScanResponse, WebhookEventPayload
)
from services.subscription_service import SubscriptionService

app = FastAPI(
    title="Appian Provider Credentialing Approval Agent API",
    description=(
        "Enterprise Credentialing Approval and Event Subscription API for Healthcare Provider Management Systems (PMS). "
        "Performs Primary Source Verification (NPI & CAQH ProView), captures clinical credentials (education, work history, "
        "state licenses, DEA, board certifications), evaluates business market lines with products/dates, "
        "and publishes event webhooks for Appian Process Automation."
    ),
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for Appian Web API / Portal consumption
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

subscription_service = SubscriptionService()
orchestrator = CredentialingOrchestrator(subscription_service=subscription_service)


# -------------------------------------------------------------
# PYDANTIC REQUEST SCHEMAS (CLEANED FOR PYDANTIC V2)
# -------------------------------------------------------------
class SingleProviderRequest(BaseModel):
    npi: str = Field(
        ...,
        description="10-digit National Provider Identifier",
        json_schema_extra={"example": "1234567893"}
    )
    first_name: str = Field(
        ...,
        description="Provider legal first name",
        json_schema_extra={"example": "Sarah"}
    )
    last_name: str = Field(
        ...,
        description="Provider legal last name",
        json_schema_extra={"example": "Conner"}
    )
    caqh_id: Optional[str] = Field(
        None,
        description="CAQH ProView ID",
        json_schema_extra={"example": "14892011"}
    )
    tin: Optional[str] = Field(
        None,
        description="Tax ID / EIN",
        json_schema_extra={"example": "74-8899123"}
    )
    group_name: Optional[str] = Field(
        None,
        description="Provider group practice",
        json_schema_extra={"example": "Austin Family Health Partners"}
    )
    specialty: Optional[str] = Field(
        "Family Medicine",
        description="Specialty taxonomy description",
        json_schema_extra={"example": "Family Medicine"}
    )
    practice_state: str = Field(
        "TX",
        description="Practicing location state code",
        json_schema_extra={"example": "TX"}
    )
    requested_products: List[str] = Field(
        default_factory=lambda: ["Commercial HMO", "Commercial PPO", "Medicare Advantage", "Medicaid"],
        description="Lines of business and products requested for participation"
    )
    appian_case_id: Optional[str] = Field(
        None,
        description="Appian Case/Process ID",
        json_schema_extra={"example": "APP-CRED-2026-001"}
    )


class RosterBase64Request(BaseModel):
    filename: str = Field(
        "roster.csv",
        description="Name of the uploaded roster file",
        json_schema_extra={"example": "network_provider_roster_q4.csv"}
    )
    base64_content: str = Field(
        ...,
        description="Base64-encoded string of the CSV or JSON file from Appian a!document()"
    )


class SubscriptionUpdateRequest(BaseModel):
    is_active: Optional[bool] = Field(None, description="Toggle active/paused status")
    webhook_url: Optional[str] = Field(None, description="Updated target webhook URL")


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    connected_system_ready: bool
    active_subscriptions: int


# -------------------------------------------------------------
# 0. STANDALONE WEB OPERATIONS WORKBENCH UI
# -------------------------------------------------------------
@app.get("/", include_in_schema=False)
def root_redirect():
    """Redirect root to the interactive Web Operations Workbench UI."""
    return RedirectResponse(url="/ui")


@app.get("/ui", response_class=HTMLResponse, tags=["Web Operations UI"], summary="Web Operations Workbench UI")
def serve_web_ui():
    """Serves the standalone HTML/JS Credentialing Operations Workbench UI."""
    portal_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "portal.html")
    if os.path.exists(portal_path):
        with open(portal_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>Portal UI not found.</h3>", status_code=404)


# -------------------------------------------------------------
# 1. SYSTEM & HEALTH CHECK
# -------------------------------------------------------------
@app.get("/api/v1/health", response_model=HealthResponse, tags=["Appian Health & System"])
def health_check():
    """Health check endpoint for Appian Connected System connection verification."""
    subs = subscription_service.list_subscriptions()
    active_count = sum(1 for s in subs if s.is_active)
    return HealthResponse(
        status="UP",
        service="Healthcare Credentialing Approval Agent",
        version="2.1.0",
        connected_system_ready=True,
        active_subscriptions=active_count
    )


@app.get("/api/v1/market-lines", tags=["Market Lines & Rules"])
def get_market_lines():
    """Returns the business-approved market lines, product codes, network tiers, and rules."""
    return orchestrator.rules_agent.market_lines_config


# -------------------------------------------------------------
# 2. CORE APPIAN CREDENTIALING WORKFLOW ENDPOINTS
# -------------------------------------------------------------
@app.post(
    "/api/v1/provider/credential",
    response_model=ProviderCredentialingResult,
    tags=["Appian Credentialing Automation"],
    summary="Credential Single Provider (On-Demand / Record Action)"
)
def credential_single_provider(request: SingleProviderRequest):
    """
    Called by Appian Integration Object or Process Model to credential a single provider on-demand.
    Validates NPI and CAQH ProView, gathers market lines, captures education/work history/licenses,
    and returns full decision docket.
    """
    provider_item = RosterProviderItem(
        npi=request.npi,
        first_name=request.first_name,
        last_name=request.last_name,
        caqh_id=request.caqh_id,
        tin=request.tin,
        group_name=request.group_name,
        specialty=request.specialty,
        practice_state=request.practice_state,
        requested_products=request.requested_products
    )

    result = orchestrator.process_single_provider(provider_item, case_id=request.appian_case_id)
    return result


@app.post(
    "/api/v1/roster/process",
    response_model=BatchRosterResult,
    tags=["Appian Credentialing Automation"],
    summary="Process Provider Roster File (Batch / Ingestion)"
)
async def process_roster_file(file: UploadFile = File(...)):
    """
    Called by Appian Process Model when a provider roster file (CSV) is uploaded in Appian.
    Parses roster records, executes agentic validation for each provider, and returns batch stats.
    """
    try:
        content = await file.read()
        decoded_content = content.decode("utf-8", errors="replace")
        batch_result = orchestrator.process_roster(decoded_content, filename=file.filename)
        return batch_result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process roster file: {str(e)}")


@app.post(
    "/api/v1/roster/process-base64",
    response_model=BatchRosterResult,
    tags=["Appian Credentialing Automation"],
    summary="Process Roster via Base64 (Appian Document Integration)"
)
def process_roster_base64(payload: RosterBase64Request):
    """
    Called by Appian Integration Object passing a document converted to Base64
    via Appian's documentToBase64() or smart service.
    """
    try:
        decoded_bytes = base64.b64decode(payload.base64_content)
        decoded_str = decoded_bytes.decode("utf-8", errors="replace")
        batch_result = orchestrator.process_roster(decoded_str, filename=payload.filename)
        return batch_result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode and process base64 roster: {str(e)}")


@app.post(
    "/api/v1/roster/process-json",
    response_model=BatchRosterResult,
    tags=["Appian Credentialing Automation"],
    summary="Process Provider Roster JSON (Appian Process Variables)"
)
def process_roster_json(providers: List[SingleProviderRequest]):
    """
    Called by Appian Process Model passing an array of CDT records directly as JSON payload.
    """
    dict_payload = [p.model_dump() for p in providers]
    batch_result = orchestrator.process_roster(dict_payload, filename="appian_process_roster.json")
    return batch_result


@app.post(
    "/api/v1/roster/process-sample",
    response_model=BatchRosterResult,
    tags=["Appian Credentialing Automation"],
    summary="Process Sample Test Roster (Web UI 1-Click Intake)"
)
def process_sample_roster():
    """
    Loads and evaluates the default multi-scenario sample provider roster.
    Useful for immediate testing, demos, and web portal operations.
    """
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    sample_csv = os.path.join(data_dir, "sample_provider_roster.csv")
    if not os.path.exists(sample_csv):
        raise HTTPException(status_code=404, detail="Default sample provider roster file not found.")
    with open(sample_csv, "r", encoding="utf-8") as f:
        content = f.read()
    return orchestrator.process_roster(content, filename="sample_provider_roster.csv")


# -------------------------------------------------------------
# 3. AGENT CREDENTIALING SERVICE SUBSCRIPTION API (NEW!)
# -------------------------------------------------------------
@app.post(
    "/api/v1/subscriptions",
    response_model=SubscriptionModel,
    status_code=status.HTTP_201_CREATED,
    tags=["Agent Credentialing Service Subscriptions"],
    summary="Register Webhook Subscription for Appian Events"
)
def create_subscription(request: SubscriptionRequest):
    """
    Register Appian Web API or external consumer to receive real-time webhook notifications
    for credentialing events (e.g. BATCH_COMPLETED, CREDENTIALING_COMPLETED, RECREDENTIALING_ALERT,
    CAQH_EXPIRATION_ALERT, SANCTION_DETECTED).
    """
    sub = subscription_service.register_subscription(request)
    return sub


@app.get(
    "/api/v1/subscriptions",
    response_model=List[SubscriptionModel],
    tags=["Agent Credentialing Service Subscriptions"],
    summary="List All Webhook Subscriptions"
)
def list_subscriptions():
    """Retrieve all registered subscriptions and their delivery health metrics."""
    return subscription_service.list_subscriptions()


@app.get(
    "/api/v1/subscriptions/{subscription_id}",
    response_model=SubscriptionModel,
    tags=["Agent Credentialing Service Subscriptions"],
    summary="Get Subscription Details"
)
def get_subscription(subscription_id: str = Path(..., description="Unique Subscription ID")):
    """Get metadata and telemetry for a specific subscription."""
    sub = subscription_service.get_subscription(subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail=f"Subscription {subscription_id} not found")
    return sub


@app.put(
    "/api/v1/subscriptions/{subscription_id}",
    response_model=SubscriptionModel,
    tags=["Agent Credentialing Service Subscriptions"],
    summary="Update Subscription Status or Target URL"
)
def update_subscription(
    subscription_id: str = Path(..., description="Unique Subscription ID"),
    payload: SubscriptionUpdateRequest = None
):
    """Pause, resume, or update the target webhook URL for a subscription."""
    updated = subscription_service.update_subscription(
        subscription_id,
        is_active=payload.is_active if payload else None,
        webhook_url=payload.webhook_url if payload else None
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Subscription {subscription_id} not found")
    return updated


@app.delete(
    "/api/v1/subscriptions/{subscription_id}",
    tags=["Agent Credentialing Service Subscriptions"],
    summary="Cancel Webhook Subscription"
)
def delete_subscription(subscription_id: str = Path(..., description="Unique Subscription ID")):
    """De-register an Appian webhook subscription."""
    deleted = subscription_service.delete_subscription(subscription_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Subscription {subscription_id} not found")
    return {"message": f"Subscription {subscription_id} successfully cancelled", "deleted": True}


@app.post(
    "/api/v1/subscriptions/{subscription_id}/test",
    tags=["Agent Credentialing Service Subscriptions"],
    summary="Send Test Ping / Verification Webhook"
)
def test_subscription_webhook(
    subscription_id: str = Path(..., description="Unique Subscription ID"),
    req: TestWebhookRequest = TestWebhookRequest()
):
    """
    Dispatches a mock event payload to the registered webhook URL to verify network connectivity,
    Appian authentication, and HMAC signature validation.
    """
    sub = subscription_service.get_subscription(subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail=f"Subscription {subscription_id} not found")

    mock_event = WebhookEventPayload(
        event_type=req.event_type,
        subscription_id=sub.subscription_id,
        client_name=sub.client_name,
        data={
            "test_ping": True,
            "message": "Verification test webhook from Healthcare Credentialing Approval Agent",
            "npi": "1234567893",
            "provider_name": "SARAH CONNER",
            "decision": "APPROVED",
            "approved_products": ["Commercial HMO Premier", "Medicare Advantage Choice HMO"]
        }
    )
    delivery_result = subscription_service.deliver_event(sub, mock_event)
    return {
        "subscription_id": sub.subscription_id,
        "webhook_url": sub.webhook_url,
        "delivery_result": delivery_result
    }


@app.post(
    "/api/v1/subscriptions/scan-alerts",
    response_model=AlertScanResponse,
    tags=["Agent Credentialing Service Subscriptions"],
    summary="Trigger Continuous Monitoring Alert Scan"
)
def trigger_alert_scan():
    """
    Scans provider network for upcoming 90-day NCQA recredentialing deadlines,
    expiring CAQH attestations (> 90 days), and sanction flags.
    Automatically dispatches webhooks to all subscribed Appian callback endpoints.
    """
    scan_result = orchestrator.run_credentialing_alert_scan()
    return scan_result


# -------------------------------------------------------------
# 4. APPIAN OPENAPI SCHEMA EXPORT
# -------------------------------------------------------------
@app.get("/api/v1/appian/openapi.json", tags=["Appian Setup"])
def get_appian_openapi():
    """Returns OpenAPI schema for 1-click import into Appian Integration Designer."""
    return app.openapi()


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api.appian_api:app", host=host, port=port, app_dir=PROJECT_ROOT)
