"""
CLI Runner for Provider Credentialing Approval Agent.
Allows running credentialing validation over a roster file (CSV/JSON) or individual NPI.
Outputs formatted executive summary and committee docket.
"""

import argparse
import sys
import os
import json

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agents.credentialing_orchestrator import CredentialingOrchestrator
from models.provider_models import RosterProviderItem


def print_banner():
    print("=" * 80)
    print(" HEALTHCARE PROVIDER CREDENTIALING APPROVAL AGENTIC SYSTEM")
    print(" Primary Source Verification (NPI & CAQH) | Market Lines | Appian Ready")
    print("=" * 80)


def print_provider_result(res):
    print(f"\n" + "-" * 75)
    status_icon = {
        "APPROVED": "[APPROVED] [OK]",
        "CONDITIONAL_APPROVAL": "[CONDITIONAL APPROVAL] [!]",
        "COMMITTEE_REVIEW_REQUIRED": "[COMMITTEE REVIEW REQUIRED] [?]",
        "DENIED": "[DENIED] [X]"
    }.get(res.overall_decision.value, res.overall_decision.value)

    print(f"PROVIDER: {res.provider_name} | NPI: {res.npi} | CAQH ID: {res.caqh_id or 'N/A'}")
    print(f"CASE ID:  {res.appian_case_id} | DECISION: {status_icon}")
    print(f"SUMMARY:  {res.decision_summary}")
    print(f"RE-CREDENTIALING DUE: {res.recredentialing_due_date}")

    if res.committee_flags:
        print("\n  ⚠️ Flags / Action Items:")
        for flag in res.committee_flags:
            print(f"    - {flag}")

    print("\n  📋 Primary Source Verification (PSV) Highlights:")
    for check in res.psv_checks:
        check_icon = "✓" if check.status == "PASS" else ("!" if check.status == "FLAGGED" else "✗")
        print(f"    [{check_icon}] {check.check_name} ({check.source}): {check.status}")
        print(f"        └─ {check.details}")

    print("\n  🎓 Education & Work History Captured:")
    for edu in res.education_summary:
        print(f"    - Degree: {edu['degree']} | Institution: {edu['institution']} ({edu['graduation_year']})")
    for work in res.work_history_summary[:2]:
        print(f"    - Work: {work['position']} at {work['organization']} ({work['start_date']} - {work['end_date']})")

    print("\n  🏥 Approved Market Lines & Products:")
    if res.approved_market_lines:
        for m in res.approved_market_lines:
            print(f"    • [{m.status}] {m.market_line} -> {m.product_name} (Code: {m.plan_code})")
            print(f"        Tier: {m.network_tier} | Effective: {m.effective_date} to {m.expiration_date}")
    else:
        print("    • None (All market lines rejected due to credentialing status)")

    if res.rejected_market_lines:
        print("\n  🚫 Excluded / Rejected Market Lines:")
        for rej in res.rejected_market_lines:
            print(f"    • {rej.market_line} -> {rej.product_name}: {rej.approval_reason}")


def main():
    parser = argparse.ArgumentParser(description="Provider Credentialing Approval Agentic Workflow")
    parser.add_argument("--roster", type=str, default="data/sample_provider_roster.csv", help="Path to roster CSV or JSON")
    parser.add_argument("--npi", type=str, help="Specific NPI to credential on-demand")
    parser.add_argument("--first", type=str, default="Doctor", help="Provider First Name")
    parser.add_argument("--last", type=str, default="Provider", help="Provider Last Name")
    parser.add_argument("--state", type=str, default="TX", help="Practice State")
    parser.add_argument("--output", type=str, help="Save JSON results to output file")

    args = parser.parse_args()
    print_banner()

    orchestrator = CredentialingOrchestrator()

    if args.npi:
        print(f"[*] Running on-demand single provider credentialing for NPI: {args.npi}")
        provider_item = RosterProviderItem(
            npi=args.npi,
            first_name=args.first,
            last_name=args.last,
            practice_state=args.state
        )
        result = orchestrator.process_single_provider(provider_item)
        print_provider_result(result)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result.model_dump_json(indent=2))
            print(f"\n[+] Saved results to {args.output}")
    else:
        roster_path = args.roster
        if not os.path.isabs(roster_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            roster_path = os.path.join(base_dir, args.roster)

        print(f"[*] Ingesting and processing roster file: {roster_path}")
        batch_result = orchestrator.process_roster(roster_path, filename=os.path.basename(roster_path))

        print("\n" + "=" * 80)
        print(f" BATCH PROCESSING SUMMARY (Batch ID: {batch_result.batch_id})")
        print("=" * 80)
        print(f" Total Providers Processed:      {batch_result.total_providers}")
        print(f" Full Approvals:                 {batch_result.approved_count} [APPROVED]")
        print(f" Conditional Approvals:          {batch_result.conditional_count} [CONDITIONAL]")
        print(f" Committee Review Required:      {batch_result.committee_review_count} [REVIEW]")
        print(f" Denied:                         {batch_result.denied_count} [DENIED]")

        for res in batch_result.results:
            print_provider_result(res)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(batch_result.model_dump_json(indent=2))
            print(f"\n[+] Saved full batch results to {args.output}")


if __name__ == "__main__":
    main()
