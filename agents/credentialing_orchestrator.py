"""
Credentialing Orchestrator Agent.
Coordinates multi-agent provider credentialing approval workflow:
1. Roster intake & data normalization (RosterIngestionAgent)
2. Primary Source Verification across NPI, CAQH, State Boards, Sanctions (PSVVerificationAgent)
3. Business Market Lines approval, product matching, and NCQA committee decisioning (BusinessRulesAgent)
4. Synthesis into Appian-compatible CDM / Case Management structures.
5. Event notifications via Credentialing Service Subscription API.
"""

import os
import uuid
from typing import List, Dict, Any, Union, Optional
from models.provider_models import RosterProviderItem
from models.credentialing_models import (
    ProviderCredentialingResult, BatchRosterResult, CredentialingAuditTrail
)
from models.subscription_models import SubscriptionEventType, AlertScanResponse
from agents.roster_ingestion_agent import RosterIngestionAgent
from agents.psv_verification_agent import PSVVerificationAgent
from agents.business_rules_agent import BusinessRulesAgent
from services.subscription_service import SubscriptionService


class CredentialingOrchestrator:
    """Master orchestrator agent for Provider Credentialing & Approval."""

    NAME = "CredentialingOrchestrator"

    def __init__(self, subscription_service: Optional[SubscriptionService] = None):
        self.ingestion_agent = RosterIngestionAgent()
        self.psv_agent = PSVVerificationAgent()
        self.rules_agent = BusinessRulesAgent()
        self.subscription_service = subscription_service or SubscriptionService()

    def process_single_provider(
        self,
        provider_item: RosterProviderItem,
        case_id: str = None,
        notify_subscribers: bool = True
    ) -> ProviderCredentialingResult:
        """Execute full credentialing workflow for an individual provider."""
        appian_case_id = case_id or f"CRED-{uuid.uuid4().hex[:8].upper()}"
        master_audit_trail: List[CredentialingAuditTrail] = []

        master_audit_trail.append(CredentialingAuditTrail(
            step_name="CREDENTIALING_WORKFLOW_INITIATED",
            agent_name=self.NAME,
            action_taken=f"Initiated credentialing case {appian_case_id} for NPI {provider_item.npi}",
            details=f"Provider: {provider_item.first_name} {provider_item.last_name}, State: {provider_item.practice_state}, Group: {provider_item.group_name or 'Independent'}",
            status="SUCCESS"
        ))

        # Step 1: Primary Source Verification
        npi_record, caqh_profile, psv_checks, psv_audit = self.psv_agent.verify_provider(provider_item)
        master_audit_trail.extend(psv_audit)

        # Step 2: Business Market Lines & Committee Rules Decisioning
        (
            overall_decision,
            decision_summary,
            recred_due_date,
            committee_review_needed,
            committee_flags,
            approved_lines,
            rejected_lines,
            rules_audit
        ) = self.rules_agent.evaluate_decision_and_market_lines(
            provider=provider_item,
            npi_record=npi_record,
            caqh_profile=caqh_profile,
            psv_checks=psv_checks
        )
        master_audit_trail.extend(rules_audit)

        # Step 3: Capture Additional Credentialing Summaries
        education_summary = [
            {
                "degree": e.degree,
                "institution": e.institution,
                "graduation_year": e.graduation_year,
                "type": e.degree_type,
                "verified": e.verified
            }
            for e in caqh_profile.education
        ]

        work_history_summary = [
            {
                "organization": w.organization,
                "position": w.position,
                "start_date": w.start_date,
                "end_date": w.end_date,
                "gap_flag": w.gap_flag,
                "gap_reason": w.gap_reason
            }
            for w in caqh_profile.work_history
        ]

        licenses_summary = [
            {
                "state": lic.state,
                "license_number": lic.license_number,
                "type": lic.license_type,
                "status": lic.status,
                "expiration_date": lic.expiration_date,
                "disciplinary_flag": lic.has_disciplinary_action
            }
            for lic in caqh_profile.licenses
        ]

        board_certs = [
            f"{b.specialty} ({b.board_name}) - {'ACTIVE' if b.is_active else 'EXPIRED'}"
            for b in caqh_profile.board_certifications
        ]

        ready_for_contracting = (overall_decision.value in ("APPROVED", "CONDITIONAL_APPROVAL"))

        master_audit_trail.append(CredentialingAuditTrail(
            step_name="CREDENTIALING_WORKFLOW_COMPLETE",
            agent_name=self.NAME,
            action_taken=f"Completed credentialing decision: {overall_decision.value}",
            details=f"Approved Market Lines: {len(approved_lines)}. Committee Review Required: {committee_review_needed}",
            status="SUCCESS"
        ))

        result = ProviderCredentialingResult(
            npi=provider_item.npi,
            provider_name=f"{provider_item.first_name} {provider_item.last_name}",
            caqh_id=caqh_profile.caqh_id,
            overall_decision=overall_decision,
            decision_summary=decision_summary,
            recredentialing_due_date=recred_due_date,
            committee_review_needed=committee_review_needed,
            committee_flags=committee_flags,
            psv_checks=psv_checks,
            approved_market_lines=approved_lines,
            rejected_market_lines=rejected_lines,
            npi_profile=npi_record,
            caqh_profile=caqh_profile,
            education_summary=education_summary,
            work_history_summary=work_history_summary,
            licenses_summary=licenses_summary,
            board_certifications=board_certs,
            audit_trail=master_audit_trail,
            appian_case_id=appian_case_id,
            ready_for_pdm_contracting=ready_for_contracting
        )

        # Notify active Appian subscribers
        if notify_subscribers and self.subscription_service:
            event_data = {
                "npi": result.npi,
                "provider_name": result.provider_name,
                "appian_case_id": result.appian_case_id,
                "overall_decision": result.overall_decision.value,
                "decision_summary": result.decision_summary,
                "recredentialing_due_date": result.recredentialing_due_date,
                "ready_for_contracting": result.ready_for_pdm_contracting,
                "approved_market_lines_count": len(result.approved_market_lines)
            }
            self.subscription_service.dispatch_event(
                SubscriptionEventType.CREDENTIALING_COMPLETED,
                event_data
            )

        return result

    def process_roster(
        self,
        roster_input: Union[str, List[Dict[str, Any]]],
        filename: str = "roster.csv",
        notify_subscribers: bool = True
    ) -> BatchRosterResult:
        """Process an entire roster file (CSV file path, raw string, or JSON list)."""
        batch_id = f"BATCH-{uuid.uuid4().hex[:6].upper()}"

        if isinstance(roster_input, str) and filename == "roster.csv" and os.path.isfile(roster_input):
            filename = os.path.basename(roster_input)

        if isinstance(roster_input, list):
            providers = self.ingestion_agent.parse_json_content(roster_input)
        elif isinstance(roster_input, str):
            stripped = roster_input.strip()
            if stripped.startswith("[") or stripped.startswith("{"):
                providers = self.ingestion_agent.parse_json_content(roster_input)
            elif roster_input.lower().endswith(".json") or filename.lower().endswith(".json"):
                providers = self.ingestion_agent.parse_json_content(roster_input)
            elif os.path.isfile(roster_input):
                try:
                    with open(roster_input, "r", encoding="utf-8-sig") as f:
                        first_chars = f.read(10).strip()
                    if first_chars.startswith("[") or first_chars.startswith("{"):
                        providers = self.ingestion_agent.parse_json_content(roster_input)
                    else:
                        providers = self.ingestion_agent.parse_csv_content(roster_input)
                except Exception:
                    providers = self.ingestion_agent.parse_csv_content(roster_input)
            else:
                providers = self.ingestion_agent.parse_csv_content(roster_input)
        else:
            providers = []

        results: List[ProviderCredentialingResult] = []
        approved_count = 0
        conditional_count = 0
        committee_count = 0
        denied_count = 0

        for provider in providers:
            # We skip individual notifications inside bulk batch to avoid overwhelming webhook listeners
            res = self.process_single_provider(provider, notify_subscribers=False)
            results.append(res)

            if res.overall_decision.value == "APPROVED":
                approved_count += 1
            elif res.overall_decision.value == "CONDITIONAL_APPROVAL":
                conditional_count += 1
            elif res.overall_decision.value == "COMMITTEE_REVIEW_REQUIRED":
                committee_count += 1
            elif res.overall_decision.value == "DENIED":
                denied_count += 1

        batch_result = BatchRosterResult(
            batch_id=batch_id,
            filename=filename,
            total_providers=len(results),
            approved_count=approved_count,
            conditional_count=conditional_count,
            committee_review_count=committee_count,
            denied_count=denied_count,
            results=results
        )

        # Notify active Appian subscribers of batch completion
        if notify_subscribers and self.subscription_service:
            batch_event_data = {
                "batch_id": batch_result.batch_id,
                "filename": batch_result.filename,
                "total_providers": batch_result.total_providers,
                "approved_count": batch_result.approved_count,
                "conditional_count": batch_result.conditional_count,
                "committee_review_count": batch_result.committee_review_count,
                "denied_count": batch_result.denied_count
            }
            self.subscription_service.dispatch_event(
                SubscriptionEventType.BATCH_COMPLETED,
                batch_event_data
            )

        return batch_result

    def run_credentialing_alert_scan(self, providers: Optional[List[ProviderCredentialingResult]] = None) -> AlertScanResponse:
        """Scan providers for 90-day recredentialing and CAQH expiration alerts."""
        if not providers:
            # Run scan against sample roster as baseline
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sample_csv = os.path.join(base_dir, "data", "sample_provider_roster.csv")
            batch_res = self.process_roster(sample_csv, notify_subscribers=False)
            providers = batch_res.results

        return self.subscription_service.scan_for_credentialing_alerts(providers)
