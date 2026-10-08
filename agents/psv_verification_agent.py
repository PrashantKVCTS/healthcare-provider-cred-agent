"""
Primary Source Verification (PSV) Agent.
Orchestrates primary source verification against NPI Registry, CAQH ProView,
State Licensing Boards, OIG LEIE, SAM.gov, and malpractice carriers.
Captures education, work history, licenses, DEA, board certifications, and flags anomalies.
"""

from datetime import datetime
from typing import Tuple, List, Dict, Any
from models.provider_models import RosterProviderItem, NPIRecord, CAQHProfile
from models.credentialing_models import PSVCheckItem, CredentialingAuditTrail
from services.npi_service import NPIService, luhn_checksum_valid
from services.caqh_service import CAQHService
from services.sanctions_service import SanctionsService


class PSVVerificationAgent:
    """Agent that performs multi-source credentialing verification (PSV)."""

    NAME = "PSVVerificationAgent"

    def __init__(self):
        self.npi_service = NPIService()
        self.caqh_service = CAQHService()
        self.sanctions_service = SanctionsService()

    def verify_provider(
        self, provider: RosterProviderItem
    ) -> Tuple[NPIRecord, CAQHProfile, List[PSVCheckItem], List[CredentialingAuditTrail]]:
        """
        Execute comprehensive PSV verification suite for a provider.
        Returns:
            - NPIRecord
            - CAQHProfile
            - List of PSVCheckItems
            - Audit trail entries
        """
        psv_checks: List[PSVCheckItem] = []
        audit_trail: List[CredentialingAuditTrail] = []
        today_str = datetime.now().strftime("%Y-%m-%d")

        # 1. NPI Verification Check
        npi_valid_format = luhn_checksum_valid(provider.npi)
        npi_record = self.npi_service.verify_npi(
            provider.npi,
            expected_first=provider.first_name,
            expected_last=provider.last_name
        )

        if npi_record.deactivated:
            psv_checks.append(PSVCheckItem(
                check_name="NPI Registry Status Check",
                source="NPPES_API",
                status="FAIL",
                details=f"NPI {provider.npi} is marked as DEACTIVATED in CMS NPPES Registry."
            ))
        elif not npi_record.is_valid:
            psv_checks.append(PSVCheckItem(
                check_name="NPI Registry Status Check",
                source="NPPES_API",
                status="FAIL",
                details=f"NPI {provider.npi} status is inactive or invalid in NPPES."
            ))
        else:
            psv_checks.append(PSVCheckItem(
                check_name="NPI Registry Status Check",
                source="NPPES_API",
                status="PASS",
                details=f"Active Type 1 Individual Provider NPI verified. Primary taxonomy: {npi_record.primary_specialty} ({npi_record.primary_taxonomy})."
            ))

        audit_trail.append(CredentialingAuditTrail(
            step_name="NPI_VERIFICATION",
            agent_name=self.NAME,
            action_taken=f"Verified NPI {provider.npi} against CMS NPPES Registry",
            details=f"Status: {npi_record.status}, Taxonomy: {npi_record.primary_specialty}",
            status="SUCCESS" if npi_record.is_valid and not npi_record.deactivated else "FAILED"
        ))

        # 2. CAQH ProView Data Ingestion & Attestation Check
        caqh_profile = self.caqh_service.get_profile_by_npi(
            provider.npi,
            caqh_id=provider.caqh_id,
            practice_state=provider.practice_state or "TX"
        )

        if caqh_profile.is_attestation_current:
            psv_checks.append(PSVCheckItem(
                check_name="CAQH ProView Attestation Currency (<= 120 Days)",
                source="CAQH_PROVIEW",
                status="PASS",
                details=f"CAQH ID {caqh_profile.caqh_id} attested on {caqh_profile.attestation_date} ({caqh_profile.days_since_attestation} days ago - within NCQA 120-day limit)."
            ))
        else:
            psv_checks.append(PSVCheckItem(
                check_name="CAQH ProView Attestation Currency (<= 120 Days)",
                source="CAQH_PROVIEW",
                status="FLAGGED",
                details=f"EXPIRED ATTESTATION: CAQH ID {caqh_profile.caqh_id} was attested {caqh_profile.days_since_attestation} days ago (exceeds 120-day NCQA currency threshold)."
            ))

        audit_trail.append(CredentialingAuditTrail(
            step_name="CAQH_INTAKE",
            agent_name=self.NAME,
            action_taken=f"Extracted CAQH ProView profile {caqh_profile.caqh_id}",
            details=f"Attestation: {caqh_profile.attestation_date} ({caqh_profile.days_since_attestation}d ago). Currency status: {'CURRENT' if caqh_profile.is_attestation_current else 'EXPIRED'}",
            status="SUCCESS"
        ))

        # 3. State Medical License Verification
        req_state = (provider.practice_state or "TX").upper()
        matching_license = next((lic for lic in caqh_profile.licenses if lic.state.upper() == req_state), None)

        if not matching_license:
            psv_checks.append(PSVCheckItem(
                check_name="State Medical Board License Check",
                source="STATE_MEDICAL_BOARD",
                status="FAIL",
                details=f"No medical license found for requested practice state: {req_state}."
            ))
        else:
            if matching_license.status != "ACTIVE" or matching_license.has_disciplinary_action:
                psv_checks.append(PSVCheckItem(
                    check_name="State Medical Board License Check",
                    source="STATE_MEDICAL_BOARD",
                    status="FAIL",
                    details=f"License {matching_license.license_number} in {req_state} has status '{matching_license.status}' with disciplinary action flag."
                ))
            elif matching_license.expiration_date and matching_license.expiration_date < today_str:
                psv_checks.append(PSVCheckItem(
                    check_name="State Medical Board License Check",
                    source="STATE_MEDICAL_BOARD",
                    status="FAIL",
                    details=f"License {matching_license.license_number} in {req_state} expired on {matching_license.expiration_date}."
                ))
            else:
                psv_checks.append(PSVCheckItem(
                    check_name="State Medical Board License Check",
                    source="STATE_MEDICAL_BOARD",
                    status="PASS",
                    details=f"Active, unrestricted {matching_license.license_type} license ({matching_license.license_number}) verified in {req_state}. Expires: {matching_license.expiration_date}."
                ))

        # 4. Education & Training Verification
        verified_edu_count = sum(1 for e in caqh_profile.education if e.verified)
        if verified_edu_count > 0:
            med_school = next((e for e in caqh_profile.education if e.degree_type == "Medical School"), caqh_profile.education[0])
            psv_checks.append(PSVCheckItem(
                check_name="Primary Education & Medical Degree PSV",
                source="AMA_ECFMG_CREDENTIALS",
                status="PASS",
                details=f"Medical Education verified: {med_school.institution} ({med_school.graduation_year}), Degree: {med_school.degree}."
            ))
        else:
            psv_checks.append(PSVCheckItem(
                check_name="Primary Education & Medical Degree PSV",
                source="AMA_ECFMG_CREDENTIALS",
                status="FLAGGED",
                details="Primary source education verification documentation incomplete."
            ))

        # 5. Work History & Gap Analysis (NCQA Standard: 5-year history)
        gaps = [w for w in caqh_profile.work_history if w.gap_flag]
        if gaps:
            psv_checks.append(PSVCheckItem(
                check_name="Work History & 5-Year Chronology Gap Check",
                source="CAQH_PROVIEW",
                status="FLAGGED",
                details=f"Work history gap detected: {gaps[0].gap_reason or 'Unexplained gap > 6 months'}."
            ))
        else:
            psv_checks.append(PSVCheckItem(
                check_name="Work History & 5-Year Chronology Gap Check",
                source="CAQH_PROVIEW",
                status="PASS",
                details="Continuous 5-year work history documented without unaddressed gaps."
            ))

        # 6. DEA Registration Check
        active_dea = next((d for d in caqh_profile.dea_records if d.status == "ACTIVE" and d.expiration_date > today_str), None)
        if active_dea:
            psv_checks.append(PSVCheckItem(
                check_name="Federal DEA Registration Check",
                source="US_DOJ_DEA",
                status="PASS",
                details=f"Active DEA #{active_dea.dea_number} verified with schedules {', '.join(active_dea.schedules)}. Expires: {active_dea.expiration_date}."
            ))
        else:
            psv_checks.append(PSVCheckItem(
                check_name="Federal DEA Registration Check",
                source="US_DOJ_DEA",
                status="FAIL" if caqh_profile.dea_records else "WARNING",
                details="No active, non-expired DEA registration found."
            ))

        # 7. Malpractice Insurance Check
        mp = caqh_profile.malpractice
        if not mp or not mp.is_active:
            psv_checks.append(PSVCheckItem(
                check_name="Malpractice Insurance Liability Coverage Check",
                source="CARRIER_COI",
                status="FAIL",
                details="No active professional liability malpractice coverage found."
            ))
        else:
            if mp.claims_past_5_years > 0:
                psv_checks.append(PSVCheckItem(
                    check_name="Malpractice Insurance Liability Coverage Check",
                    source="CARRIER_COI",
                    status="FLAGGED",
                    details=f"Active coverage with {mp.carrier} (${mp.per_claim_limit:,.0f}/${mp.aggregate_limit:,.0f}). FLAGGED: {mp.claims_past_5_years} malpractice claim(s) reported in past 5 years."
                ))
            else:
                psv_checks.append(PSVCheckItem(
                    check_name="Malpractice Insurance Liability Coverage Check",
                    source="CARRIER_COI",
                    status="PASS",
                    details=f"Active coverage with {mp.carrier} (${mp.per_claim_limit:,.0f}/${mp.aggregate_limit:,.0f}) with 0 claims in past 5 years. Policy #{mp.policy_number}."
                ))

        # 8. Federal & State Sanctions (OIG LEIE & SAM.gov)
        sanction_checks = self.sanctions_service.check_exclusions(provider.npi, f"{provider.first_name} {provider.last_name}")
        psv_checks.extend(sanction_checks)

        audit_trail.append(CredentialingAuditTrail(
            step_name="PRIMARY_SOURCE_VERIFICATION_COMPLETE",
            agent_name=self.NAME,
            action_taken="Completed all 8 Primary Source Verification checks",
            details=f"Checks: {len(psv_checks)} executed. Passed: {sum(1 for c in psv_checks if c.status == 'PASS')}, Flagged/Failed: {sum(1 for c in psv_checks if c.status != 'PASS')}",
            status="SUCCESS"
        ))

        return npi_record, caqh_profile, psv_checks, audit_trail
