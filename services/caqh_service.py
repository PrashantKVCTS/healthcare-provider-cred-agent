"""
CAQH ProView Integration Service.
Simulates CAQH ProView data extraction including 120-day attestation currency,
education, work history, state medical licenses, DEA, board certifications, and malpractice history.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from models.provider_models import (
    CAQHProfile, EducationRecord, WorkHistoryItem,
    StateLicense, BoardCertification, MalpracticePolicy, DEARecord
)


class CAQHService:
    """Service to query and extract CAQH ProView credentialing profiles."""

    def __init__(self):
        # Current date baseline
        self.today = datetime.now().date()

    def get_profile_by_npi(self, npi: str, caqh_id: Optional[str] = None, practice_state: str = "TX") -> CAQHProfile:
        """Fetch CAQH profile. Returns rich structured credentialing profile."""
        
        # Test Case 1: SARAH CONNER - Clean Provider (Family Medicine)
        if npi == "1234567893":
            attestation_dt = self.today - timedelta(days=22)
            return CAQHProfile(
                caqh_id=caqh_id or "14892011",
                npi=npi,
                attestation_date=attestation_dt.strftime("%Y-%m-%d"),
                is_attestation_current=True,
                days_since_attestation=22,
                education=[
                    EducationRecord(
                        degree="M.D.",
                        institution="University of Texas Southwestern Medical Center",
                        graduation_year=2012,
                        degree_type="Medical School",
                        verified=True
                    ),
                    EducationRecord(
                        degree="Residency",
                        institution="Baylor College of Medicine",
                        graduation_year=2015,
                        degree_type="Residency",
                        verified=True
                    )
                ],
                work_history=[
                    WorkHistoryItem(
                        organization="Austin Community Health Network",
                        position="Attending Physician - Family Medicine",
                        start_date="2015-08-01",
                        end_date="Present",
                        current=True,
                        gap_flag=False
                    )
                ],
                licenses=[
                    StateLicense(
                        state="TX",
                        license_number="MD-TX-984210",
                        license_type="MD",
                        issue_date="2015-05-10",
                        expiration_date=(self.today + timedelta(days=580)).strftime("%Y-%m-%d"),
                        status="ACTIVE",
                        has_disciplinary_action=False
                    )
                ],
                specialties=["Family Medicine", "Primary Care"],
                board_certifications=[
                    BoardCertification(
                        specialty="Family Medicine",
                        board_name="American Board of Family Medicine (ABFM)",
                        certified_date="2015-09-01",
                        recertified_date="2025-09-01",
                        expiration_date=(self.today + timedelta(days=730)).strftime("%Y-%m-%d"),
                        is_active=True
                    )
                ],
                dea_records=[
                    DEARecord(
                        dea_number="BC1928374",
                        schedules=["2", "2N", "3", "3N", "4", "5"],
                        expiration_date=(self.today + timedelta(days=400)).strftime("%Y-%m-%d"),
                        status="ACTIVE"
                    )
                ],
                malpractice=MalpracticePolicy(
                    carrier="The Doctors Company",
                    policy_number="TDC-992144-TX",
                    per_claim_limit=1000000.0,
                    aggregate_limit=3000000.0,
                    effective_date=(self.today - timedelta(days=180)).strftime("%Y-%m-%d"),
                    expiration_date=(self.today + timedelta(days=185)).strftime("%Y-%m-%d"),
                    is_active=True,
                    claims_past_5_years=0
                ),
                sanction_history=False,
                disclosure_adverse_actions=False
            )

        # Test Case 2: ROBERT CHEN - Internal Medicine with Expired CAQH Attestation (> 120 days)
        if npi == "1987654321":
            attestation_dt = self.today - timedelta(days=145)  # EXPIRED ATTESTATION!
            return CAQHProfile(
                caqh_id=caqh_id or "15983022",
                npi=npi,
                attestation_date=attestation_dt.strftime("%Y-%m-%d"),
                is_attestation_current=False,
                days_since_attestation=145,
                education=[
                    EducationRecord(
                        degree="M.D.",
                        institution="Johns Hopkins University School of Medicine",
                        graduation_year=2008,
                        degree_type="Medical School",
                        verified=True
                    ),
                    EducationRecord(
                        degree="Residency",
                        institution="Duke University Hospital",
                        graduation_year=2011,
                        degree_type="Residency",
                        verified=True
                    )
                ],
                work_history=[
                    WorkHistoryItem(
                        organization="Dallas Internal Medicine Specialists",
                        position="Senior Internist",
                        start_date="2011-09-01",
                        end_date="Present",
                        current=True,
                        gap_flag=False
                    )
                ],
                licenses=[
                    StateLicense(
                        state="TX",
                        license_number="MD-TX-448102",
                        license_type="MD",
                        issue_date="2011-06-15",
                        expiration_date=(self.today + timedelta(days=450)).strftime("%Y-%m-%d"),
                        status="ACTIVE",
                        has_disciplinary_action=False
                    )
                ],
                specialties=["Internal Medicine", "Adult Gerontology"],
                board_certifications=[
                    BoardCertification(
                        specialty="Internal Medicine",
                        board_name="American Board of Internal Medicine (ABIM)",
                        certified_date="2011-10-15",
                        recertified_date="2021-10-15",
                        expiration_date=(self.today + timedelta(days=600)).strftime("%Y-%m-%d"),
                        is_active=True
                    )
                ],
                dea_records=[
                    DEARecord(
                        dea_number="FC9821435",
                        schedules=["2", "2N", "3", "3N", "4", "5"],
                        expiration_date=(self.today + timedelta(days=320)).strftime("%Y-%m-%d"),
                        status="ACTIVE"
                    )
                ],
                malpractice=MalpracticePolicy(
                    carrier="Medical Protective (MedPro)",
                    policy_number="MP-559102-TX",
                    per_claim_limit=1000000.0,
                    aggregate_limit=3000000.0,
                    effective_date=(self.today - timedelta(days=90)).strftime("%Y-%m-%d"),
                    expiration_date=(self.today + timedelta(days=275)).strftime("%Y-%m-%d"),
                    is_active=True,
                    claims_past_5_years=0
                ),
                sanction_history=False,
                disclosure_adverse_actions=False
            )

        # Test Case 3: EMILY WATSON - Orthopedic Surgery with Recent Malpractice Settlement (Flagged for Committee)
        if npi == "1457896325":
            attestation_dt = self.today - timedelta(days=15)
            return CAQHProfile(
                caqh_id=caqh_id or "16744033",
                npi=npi,
                attestation_date=attestation_dt.strftime("%Y-%m-%d"),
                is_attestation_current=True,
                days_since_attestation=15,
                education=[
                    EducationRecord(
                        degree="D.O.",
                        institution="Nova Southeastern University College of Osteopathic Medicine",
                        graduation_year=2014,
                        degree_type="Medical School",
                        verified=True
                    ),
                    EducationRecord(
                        degree="Residency",
                        institution="University of Miami / Jackson Memorial Hospital",
                        graduation_year=2019,
                        degree_type="Residency",
                        verified=True
                    )
                ],
                work_history=[
                    WorkHistoryItem(
                        organization="Biscayne Orthopedics Group",
                        position="Orthopedic Surgeon",
                        start_date="2019-08-01",
                        end_date="Present",
                        current=True,
                        gap_flag=False
                    )
                ],
                licenses=[
                    StateLicense(
                        state="FL",
                        license_number="DO-FL-881204",
                        license_type="DO",
                        issue_date="2019-07-01",
                        expiration_date=(self.today + timedelta(days=390)).strftime("%Y-%m-%d"),
                        status="ACTIVE",
                        has_disciplinary_action=False
                    )
                ],
                specialties=["Orthopedic Surgery"],
                board_certifications=[
                    BoardCertification(
                        specialty="Orthopedic Surgery",
                        board_name="American Osteopathic Board of Orthopedic Surgery",
                        certified_date="2020-05-12",
                        expiration_date=(self.today + timedelta(days=800)).strftime("%Y-%m-%d"),
                        is_active=True
                    )
                ],
                dea_records=[
                    DEARecord(
                        dea_number="BW7711223",
                        schedules=["2", "2N", "3", "3N", "4", "5"],
                        expiration_date=(self.today + timedelta(days=510)).strftime("%Y-%m-%d"),
                        status="ACTIVE"
                    )
                ],
                malpractice=MalpracticePolicy(
                    carrier="NORCAL Group",
                    policy_number="NC-884011-FL",
                    per_claim_limit=1000000.0,
                    aggregate_limit=3000000.0,
                    effective_date=(self.today - timedelta(days=120)).strftime("%Y-%m-%d"),
                    expiration_date=(self.today + timedelta(days=245)).strftime("%Y-%m-%d"),
                    is_active=True,
                    claims_past_5_years=2  # Malpractice claims flagged!
                ),
                sanction_history=False,
                disclosure_adverse_actions=False
            )

        # Test Case 4: MARCUS VANCE - Disciplinary Board Action / License Sanction (DENIAL CASE)
        if npi == "1122334455":
            attestation_dt = self.today - timedelta(days=40)
            return CAQHProfile(
                caqh_id=caqh_id or "11229988",
                npi=npi,
                attestation_date=attestation_dt.strftime("%Y-%m-%d"),
                is_attestation_current=True,
                days_since_attestation=40,
                education=[
                    EducationRecord(
                        degree="M.D.",
                        institution="Midwest University of Health",
                        graduation_year=2004,
                        degree_type="Medical School",
                        verified=True
                    )
                ],
                work_history=[
                    WorkHistoryItem(
                        organization="Private Cardiology Clinic",
                        position="Cardiologist",
                        start_date="2008-01-01",
                        end_date="2024-02-15",
                        current=False,
                        gap_flag=True,
                        gap_reason="License suspension under administrative board investigation"
                    )
                ],
                licenses=[
                    StateLicense(
                        state="TX",
                        license_number="MD-TX-109283",
                        license_type="MD",
                        issue_date="2008-05-10",
                        expiration_date=(self.today - timedelta(days=30)).strftime("%Y-%m-%d"),  # EXPIRED LICENSE!
                        status="SUSPENDED",
                        has_disciplinary_action=True
                    )
                ],
                specialties=["Cardiology"],
                board_certifications=[
                    BoardCertification(
                        specialty="Cardiology",
                        board_name="American Board of Internal Medicine",
                        is_active=False
                    )
                ],
                dea_records=[
                    DEARecord(
                        dea_number="MV1122334",
                        schedules=["2", "3"],
                        expiration_date=(self.today - timedelta(days=90)).strftime("%Y-%m-%d"),
                        status="REVOKED"
                    )
                ],
                malpractice=None,
                sanction_history=True,
                disclosure_adverse_actions=True
            )

        # Default dynamic generator for arbitrary providers
        attestation_dt = self.today - timedelta(days=30)
        return CAQHProfile(
            caqh_id=caqh_id or f"9{npi[-7:]}",
            npi=npi,
            attestation_date=attestation_dt.strftime("%Y-%m-%d"),
            is_attestation_current=True,
            days_since_attestation=30,
            education=[
                EducationRecord(
                    degree="M.D.",
                    institution="State Health Science Center",
                    graduation_year=2013,
                    degree_type="Medical School",
                    verified=True
                ),
                EducationRecord(
                    degree="Residency",
                    institution="Metro Academic Health System",
                    graduation_year=2016,
                    degree_type="Residency",
                    verified=True
                )
            ],
            work_history=[
                WorkHistoryItem(
                    organization="Regional Healthcare Partners",
                    position="Staff Physician",
                    start_date="2016-08-01",
                    end_date="Present",
                    current=True,
                    gap_flag=False
                )
            ],
            licenses=[
                StateLicense(
                    state=practice_state or "TX",
                    license_number=f"MD-{practice_state}-847291",
                    license_type="MD",
                    issue_date="2016-06-01",
                    expiration_date=(self.today + timedelta(days=500)).strftime("%Y-%m-%d"),
                    status="ACTIVE",
                    has_disciplinary_action=False
                )
            ],
            specialties=["Internal Medicine"],
            board_certifications=[
                BoardCertification(
                    specialty="Internal Medicine",
                    board_name="American Board of Internal Medicine (ABIM)",
                    certified_date="2016-10-01",
                    expiration_date=(self.today + timedelta(days=650)).strftime("%Y-%m-%d"),
                    is_active=True
                )
            ],
            dea_records=[
                DEARecord(
                    dea_number=f"AB{npi[-7:]}",
                    schedules=["2", "2N", "3", "3N", "4", "5"],
                    expiration_date=(self.today + timedelta(days=420)).strftime("%Y-%m-%d"),
                    status="ACTIVE"
                )
            ],
            malpractice=MalpracticePolicy(
                carrier="ProAssurance Group",
                policy_number=f"PA-{npi[-6:]}-POL",
                per_claim_limit=1000000.0,
                aggregate_limit=3000000.0,
                effective_date=(self.today - timedelta(days=100)).strftime("%Y-%m-%d"),
                expiration_date=(self.today + timedelta(days=265)).strftime("%Y-%m-%d"),
                is_active=True,
                claims_past_5_years=0
            ),
            sanction_history=False,
            disclosure_adverse_actions=False
        )
