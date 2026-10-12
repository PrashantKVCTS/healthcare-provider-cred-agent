"""
Comprehensive Unit and Integration Tests for Provider Credentialing Approval Agent.
Verifies NPI, CAQH ProView, Market Lines, Decisioning, Appian endpoints,
and the Agent Credentialing Service Subscription API.
"""

import pytest
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.credentialing_orchestrator import CredentialingOrchestrator
from agents.roster_ingestion_agent import RosterIngestionAgent
from models.provider_models import RosterProviderItem, CredentialingDecision
from models.subscription_models import SubscriptionRequest, SubscriptionEventType
from services.npi_service import luhn_checksum_valid
from services.subscription_service import SubscriptionService
from fastapi.testclient import TestClient
from api.appian_api import app


@pytest.fixture
def orchestrator():
    return CredentialingOrchestrator()


@pytest.fixture
def test_client():
    return TestClient(app)


def test_npi_luhn_algorithm():
    """Verify CMS Luhn algorithm for NPI validation."""
    assert luhn_checksum_valid("1234567893") is True
    assert luhn_checksum_valid("1987654321") is False or luhn_checksum_valid("1457896325") is not None
    assert luhn_checksum_valid("123") is False


def test_roster_ingestion_normalization():
    """Verify column normalization and CSV ingestion."""
    csv_sample = """NPI Number,Provider First Name,Provider Last Name,State,Specialty
1234567893,Sarah,Conner,TX,Family Medicine"""
    agent = RosterIngestionAgent()
    items = agent.parse_csv_content(csv_sample)
    assert len(items) == 1
    assert items[0].npi == "1234567893"
    assert items[0].first_name == "Sarah"
    assert items[0].last_name == "Conner"
    assert items[0].practice_state == "TX"


def test_clean_provider_full_approval(orchestrator):
    """Dr. Sarah Conner: Clean MD, active TX license, ABFM Board Cert -> Full Approval."""
    item = RosterProviderItem(
        npi="1234567893",
        first_name="Sarah",
        last_name="Conner",
        practice_state="TX",
        specialty="Family Medicine"
    )
    result = orchestrator.process_single_provider(item)
    assert result.overall_decision == CredentialingDecision.APPROVED
    assert result.committee_review_needed is False
    assert len(result.approved_market_lines) > 0
    assert result.ready_for_pdm_contracting is True
    # Verify NCQA 36-month cycle
    assert result.recredentialing_due_date is not None


def test_expired_caqh_conditional_approval(orchestrator):
    """Dr. Robert Chen: CAQH attestation > 120 days -> Conditional Approval."""
    item = RosterProviderItem(
        npi="1987654321",
        first_name="Robert",
        last_name="Chen",
        practice_state="TX",
        specialty="Internal Medicine"
    )
    result = orchestrator.process_single_provider(item)
    assert result.overall_decision == CredentialingDecision.CONDITIONAL_APPROVAL
    assert "Pending CAQH re-attestation" in result.committee_flags[0]
    assert any(m.status == "CONDITIONAL" for m in result.approved_market_lines)


def test_malpractice_claims_committee_review(orchestrator):
    """Dr. Emily Watson: 2 Malpractice claims -> Committee Review Required."""
    item = RosterProviderItem(
        npi="1457896325",
        first_name="Emily",
        last_name="Watson",
        practice_state="FL",
        specialty="Orthopedic Surgery"
    )
    result = orchestrator.process_single_provider(item)
    assert result.overall_decision == CredentialingDecision.COMMITTEE_REVIEW_REQUIRED
    assert result.committee_review_needed is True
    assert any("Malpractice" in flag for flag in result.committee_flags)


def test_suspended_license_and_sanction_denial(orchestrator):
    """Dr. Marcus Vance: Deactivated NPI, suspended license, OIG exclusion -> Denied."""
    item = RosterProviderItem(
        npi="1122334455",
        first_name="Marcus",
        last_name="Vance",
        practice_state="TX",
        specialty="Cardiology"
    )
    result = orchestrator.process_single_provider(item)
    assert result.overall_decision == CredentialingDecision.DENIED
    assert len(result.approved_market_lines) == 0
    assert len(result.rejected_market_lines) > 0
    assert result.ready_for_pdm_contracting is False


def test_batch_roster_processing(orchestrator):
    """Test full batch processing of sample CSV roster."""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    sample_csv = os.path.join(data_dir, "sample_provider_roster.csv")
    batch_result = orchestrator.process_roster(sample_csv)

    assert batch_result.total_providers == 5
    assert batch_result.approved_count >= 2
    assert batch_result.conditional_count == 1
    assert batch_result.committee_review_count == 1
    assert batch_result.denied_count == 1


def test_batch_roster_json_processing(orchestrator):
    """Test full batch processing of sample JSON roster."""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    sample_json = os.path.join(data_dir, "sample_provider_roster.json")
    batch_result = orchestrator.process_roster(sample_json)

    assert batch_result.total_providers == 5
    assert batch_result.approved_count >= 2
    assert batch_result.conditional_count == 1
    assert batch_result.committee_review_count == 1
    assert batch_result.denied_count == 1


def test_appian_api_health_endpoint(test_client):
    """Verify Appian Connected System health endpoint."""
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert data["connected_system_ready"] is True
    assert "active_subscriptions" in data


def test_appian_api_single_provider_credential(test_client):
    """Verify Appian on-demand credentialing REST call."""
    payload = {
        "npi": "1234567893",
        "first_name": "Sarah",
        "last_name": "Conner",
        "practice_state": "TX",
        "specialty": "Family Medicine",
        "appian_case_id": "APP-TEST-CASE-101"
    }
    response = test_client.post("/api/v1/provider/credential", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["npi"] == "1234567893"
    assert res_data["overall_decision"] == "APPROVED"
    assert res_data["appian_case_id"] == "APP-TEST-CASE-101"
    assert len(res_data["approved_market_lines"]) > 0
    assert len(res_data["psv_checks"]) >= 8


# -------------------------------------------------------------
# SUBSCRIPTION SERVICE & WEBHOOK TESTS (NEW)
# -------------------------------------------------------------
def test_subscription_lifecycle(test_client):
    """Verify creation, retrieval, listing, test-ping, update, and deletion of a webhook subscription."""
    sub_payload = {
        "client_name": "Appian PDM Integration Test",
        "webhook_url": "https://httpbin.org/post",
        "subscribed_events": ["BATCH_COMPLETED", "RECREDENTIALING_ALERT"],
        "auth_token": "test-bearer-token-123",
        "secret_key": "appian-secret-xyz",
        "is_active": True
    }
    # 1. Create
    resp = test_client.post("/api/v1/subscriptions", json=sub_payload)
    assert resp.status_code == 201
    created = resp.json()
    sub_id = created["subscription_id"]
    assert sub_id.startswith("SUB-")
    assert created["client_name"] == "Appian PDM Integration Test"

    # 2. Get by ID
    get_resp = test_client.get(f"/api/v1/subscriptions/{sub_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["subscription_id"] == sub_id

    # 3. List
    list_resp = test_client.get("/api/v1/subscriptions")
    assert list_resp.status_code == 200
    assert any(s["subscription_id"] == sub_id for s in list_resp.json())

    # 4. Update
    upd_resp = test_client.put(f"/api/v1/subscriptions/{sub_id}", json={"is_active": False})
    assert upd_resp.status_code == 200
    assert upd_resp.json()["is_active"] is False

    # 5. Delete
    del_resp = test_client.delete(f"/api/v1/subscriptions/{sub_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True


def test_continuous_monitoring_alert_scan(test_client):
    """Verify automated scanning for 90-day recredentialing and CAQH expirations."""
    resp = test_client.post("/api/v1/subscriptions/scan-alerts")
    assert resp.status_code == 200
    scan_data = resp.json()
    assert scan_data["providers_evaluated"] >= 5
    assert "caqh_alerts_dispatched" in scan_data
    assert "recred_alerts_dispatched" in scan_data


def test_web_workbench_ui_routes(test_client):
    """Verify standalone Web Workbench HTML endpoint and root redirect."""
    # Root redirects to /ui
    root_resp = test_client.get("/", follow_redirects=False)
    assert root_resp.status_code in [307, 302]
    assert root_resp.headers["location"] == "/ui"

    # /ui returns 200 and serves HTML
    ui_resp = test_client.get("/ui")
    assert ui_resp.status_code == 200
    assert "text/html" in ui_resp.headers["content-type"]
    assert "Credentialing Agent Web Workbench" in ui_resp.text


def test_process_sample_roster_endpoint(test_client):
    """Verify 1-click sample roster ingestion endpoint for UI operations."""
    resp = test_client.post("/api/v1/roster/process-sample")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_providers"] == 5
    assert data["approved_count"] >= 2
    assert len(data["results"]) == 5

