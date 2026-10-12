"""
Business Rules & Market Lines Decisioning Agent.
Evaluates provider eligibility for business market lines, products, tiers,
and determines Credentialing Approval, Conditional Approval, Committee Review, or Denial.
Calculates effective, expiration, and re-credentialing cycle dates according to NCQA standards.
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from models.provider_models import RosterProviderItem, NPIRecord, CAQHProfile, CredentialingDecision
from models.credentialing_models import (
    MarketProductApproval, PSVCheckItem, CredentialingAuditTrail
)


class BusinessRulesAgent:
    """Agent executing credentialing business rules and market line approval logic."""

    NAME = "BusinessRulesAgent"

    def __init__(self, config_path: str = None):
        if not config_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config", "market_lines_config.json")
        self.config_path = config_path
        self.market_lines_config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load business market lines and product rules."""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"market_lines": []}

    def evaluate_decision_and_market_lines(
        self,
        provider: RosterProviderItem,
        npi_record: NPIRecord,
        caqh_profile: CAQHProfile,
        psv_checks: List[PSVCheckItem]
    ) -> Tuple[CredentialingDecision, str, str, bool, List[str], List[MarketProductApproval], List[MarketProductApproval], List[CredentialingAuditTrail]]:
        """
        Evaluate overall credentialing decision and approve/deny specific market lines.
        Returns:
            - overall_decision (CredentialingDecision)
            - decision_summary (str)
            - recred_due_date (str)
            - committee_review_needed (bool)
            - committee_flags (List[str])
            - approved_market_lines (List[MarketProductApproval])
            - rejected_market_lines (List[MarketProductApproval])
            - audit_trail (List[CredentialingAuditTrail])
        """
        audit_trail: List[CredentialingAuditTrail] = []
        committee_flags: List[str] = []

        now = datetime.now()
        # Effective date starts 1st of next month or month after next if late in month
        if now.day > 25:
            # If late in month, effective 1st of month after next (advance 2 months)
            first_of_next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
            next_month = (first_of_next_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        else:
            next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
            
        effective_date_str = next_month.strftime("%Y-%m-%d")
        
        # 36 months / 3-year NCQA credentialing cycle
        exp_year = next_month.year + 3
        try:
            expiration_dt = next_month.replace(year=exp_year)
        except ValueError:
            # Leap year edge case
            expiration_dt = next_month.replace(year=exp_year, day=28)
            
        expiration_date_str = expiration_dt.strftime("%Y-%m-%d")
        recred_due_date_str = (expiration_dt - timedelta(days=90)).strftime("%Y-%m-%d")

        # 1. Check for Hard Disqualifiers (DENIAL)
        failed_checks = [c for c in psv_checks if c.status == "FAIL"]
        if npi_record.deactivated or not npi_record.is_valid:
            committee_flags.append(f"Invalid or Deactivated NPI: {npi_record.status}")
        if caqh_profile.sanction_history:
            committee_flags.append("Sanction history detected in CAQH / OIG / SAM registries")
        
        oig_fail = any(c.source in ("OIG_LEIE", "SAM_GOV") and c.status == "FAIL" for c in psv_checks)
        if oig_fail:
            committee_flags.append("Federal OIG/SAM Exclusion or Debarment")

        lic_fail = any(c.source == "STATE_MEDICAL_BOARD" and c.status == "FAIL" for c in psv_checks)
        if lic_fail:
            committee_flags.append(f"No active unrestricted license in practicing state ({provider.practice_state})")

        # Hard Denial Logic
        if oig_fail or lic_fail or npi_record.deactivated:
            overall_decision = CredentialingDecision.DENIED
            decision_summary = f"Credentialing DENIED due to critical PSV failures: {'; '.join(committee_flags)}."
            committee_review_needed = True
            
            audit_trail.append(CredentialingAuditTrail(
                step_name="CREDENTIALING_DECISION",
                agent_name=self.NAME,
                action_taken="Issued Credentialing DENIAL",
                details=decision_summary,
                status="DENIED"
            ))

            # All requested market lines rejected
            rejected_lines = self._generate_all_rejected_lines(provider, "Provider does not meet baseline credentialing criteria")
            return overall_decision, decision_summary, recred_due_date_str, committee_review_needed, committee_flags, [], rejected_lines, audit_trail

        # 2. Check for Committee Review Triggers
        flagged_checks = [c for c in psv_checks if c.status == "FLAGGED"]
        for c in flagged_checks:
            if "Malpractice" in c.check_name:
                committee_flags.append(f"Malpractice claims history flagged: {c.details}")
            elif "Work History" in c.check_name:
                committee_flags.append(f"Work history gap flagged: {c.details}")

        # 3. Check for Conditional Approval (e.g. Expired CAQH attestation > 120 days)
        caqh_attestation_expired = not caqh_profile.is_attestation_current

        if committee_flags:
            overall_decision = CredentialingDecision.COMMITTEE_REVIEW_REQUIRED
            decision_summary = f"Flagged for Peer Review Credentialing Committee docket: {'; '.join(committee_flags)}"
            committee_review_needed = True
        elif caqh_attestation_expired:
            overall_decision = CredentialingDecision.CONDITIONAL_APPROVAL
            decision_summary = (
                f"CONDITIONAL APPROVAL: Provider credentials satisfy standards, but CAQH attestation is expired "
                f"({caqh_profile.days_since_attestation} days ago). 30-day grace period granted to complete CAQH re-attestation."
            )
            committee_review_needed = False
            committee_flags.append(f"Pending CAQH re-attestation (last attested {caqh_profile.attestation_date})")
        else:
            overall_decision = CredentialingDecision.APPROVED
            decision_summary = "Full Credentialing APPROVAL: All PSV checks passed cleanly. Compliant with NCQA & CMS standards."
            committee_review_needed = False

        # 4. Evaluate Market Lines & Products
        approved_lines: List[MarketProductApproval] = []
        rejected_lines: List[MarketProductApproval] = []

        active_board_certified = any(b.is_active for b in caqh_profile.board_certifications)
        provider_specialty = provider.specialty or npi_record.primary_specialty or "General"
        practice_st = (provider.practice_state or "TX").upper()

        for line in self.market_lines_config.get("market_lines", []):
            line_id = line.get("market_line_id", "")
            line_name = line.get("market_line_name", "")
            req_board = line.get("requires_board_cert", False)
            allowed_specs = line.get("allowed_specialties", ["ALL"])

            # Specialty match check
            spec_matched = ("ALL" in allowed_specs) or any(
                s.lower() in provider_specialty.lower() for s in allowed_specs
            )

            for prod in line.get("products", []):
                prod_code = prod.get("product_code")
                prod_name = prod.get("product_name")
                eligible_states = prod.get("eligible_states", [])
                tier = prod.get("network_tier", "Tier 1 - Standard")

                # State eligibility
                if practice_st not in eligible_states:
                    rejected_lines.append(MarketProductApproval(
                        market_line=line_name,
                        product_name=prod_name,
                        plan_code=prod_code,
                        status="REJECTED",
                        effective_date=effective_date_str,
                        expiration_date=expiration_date_str,
                        recred_due_date=recred_due_date_str,
                        network_tier=tier,
                        specialty_scope=provider_specialty,
                        approval_reason=f"Product not offered in provider practice state ({practice_st})."
                    ))
                    continue

                # Specialty eligibility check
                if not spec_matched:
                    rejected_lines.append(MarketProductApproval(
                        market_line=line_name,
                        product_name=prod_name,
                        plan_code=prod_code,
                        status="REJECTED",
                        effective_date=effective_date_str,
                        expiration_date=expiration_date_str,
                        recred_due_date=recred_due_date_str,
                        network_tier=tier,
                        specialty_scope=provider_specialty,
                        approval_reason=f"Provider specialty '{provider_specialty}' is not eligible for market line '{line_name}'."
                    ))
                    continue

                # Board cert rule for line (e.g., Medicare Advantage)
                if req_board and not active_board_certified:
                    rejected_lines.append(MarketProductApproval(
                        market_line=line_name,
                        product_name=prod_name,
                        plan_code=prod_code,
                        status="REJECTED",
                        effective_date=effective_date_str,
                        expiration_date=expiration_date_str,
                        recred_due_date=recred_due_date_str,
                        network_tier=tier,
                        specialty_scope=provider_specialty,
                        approval_reason="Requires active Board Certification in specialty for Medicare Advantage participation."
                    ))
                    continue

                # Overall credentialing status gating
                if overall_decision == CredentialingDecision.DENIED:
                    status_str = "REJECTED"
                    reason_str = "Denied at provider credentialing level"
                    rejected_lines.append(MarketProductApproval(
                        market_line=line_name,
                        product_name=prod_name,
                        plan_code=prod_code,
                        status=status_str,
                        effective_date=effective_date_str,
                        expiration_date=expiration_date_str,
                        recred_due_date=recred_due_date_str,
                        network_tier=tier,
                        specialty_scope=provider_specialty,
                        approval_reason=reason_str
                    ))
                elif overall_decision == CredentialingDecision.CONDITIONAL_APPROVAL:
                    status_str = "CONDITIONAL"
                    reason_str = "Approved conditionally pending CAQH re-attestation within 30 days"
                    approved_lines.append(MarketProductApproval(
                        market_line=line_name,
                        product_name=prod_name,
                        plan_code=prod_code,
                        status=status_str,
                        effective_date=effective_date_str,
                        expiration_date=expiration_date_str,
                        recred_due_date=recred_due_date_str,
                        network_tier=tier,
                        specialty_scope=provider_specialty,
                        approval_reason=reason_str
                    ))
                elif overall_decision == CredentialingDecision.COMMITTEE_REVIEW_REQUIRED:
                    status_str = "PENDING_COMMITTEE"
                    reason_str = "Recommended for approval pending formal Credentialing Committee review"
                    approved_lines.append(MarketProductApproval(
                        market_line=line_name,
                        product_name=prod_name,
                        plan_code=prod_code,
                        status=status_str,
                        effective_date=effective_date_str,
                        expiration_date=expiration_date_str,
                        recred_due_date=recred_due_date_str,
                        network_tier=tier,
                        specialty_scope=provider_specialty,
                        approval_reason=reason_str
                    ))
                else:
                    status_str = "APPROVED"
                    reason_str = "Approved for business participation. Network tier assigned."
                    approved_lines.append(MarketProductApproval(
                        market_line=line_name,
                        product_name=prod_name,
                        plan_code=prod_code,
                        status=status_str,
                        effective_date=effective_date_str,
                        expiration_date=expiration_date_str,
                        recred_due_date=recred_due_date_str,
                        network_tier=tier,
                        specialty_scope=provider_specialty,
                        approval_reason=reason_str
                    ))

        audit_trail.append(CredentialingAuditTrail(
            step_name="MARKET_LINES_EVALUATION",
            agent_name=self.NAME,
            action_taken=f"Evaluated market lines for {provider.first_name} {provider.last_name}",
            details=f"Approved lines: {len(approved_lines)}, Rejected lines: {len(rejected_lines)}. Effective: {effective_date_str}, Exp: {expiration_date_str}",
            status="SUCCESS"
        ))

        return (
            overall_decision,
            decision_summary,
            recred_due_date_str,
            committee_review_needed,
            committee_flags,
            approved_lines,
            rejected_lines,
            audit_trail
        )

    def _generate_all_rejected_lines(self, provider: RosterProviderItem, reason: str) -> List[MarketProductApproval]:
        """Generate rejected entries when overall decision is DENIED."""
        rejected = []
        for line in self.market_lines_config.get("market_lines", []):
            line_name = line.get("market_line_name", "")
            for prod in line.get("products", []):
                rejected.append(MarketProductApproval(
                    market_line=line_name,
                    product_name=prod.get("product_name"),
                    plan_code=prod.get("product_code"),
                    status="REJECTED",
                    effective_date="N/A",
                    expiration_date="N/A",
                    recred_due_date="N/A",
                    network_tier="None",
                    specialty_scope=provider.specialty or "General",
                    approval_reason=reason
                ))
        return rejected
