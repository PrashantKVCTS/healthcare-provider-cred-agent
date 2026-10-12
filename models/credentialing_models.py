"""
Credentialing approval, market lines, and validation result models.
Compatible with Appian CDTs and standard healthcare credentialing workflows.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from models.provider_models import CredentialingDecision, NPIRecord, CAQHProfile


class MarketProductApproval(BaseModel):
    market_line: str  # e.g., "Commercial", "Medicare Advantage", "Medicaid Managed Care", "ACA Exchange"
    product_name: str  # e.g., "Commercial HMO Choice", "MA Premier PPO", "Medicaid Star"
    plan_code: str
    status: str = "APPROVED"  # APPROVED, CONDITIONAL, REJECTED, EXCLUDED_BY_MARKET
    effective_date: str
    expiration_date: str
    recred_due_date: str
    network_tier: str = "Tier 1 - Preferred"
    specialty_scope: str = "Primary Care"
    approval_reason: str = "Meets all NCQA PSV and business network requirements"


class PSVCheckItem(BaseModel):
    check_name: str
    source: str  # "NPPES_API", "CAQH_PROVIEW", "OIG_LEIE", "SAM_GOV", "STATE_MEDICAL_BOARD"
    status: str  # "PASS", "FAIL", "FLAGGED", "WARNING"
    details: str
    verified_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CredentialingAuditTrail(BaseModel):
    step_name: str
    agent_name: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    action_taken: str
    details: str
    status: str = "SUCCESS"


class ProviderCredentialingResult(BaseModel):
    npi: str
    provider_name: str
    caqh_id: Optional[str] = None
    overall_decision: CredentialingDecision
    decision_summary: str
    decision_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    recredentialing_due_date: str
    # Committee review and human decision overrides
    committee_review_needed: bool = False
    committee_flags: List[str] = Field(default_factory=list)
    committee_decision: Optional[str] = None  # e.g. "APPROVED", "CONDITIONAL_APPROVAL", "DENIED", "DEFERRED"
    committee_notes: Optional[str] = None
    committee_reviewer: Optional[str] = None
    committee_signed_at: Optional[str] = None
    committee_stipulations: List[str] = Field(default_factory=list)

    # PSV verification checks
    psv_checks: List[PSVCheckItem] = Field(default_factory=list)

    # Approved Market Lines with dates & products
    approved_market_lines: List[MarketProductApproval] = Field(default_factory=list)
    rejected_market_lines: List[MarketProductApproval] = Field(default_factory=list)

    # Captured provider credentialing profiles
    npi_profile: Optional[NPIRecord] = None
    caqh_profile: Optional[CAQHProfile] = None

    # Education & work history captured
    education_summary: List[Dict[str, Any]] = Field(default_factory=list)
    work_history_summary: List[Dict[str, Any]] = Field(default_factory=list)
    licenses_summary: List[Dict[str, Any]] = Field(default_factory=list)
    board_certifications: List[str] = Field(default_factory=list)

    # Agent execution trace
    audit_trail: List[CredentialingAuditTrail] = Field(default_factory=list)

    # Appian specific fields
    appian_case_id: Optional[str] = None
    ready_for_pdm_contracting: bool = True


class BatchRosterResult(BaseModel):
    batch_id: str
    filename: Optional[str] = "roster.csv"
    processed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_providers: int = 0
    approved_count: int = 0
    conditional_count: int = 0
    committee_review_count: int = 0
    denied_count: int = 0
    results: List[ProviderCredentialingResult] = Field(default_factory=list)
