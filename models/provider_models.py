"""
Data models for Provider Credentialing.
Defines schemas for roster intake, NPI registry data, CAQH ProView data,
and comprehensive provider profiles.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import date, datetime
from enum import Enum


class ProviderStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"
    SUSPENDED = "SUSPENDED"


class CredentialingDecision(str, Enum):
    APPROVED = "APPROVED"
    CONDITIONAL_APPROVAL = "CONDITIONAL_APPROVAL"
    COMMITTEE_REVIEW_REQUIRED = "COMMITTEE_REVIEW_REQUIRED"
    DENIED = "DENIED"


class StateLicense(BaseModel):
    state: str
    license_number: str
    license_type: str = "MD"
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None
    status: str = "ACTIVE"
    has_disciplinary_action: bool = False


class EducationRecord(BaseModel):
    degree: str  # MD, DO, NP, PA, etc.
    institution: str
    graduation_year: int
    degree_type: str = "Medical School"  # Medical School, Residency, Fellowship
    verified: bool = True


class WorkHistoryItem(BaseModel):
    organization: str
    position: str
    start_date: str
    end_date: Optional[str] = "Present"
    current: bool = True
    gap_flag: bool = False
    gap_reason: Optional[str] = None


class BoardCertification(BaseModel):
    specialty: str
    board_name: str
    certified_date: Optional[str] = None
    recertified_date: Optional[str] = None
    expiration_date: Optional[str] = None
    is_active: bool = True


class MalpracticePolicy(BaseModel):
    carrier: str
    policy_number: str
    per_claim_limit: float = 1000000.0  # $1,000,000
    aggregate_limit: float = 3000000.0   # $3,000,000
    effective_date: str
    expiration_date: str
    is_active: bool = True
    claims_past_5_years: int = 0


class DEARecord(BaseModel):
    dea_number: str
    schedules: List[str] = Field(default_factory=lambda: ["2", "2N", "3", "3N", "4", "5"])
    expiration_date: str
    status: str = "ACTIVE"


class CAQHProfile(BaseModel):
    caqh_id: str
    npi: str
    attestation_date: str
    is_attestation_current: bool = True  # Within 120 days
    days_since_attestation: int = 25
    education: List[EducationRecord] = Field(default_factory=list)
    work_history: List[WorkHistoryItem] = Field(default_factory=list)
    licenses: List[StateLicense] = Field(default_factory=list)
    specialties: List[str] = Field(default_factory=list)
    board_certifications: List[BoardCertification] = Field(default_factory=list)
    dea_records: List[DEARecord] = Field(default_factory=list)
    malpractice: Optional[MalpracticePolicy] = None
    sanction_history: bool = False
    disclosure_adverse_actions: bool = False


class NPIRecord(BaseModel):
    npi: str
    enumeration_type: str = "NPI-1"  # Individual
    first_name: str
    last_name: str
    middle_name: Optional[str] = ""
    credential: Optional[str] = "M.D."
    gender: Optional[str] = "M"
    sole_proprietor: Optional[str] = "NO"
    status: str = "A"  # Active
    enumeration_date: Optional[str] = None
    last_updated: Optional[str] = None
    primary_taxonomy: Optional[str] = None
    primary_specialty: Optional[str] = None
    practice_address_state: Optional[str] = None
    practice_address_city: Optional[str] = None
    practice_address_line1: Optional[str] = None
    practice_phone: Optional[str] = None
    is_valid: bool = True
    deactivated: bool = False


class RosterProviderItem(BaseModel):
    """Raw provider line from roster file"""
    npi: str
    first_name: str
    last_name: str
    caqh_id: Optional[str] = None
    tin: Optional[str] = None
    group_name: Optional[str] = None
    specialty: Optional[str] = None
    practice_state: Optional[str] = "TX"
    requested_products: List[str] = Field(default_factory=lambda: ["Commercial HMO", "Commercial PPO", "Medicare Advantage", "Medicaid"])
    roster_submission_date: Optional[str] = None
