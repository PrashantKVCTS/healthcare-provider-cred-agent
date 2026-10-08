"""
Sanctions, Exclusions, and Disciplinary Verification Service.
Simulates Primary Source Verification against OIG LEIE, SAM.gov, and State Disciplinary Boards.
"""

from typing import Dict, Any, List
from models.credentialing_models import PSVCheckItem


class SanctionsService:
    """Service to verify provider against Federal & State exclusion lists."""

    # Explicit list of excluded NPIs for simulation
    EXCLUDED_NPIS = {
        "1122334455": {
            "source": "OIG_LEIE",
            "exclusion_type": "1128(a)(1) - Mandatory Exclusion",
            "exclusion_date": "2024-03-20",
            "reason": "Conviction of program-related crimes (healthcare fraud)"
        }
    }

    def check_exclusions(self, npi: str, provider_name: str) -> List[PSVCheckItem]:
        """Check OIG LEIE and SAM.gov databases."""
        checks = []

        if npi in self.EXCLUDED_NPIS:
            record = self.EXCLUDED_NPIS[npi]
            checks.append(PSVCheckItem(
                check_name="Federal OIG LEIE Exclusion Check",
                source="OIG_LEIE",
                status="FAIL",
                details=f"EXCLUSION FOUND: {record['exclusion_type']} on {record['exclusion_date']}. Reason: {record['reason']}"
            ))
            checks.append(PSVCheckItem(
                check_name="Federal SAM.gov Debarment Check",
                source="SAM_GOV",
                status="FAIL",
                details="ACTIVE DEBARMENT: Provider excluded from federal healthcare contracting."
            ))
        else:
            checks.append(PSVCheckItem(
                check_name="Federal OIG LEIE Exclusion Check",
                source="OIG_LEIE",
                status="PASS",
                details=f"No exclusion records found in OIG LEIE for NPI {npi} ({provider_name})."
            ))
            checks.append(PSVCheckItem(
                check_name="Federal SAM.gov Debarment Check",
                source="SAM_GOV",
                status="PASS",
                details=f"No active exclusions or debarments found in SAM.gov for NPI {npi}."
            ))

        return checks
