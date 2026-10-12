"""
Standalone Operations & Committee Portal for Healthcare Provider Credentialing.
A full-featured alternative to the Appian UI workflow, providing Roster Ingestion,
Human-in-the-Loop Committee Reviews, Case Management, Committee Docket Generation,
Adverse Action Notices, On-Demand Verification, and Webhook Subscriptions.
"""

import streamlit as st
import pandas as pd
import json
import os
import sys
from datetime import datetime

# Ensure current project directory is in python path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from agents.credentialing_orchestrator import CredentialingOrchestrator
from models.provider_models import RosterProviderItem, CredentialingDecision
from models.credentialing_models import CredentialingAuditTrail

st.set_page_config(
    page_title="Healthcare Credentialing Operations & Committee Portal",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 26px;
        font-weight: 700;
        color: #1e3a8a;
        margin-bottom: 4px;
    }
    .sub-header {
        font-size: 14px;
        color: #4b5563;
        margin-bottom: 18px;
    }
    .badge-approved {
        background-color: #dcfce7;
        color: #15803d;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 12px;
        border: 1px solid #86efac;
        display: inline-block;
    }
    .badge-conditional {
        background-color: #fef9c3;
        color: #854d0e;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 12px;
        border: 1px solid #fde047;
        display: inline-block;
    }
    .badge-review {
        background-color: #ffedd5;
        color: #9a3412;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 12px;
        border: 1px solid #fdba74;
        display: inline-block;
    }
    .badge-denied {
        background-color: #fee2e2;
        color: #b91c1c;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 12px;
        border: 1px solid #fca5a5;
        display: inline-block;
    }
    .card-banner {
        background: #f8fafc;
        padding: 16px;
        border-radius: 10px;
        border-left: 6px solid #2563eb;
        margin-bottom: 20px;
    }
    .committee-box {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 16px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_orchestrator():
    return CredentialingOrchestrator()


orchestrator = get_orchestrator()

# Sidebar Navigation
st.sidebar.title("🏥 Credentialing Portal")
st.sidebar.caption("Standalone Operations & Committee Workbench")

nav_mode = st.sidebar.radio(
    "Workflow Navigation",
    [
        "📁 Roster Ingestion & Case Management",
        "⚖️ Credentialing Committee & Peer Review",
        "📜 Committee Docket & Adverse Action Letters",
        "🩺 On-Demand Single Provider Verification",
        "⚙️ Market Lines & Rules Configurator",
        "🔔 Event Subscriptions & Monitoring",
        "ℹ️ Standalone vs Appian Architecture"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Operating Mode:** 🟢 `Standalone UI`\n\n"
    "*(Replaces Appian UI workflow with full interactive intake, committee review, and docket sign-off)*"
)


def recalculate_batch_counts(res):
    """Helper to recalculate counts after human committee overrides."""
    approved = sum(1 for p in res.results if p.overall_decision == CredentialingDecision.APPROVED)
    cond = sum(1 for p in res.results if p.overall_decision == CredentialingDecision.CONDITIONAL_APPROVAL)
    review = sum(1 for p in res.results if p.overall_decision == CredentialingDecision.COMMITTEE_REVIEW_REQUIRED)
    denied = sum(1 for p in res.results if p.overall_decision == CredentialingDecision.DENIED)
    res.approved_count = approved
    res.conditional_count = cond
    res.committee_review_count = review
    res.denied_count = denied


# =============================================================
# MODE 1: ROSTER INGESTION & CASE MANAGEMENT
# =============================================================
if nav_mode == "📁 Roster Ingestion & Case Management":
    st.markdown('<div class="main-header">Provider Roster Ingestion & Case Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload a roster CSV/JSON file or load standard test data. The agent automates Primary Source Verification (PSV), captures credentials, and generates initial determinations.</div>', unsafe_allow_html=True)

    col_u1, col_u2 = st.columns([2, 1])
    with col_u1:
        uploaded_file = st.file_uploader("Upload Provider Roster (CSV / JSON)", type=["csv", "json"])
    with col_u2:
        use_sample = st.button("🚀 Load Sample Payer Roster", use_container_width=True)

    roster_content = None
    filename = "sample_provider_roster.csv"
    file_identifier = None

    if uploaded_file is not None:
        file_identifier = f"upload_{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get("last_processed_file") != file_identifier:
            roster_content = uploaded_file.getvalue().decode("utf-8", errors="replace")
            filename = uploaded_file.name
    elif use_sample or "batch_results" not in st.session_state:
        file_identifier = "sample_provider_roster.csv"
        if use_sample or st.session_state.get("last_processed_file") != file_identifier:
            sample_path = os.path.join(current_dir, "data", "sample_provider_roster.csv")
            if os.path.exists(sample_path):
                with open(sample_path, "r", encoding="utf-8") as f:
                    roster_content = f.read()
                    filename = "sample_provider_roster.csv"

    if roster_content:
        with st.spinner("🤖 Executing Primary Source Verifications (NPPES, CAQH, OIG, SAM, Medical Boards)..."):
            batch_result = orchestrator.process_roster(roster_content, filename=filename)
            st.session_state["batch_results"] = batch_result
            st.session_state["last_processed_file"] = file_identifier

    if "batch_results" in st.session_state:
        res = st.session_state["batch_results"]
        recalculate_batch_counts(res)

        # Metrics Bar
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Providers", res.total_providers)
        m2.metric("Full Approvals", res.approved_count, delta="Approved", delta_color="normal")
        m3.metric("Conditional", res.conditional_count, delta="Pending CAQH/Docs", delta_color="off")
        m4.metric("Committee Review", res.committee_review_count, delta="Action Needed", delta_color="inverse")
        m5.metric("Denied", res.denied_count, delta="Adverse Action", delta_color="inverse")

        st.markdown("---")

        # Filters & Search
        st.subheader("📋 Ingested Provider Cases")
        f_col1, f_col2 = st.columns([1, 2])
        with f_col1:
            status_filter = st.selectbox(
                "Filter by Decision Status:",
                ["ALL", "APPROVED", "CONDITIONAL_APPROVAL", "COMMITTEE_REVIEW_REQUIRED", "DENIED"],
                index=0
            )
        with f_col2:
            search_query = st.text_input("🔍 Search by NPI or Provider Name:", "").strip().lower()

        # Build list matching filters
        filtered_providers = []
        for p in res.results:
            decision_val = p.overall_decision.value if hasattr(p.overall_decision, "value") else str(p.overall_decision)
            if status_filter != "ALL" and decision_val != status_filter:
                continue
            if search_query:
                if (search_query not in p.npi.lower()) and (search_query not in p.provider_name.lower()):
                    continue
            filtered_providers.append(p)

        # Summary Table
        summary_rows = []
        for p in filtered_providers:
            dec_str = p.overall_decision.value if hasattr(p.overall_decision, "value") else str(p.overall_decision)
            summary_rows.append({
                "NPI": p.npi,
                "Provider Name": p.provider_name,
                "Specialty": p.npi_profile.primary_specialty if p.npi_profile else "N/A",
                "Decision": dec_str,
                "Committee Status": p.committee_decision or ("Action Needed" if p.committee_review_needed else "Auto Cleared"),
                "Approved Lines": len(p.approved_market_lines),
                "Case ID": p.appian_case_id or f"CASE-{p.npi}",
                "Recredentialing Due": p.recredentialing_due_date
            })

        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

        st.markdown("---")
        st.subheader("🔍 Deep-Dive Provider Dossier")

        if not filtered_providers:
            st.info("No providers match the current search / filter criteria.")
        else:
            provider_names = [f"{p.provider_name} (NPI: {p.npi})" for p in filtered_providers]
            selected_idx = st.selectbox("Select Provider to inspect:", range(len(provider_names)), format_func=lambda i: provider_names[i])
            p_sel = filtered_providers[selected_idx]

            dec_str = p_sel.overall_decision.value if hasattr(p_sel.overall_decision, "value") else str(p_sel.overall_decision)
            badge_class = {
                "APPROVED": "badge-approved",
                "CONDITIONAL_APPROVAL": "badge-conditional",
                "COMMITTEE_REVIEW_REQUIRED": "badge-review",
                "DENIED": "badge-denied"
            }.get(dec_str, "badge-approved")

            st.markdown(f"""
            <div class="card-banner">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0; color:#0f172a;">{p_sel.provider_name}</h3>
                    <span class="{badge_class}">{dec_str}</span>
                </div>
                <p style="margin-top:8px; margin-bottom:4px; font-weight:500; color:#334155;">{p_sel.decision_summary}</p>
                <div style="font-size:13px; color:#64748b;">
                    <strong>Case ID:</strong> {p_sel.appian_case_id} &nbsp;|&nbsp; 
                    <strong>Decision Date:</strong> {p_sel.decision_date} &nbsp;|&nbsp; 
                    <strong>Re-Credentialing Due:</strong> {p_sel.recredentialing_due_date} &nbsp;|&nbsp; 
                    <strong>Contracting Ready:</strong> {'YES' if p_sel.ready_for_pdm_contracting else 'NO'}
                </div>
            </div>
            """, unsafe_allow_html=True)

            t1, t2, t3, t4, t5 = st.tabs([
                "🏥 Approved Market Lines & Products",
                "🛡️ PSV Verification Checks",
                "🎓 Education & Work History",
                "📜 State Licenses & DEA",
                "🤖 Full Audit Trail & CDT JSON"
            ])

            with t1:
                st.markdown("#### Payer Market Lines & Network Tier Approvals")
                if p_sel.approved_market_lines:
                    lines_data = []
                    for m in p_sel.approved_market_lines:
                        lines_data.append({
                            "Market Line": m.market_line,
                            "Product Name": m.product_name,
                            "Plan Code": m.plan_code,
                            "Tier": m.network_tier,
                            "Status": m.status,
                            "Effective Date": m.effective_date,
                            "Expiration Date": m.expiration_date,
                            "Recred Due Date": m.recred_due_date
                        })
                    st.table(pd.DataFrame(lines_data))
                else:
                    st.warning("No market lines approved for this provider.")

                if p_sel.rejected_market_lines:
                    with st.expander("Excluded / Rejected Products"):
                        rej_data = [{"Line": r.market_line, "Product": r.product_name, "Reason": r.approval_reason} for r in p_sel.rejected_market_lines]
                        st.table(pd.DataFrame(rej_data))

            with t2:
                st.markdown("#### Primary Source Verification (PSV) Checklist")
                for c in p_sel.psv_checks:
                    c_icon = "✅" if c.status == "PASS" else ("⚠️" if c.status == "FLAGGED" else "❌")
                    with st.expander(f"{c_icon} {c.check_name} ({c.source}) - Status: {c.status}"):
                        st.write(c.details)
                        st.caption(f"Verified At: {c.verified_at}")

            with t3:
                c_ed, c_wk = st.columns(2)
                with c_ed:
                    st.markdown("#### 🎓 Education & Residency")
                    for e in p_sel.education_summary:
                        st.markdown(f"• **{e['degree']} ({e['type']})**")
                        st.markdown(f"  {e['institution']} - Graduated: {e['graduation_year']} {'(Verified)' if e.get('verified') else ''}")
                with c_wk:
                    st.markdown("#### 💼 5-Year Work History")
                    for w in p_sel.work_history_summary:
                        gap_alert = f"🚨 *Gap Flag: {w['gap_reason']}*" if w.get('gap_flag') else ""
                        st.markdown(f"• **{w['position']}** at {w['organization']}")
                        st.markdown(f"  Dates: {w['start_date']} - {w['end_date']} {gap_alert}")

            with t4:
                c_lic, c_dea = st.columns(2)
                with c_lic:
                    st.markdown("#### 📜 State Medical Licenses")
                    for lic in p_sel.licenses_summary:
                        st.markdown(f"• **State {lic['state']} - #{lic['license_number']}** ({lic['type']})")
                        st.markdown(f"  Status: **{lic['status']}** | Expires: {lic['expiration_date']}")
                with c_dea:
                    st.markdown("#### 💊 DEA & Malpractice Insurance")
                    if p_sel.caqh_profile and p_sel.caqh_profile.dea_records:
                        for d in p_sel.caqh_profile.dea_records:
                            st.markdown(f"• **DEA #{d.dea_number}** (Schedules: {', '.join(d.schedules)}) - {d.status}")
                    if p_sel.caqh_profile and p_sel.caqh_profile.malpractice:
                        mp = p_sel.caqh_profile.malpractice
                        st.markdown(f"• **Carrier:** {mp.carrier} (Policy #{mp.policy_number})")
                        st.markdown(f"  Coverage: ${mp.per_claim_limit:,.0f} / ${mp.aggregate_limit:,.0f}")
                        st.markdown(f"  Past 5-Year Claims: **{mp.claims_past_5_years}**")

            with t5:
                st.markdown("#### Agent Execution Audit Trail")
                for step in p_sel.audit_trail:
                    st.markdown(f"- **[{step.agent_name}] {step.step_name}**: {step.action_taken} (*{step.status}*)")
                st.markdown("#### Standard JSON Model Export")
                st.json(p_sel.model_dump())


# =============================================================
# MODE 2: CREDENTIALING COMMITTEE WORKBENCH (HUMAN-IN-THE-LOOP)
# Replaces Appian Committee Review Task Queue
# =============================================================
elif nav_mode == "⚖️ Credentialing Committee & Peer Review":
    st.markdown('<div class="main-header">Credentialing Committee & Peer Review Workbench</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Human-in-the-Loop peer review workstation replacing Appian Committee Task Queues. Review exceptions, evaluate committee flags, record formal deliberations, and execute binding sign-offs.</div>', unsafe_allow_html=True)

    if "batch_results" not in st.session_state:
        st.warning("No roster loaded. Please load a roster in 'Roster Ingestion' first.")
    else:
        res = st.session_state["batch_results"]
        # Review queue: providers with COMMITTEE_REVIEW_REQUIRED or CONDITIONAL_APPROVAL, or all
        queue_filter = st.radio(
            "Review Queue Filter:",
            ["Exceptions Only (Committee Review & Conditional)", "All Roster Providers"],
            horizontal=True
        )

        if queue_filter.startswith("Exceptions"):
            review_queue = [
                p for p in res.results
                if p.overall_decision in [
                    CredentialingDecision.COMMITTEE_REVIEW_REQUIRED,
                    CredentialingDecision.CONDITIONAL_APPROVAL,
                    CredentialingDecision.DENIED
                ]
            ]
        else:
            review_queue = res.results

        if not review_queue:
            st.success("🎉 No outstanding committee exceptions in queue! All providers are currently approved.")
        else:
            st.info(f"📋 **{len(review_queue)} Provider Cases** awaiting or subject to Committee Peer Review.")

            provider_labels = [
                f"{p.provider_name} (NPI: {p.npi}) - Status: {p.overall_decision.value} "
                f"{'[DECIDED: ' + p.committee_decision + ']' if p.committee_decision else ''}"
                for p in review_queue
            ]
            sel_idx = st.selectbox("Select Case from Review Queue:", range(len(provider_labels)), format_func=lambda i: provider_labels[i])
            provider = review_queue[sel_idx]

            st.markdown("---")
            c_left, c_right = st.columns([1, 1])

            with c_left:
                st.markdown("### 🔍 Case Review Dossier")
                st.write(f"**Provider:** {provider.provider_name}")
                st.write(f"**NPI:** `{provider.npi}` | **CAQH ID:** `{provider.caqh_id or 'N/A'}`")
                st.write(f"**Automated Decision:** `{provider.overall_decision.value}`")
                st.write(f"**Decision Summary:** {provider.decision_summary}")

                if provider.committee_flags:
                    st.error("⚠️ **Identified Committee Flags & PSV Exceptions:**")
                    for f in provider.committee_flags:
                        st.markdown(f"- **{f}**")

                if provider.caqh_profile and provider.caqh_profile.malpractice:
                    mp = provider.caqh_profile.malpractice
                    st.warning(f"**Malpractice Record:** {mp.claims_past_5_years} claims in past 5 years. Carrier: {mp.carrier}")

                st.markdown("#### Primary Source Verification Findings")
                for c in provider.psv_checks:
                    icon = "✅" if c.status == "PASS" else ("⚠️" if c.status == "FLAGGED" else "❌")
                    st.markdown(f"{icon} **{c.check_name}**: {c.status} — *{c.details}*")

            with c_right:
                st.markdown("### ✍️ Committee Determination & Sign-Off")

                if provider.committee_signed_at:
                    st.success(
                        f"✅ **Case already signed off by Committee:**\n\n"
                        f"- **Determination:** `{provider.committee_decision}`\n"
                        f"- **Sign-off By:** `{provider.committee_reviewer}`\n"
                        f"- **Timestamp:** `{provider.committee_signed_at}`\n"
                        f"- **Notes:** {provider.committee_notes}\n"
                        f"- **Stipulations:** {', '.join(provider.committee_stipulations) if provider.committee_stipulations else 'None'}"
                    )
                    st.markdown("You may revise or update the determination below:")

                with st.form(f"committee_determination_form_{provider.npi}"):
                    determination = st.selectbox(
                        "Final Committee Determination:",
                        [
                            "APPROVE (Committee Cleared / Override)",
                            "CONDITIONAL_APPROVAL (Stipulations Required)",
                            "DEFER (Request Additional Records)",
                            "DENY (Adverse Action Recommended)"
                        ],
                        index=0 if provider.overall_decision == CredentialingDecision.APPROVED else (1 if provider.overall_decision == CredentialingDecision.CONDITIONAL_APPROVAL else 3)
                    )

                    reviewer_name = st.text_input(
                        "Reviewing Officer / Committee Chair:",
                        value=provider.committee_reviewer or "Dr. Marcus Welby, MD (Credentialing Committee Chair)"
                    )

                    stipulation_presets = st.multiselect(
                        "Specific Conditions / Stipulations:",
                        [
                            "30-day proof of updated CAQH attestation",
                            "Proof of active malpractice coverage renewal",
                            "6-month peer review case audit",
                            "Provide explanation of 6-month practice gap",
                            "Submit certified state medical board transcript",
                            "Supervised clinical proctoring for first 5 surgeries"
                        ],
                        default=provider.committee_stipulations or []
                    )

                    notes = st.text_area(
                        "Committee Deliberation & Findings / Clinical Rationale:",
                        value=provider.committee_notes or (
                            "Committee reviewed primary source verifications and malpractice history. "
                            "Provider satisfies clinical competency standards."
                        ),
                        height=120
                    )

                    submitted = st.form_submit_button("⚖️ Sign Off & Execute Committee Determination")

                    if submitted:
                        # Map determination
                        if "APPROVE (Committee Cleared" in determination:
                            provider.overall_decision = CredentialingDecision.APPROVED
                            provider.committee_decision = "APPROVED"
                            provider.ready_for_pdm_contracting = True
                            provider.decision_summary = f"Approved by Credentialing Committee override: {notes[:80]}..."
                            # Ensure market lines are approved
                            for m in provider.approved_market_lines:
                                m.status = "APPROVED"
                        elif "CONDITIONAL_APPROVAL" in determination:
                            provider.overall_decision = CredentialingDecision.CONDITIONAL_APPROVAL
                            provider.committee_decision = "CONDITIONAL_APPROVAL"
                            provider.ready_for_pdm_contracting = False
                            provider.decision_summary = f"Conditional Approval granted with stipulations: {', '.join(stipulation_presets)}"
                            for m in provider.approved_market_lines:
                                m.status = "CONDITIONAL"
                        elif "DEFER" in determination:
                            provider.committee_decision = "DEFERRED"
                            provider.decision_summary = f"Deferred by Committee for additional documentation: {notes[:80]}"
                        elif "DENY" in determination:
                            provider.overall_decision = CredentialingDecision.DENIED
                            provider.committee_decision = "DENIED"
                            provider.ready_for_pdm_contracting = False
                            provider.approved_market_lines = []
                            provider.decision_summary = f"Denied by Credentialing Committee: {notes}"

                        provider.committee_reviewer = reviewer_name
                        provider.committee_notes = notes
                        provider.committee_stipulations = stipulation_presets
                        provider.committee_signed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        # Append to audit trail
                        provider.audit_trail.append(CredentialingAuditTrail(
                            step_name="Committee Determination Sign-off",
                            agent_name="Human Committee Reviewer",
                            action_taken=f"Signed off determination: {provider.committee_decision}",
                            details=f"Reviewer: {reviewer_name}. Stipulations: {stipulation_presets}. Rationale: {notes}",
                            status="COMPLETED"
                        ))

                        recalculate_batch_counts(res)
                        st.success(f"Determination '{provider.committee_decision}' recorded and signed for Dr. {provider.provider_name}!")
                        st.rerun()


# =============================================================
# MODE 3: COMMITTEE DOCKET & ADVERSE ACTION GENERATOR
# Replaces Appian Report & Document Generation
# =============================================================
elif nav_mode == "📜 Committee Docket & Adverse Action Letters":
    st.markdown('<div class="main-header">Committee Docket & Adverse Action Document Generator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Generate formal Medical Executive Committee (MEC) credentialing dockets, executive meeting minutes, and regulatory-compliant Adverse Action notices.</div>', unsafe_allow_html=True)

    if "batch_results" not in st.session_state:
        st.warning("No roster loaded. Please load a roster in 'Roster Ingestion' first.")
    else:
        res = st.session_state["batch_results"]
        recalculate_batch_counts(res)

        tab_docket, tab_adverse = st.tabs([
            "📋 Medical Executive Committee (MEC) Docket",
            "✉️ Adverse Action Notice Generator"
        ])

        with tab_docket:
            st.markdown("### Formal Credentialing Committee Meeting Docket")
            docket_date = datetime.now().strftime("%B %d, %Y")
            docket_id = f"MEC-DOCKET-{datetime.now().strftime('%Y%m%d')}-01"

            # Build Docket Markdown
            docket_md = f"""# MEDICAL EXECUTIVE COMMITTEE (MEC) CREDENTIALING DOCKET
**Docket Reference:** `{docket_id}`  
**Convening Date:** {docket_date}  
**Governing Standard:** NCQA Credentialing (CR1-CR7) & CMS CoP  

---

## 1. Executive Summary
- **Total Provider Applications Evaluated:** {res.total_providers}
- **Full Credentialing Approvals Granted:** {res.approved_count}
- **Conditional Approvals (Subject to Stipulations):** {res.conditional_count}
- **Cases Deferred / Pending Committee Review:** {res.committee_review_count}
- **Adverse Actions / Applications Denied:** {res.denied_count}

---

## 2. Provider Deliberation Register

| NPI | Provider Name | Specialty | Final Decision | Committee Sign-Off | Recredentialing Due |
|---|---|---|---|---|---|
"""
            for p in res.results:
                dec = p.overall_decision.value if hasattr(p.overall_decision, "value") else str(p.overall_decision)
                sign = f"Signed by {p.committee_reviewer}" if p.committee_signed_at else "Standard PSV Path"
                docket_md += f"| {p.npi} | {p.provider_name} | {p.npi_profile.primary_specialty if p.npi_profile else 'General'} | **{dec}** | {sign} | {p.recredentialing_due_date} |\n"

            docket_md += f"""
---

## 3. Committee Sign-Off & Attestation
The undersigned Credentialing Committee Chair hereby attests that all Primary Source Verifications (NPPES, CAQH ProView, State Licensing Boards, DEA, OIG LEIE, SAM.gov) were reviewed in compliance with NCQA standards.

**Committee Chair:** _______________________________________  
**Date of Ratification:** {docket_date}  
"""

            st.markdown(docket_md)
            st.download_button(
                label="📥 Download Formal Committee Docket (.md)",
                data=docket_md,
                file_name=f"cred_committee_docket_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown"
            )

        with tab_adverse:
            st.markdown("### Healthcare Quality Improvement Act (HCQIA) Adverse Action Notice")
            denied_providers = [p for p in res.results if p.overall_decision == CredentialingDecision.DENIED]

            if not denied_providers:
                st.info("No providers in the current batch have been denied. You can select any provider below to preview notice format.")
                candidate_providers = res.results
            else:
                candidate_providers = denied_providers

            sel_denied = st.selectbox(
                "Select Provider for Adverse Action Notice:",
                candidate_providers,
                format_func=lambda p: f"{p.provider_name} (NPI: {p.npi}) - Status: {p.overall_decision.value}"
            )

            if sel_denied:
                notice_text = f"""CONFIDENTIAL & PRIVILEGED - NOTICE OF ADVERSE CREDENTIALING DETERMINATION

Date: {datetime.now().strftime('%B %d, %Y')}

To:
{sel_denied.provider_name}, MD
NPI: {sel_denied.npi}
Practice State: {sel_denied.practice_state if hasattr(sel_denied, 'practice_state') else 'TX'}

RE: Healthcare Provider Network Credentialing Application (Case ID: {sel_denied.appian_case_id or 'CASE-DENIAL'})

Dear Dr. {sel_denied.provider_name.split()[-1] if sel_denied.provider_name else 'Provider'},

Please be advised that on {datetime.now().strftime('%B %d, %Y')}, the Credentialing Committee evaluated your application for participation in our healthcare payer networks. 

Based upon Primary Source Verification (PSV) and applicable NCQA / CMS credentialing standards, the Committee has voted to issue an ADVERSE ACTION resulting in the DENIAL of your credentialing application for all requested market lines.

FINDINGS OF RECORD:
- Primary Factor: {sel_denied.decision_summary}
- PSV Discrepancies: {', '.join(sel_denied.committee_flags) if sel_denied.committee_flags else 'Sanction screening or licensing deficiency'}

HEARING AND APPEAL RIGHTS:
Pursuant to the Health Care Quality Improvement Act of 1986 (42 U.S.C. § 11101 et seq.) and Network Credentialing Bylaws, you are entitled to request an appellate review hearing before the Medical Executive Committee. Your written request must be submitted within thirty (30) calendar days from the date of this notice.

Sincerely,

Credentialing Committee & Medical Director Office
Healthcare Provider Network Management
"""
                st.text_area("Notice Preview", notice_text, height=350)
                st.download_button(
                    label=f"📥 Download Adverse Action Letter (Dr. {sel_denied.provider_name})",
                    data=notice_text,
                    file_name=f"adverse_action_notice_{sel_denied.npi}.txt",
                    mime="text/plain"
                )


# =============================================================
# MODE 4: ON-DEMAND SINGLE PROVIDER
# =============================================================
elif nav_mode == "🩺 On-Demand Single Provider":
    st.markdown('<div class="main-header">On-Demand Provider Credentialing Verification</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Enter individual provider credentials to execute immediate primary source verification and rule processing.</div>', unsafe_allow_html=True)

    with st.form("single_provider_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            npi_input = st.text_input("10-Digit NPI", value="1234567893")
            fname = st.text_input("First Name", value="Sarah")
        with c2:
            lname = st.text_input("Last Name", value="Conner")
            state_val = st.selectbox("Practice State", ["TX", "CA", "FL", "NY", "IL", "GA", "OH", "PA"], index=0)
        with c3:
            specialty_val = st.selectbox("Specialty", ["Family Medicine", "Internal Medicine", "Orthopedic Surgery", "Cardiology", "Pediatrics"], index=0)
            caqh_val = st.text_input("CAQH ProView ID", value="14892011")

        submit_btn = st.form_submit_button("Run Credentialing Agent")

    if submit_btn:
        item = RosterProviderItem(
            npi=npi_input,
            first_name=fname,
            last_name=lname,
            practice_state=state_val,
            specialty=specialty_val,
            caqh_id=caqh_val
        )
        with st.spinner("Processing provider verification..."):
            res = orchestrator.process_single_provider(item)
            st.success(f"Decision: {res.overall_decision.value} - {res.decision_summary}")
            st.markdown(f"**Case Reference:** `{res.appian_case_id}` &nbsp;|&nbsp; **Re-Credentialing Due:** `{res.recredentialing_due_date}`")

            st.markdown("### Approved Market Lines")
            st.table(pd.DataFrame([m.model_dump() for m in res.approved_market_lines]))

            st.markdown("### Primary Source Verification (PSV) Checklist")
            st.table(pd.DataFrame([c.model_dump() for c in res.psv_checks]))


# =============================================================
# MODE 5: MARKET LINES & RULES CONFIGURATOR
# =============================================================
elif nav_mode == "⚙️ Market Lines & Rules Configurator":
    st.markdown('<div class="main-header">Business Market Lines & Product Configurator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Inspect and customize healthcare payer lines of business, product codes, network tiers, and NCQA recredentialing cycle parameters.</div>', unsafe_allow_html=True)

    rules = orchestrator.rules_agent.market_lines_config

    st.markdown("#### Configured Healthcare Payer Lines of Business")
    for lob in rules.get("market_lines", []):
        with st.expander(f"🏥 {lob.get('name')} (Recredentialing Cycle: {lob.get('recred_cycle_months')} Months)"):
            st.write(f"**NCQA Required Primary Source Verifications:** {', '.join(lob.get('ncqa_required_psv', []))}")
            st.write(f"**Description:** {lob.get('description')}")
            st.markdown("**Participating Products:**")
            prod_rows = []
            for p in lob.get("products", []):
                prod_rows.append({
                    "Product Name": p.get("product_name"),
                    "Plan Code": p.get("plan_code"),
                    "Default Tier": p.get("network_tier"),
                    "Requires Board Cert": p.get("requires_board_cert")
                })
            st.table(pd.DataFrame(prod_rows))

    st.markdown("#### Underlying Configuration JSON")
    st.json(rules)


# =============================================================
# MODE 6: EVENT SUBSCRIPTIONS & MONITORING
# =============================================================
elif nav_mode == "🔔 Event Subscriptions & Monitoring":
    st.markdown('<div class="main-header">Credentialing Webhook Subscriptions & Continuous Monitoring</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Manage webhook callbacks, test event delivery, and execute continuous monitoring scans for 90-day recredentialing deadlines and CAQH expirations.</div>', unsafe_allow_html=True)

    sub_svc = orchestrator.subscription_service
    subs = sub_svc.list_subscriptions()

    tab_subs, tab_new, tab_scan = st.tabs([
        "📋 Active Subscriptions",
        "➕ Register New Webhook",
        "🔍 Continuous Monitoring Alert Scanner"
    ])

    with tab_subs:
        st.markdown(f"#### Registered Consumers ({len(subs)})")
        if not subs:
            st.info("No active subscriptions found. Register a webhook callback below to receive real-time notifications.")
        else:
            for s in subs:
                status_text = "ACTIVE" if s.is_active else "PAUSED"
                with st.expander(f"🔔 {s.client_name} ({s.subscription_id}) - [{status_text}]"):
                    st.markdown(f"**Target Webhook URL:** `{s.webhook_url}`")
                    st.markdown(f"**Subscribed Events:** `{', '.join([e.value for e in s.subscribed_events])}`")
                    st.markdown(f"**Created At:** {s.created_at} | **Last Delivery:** {s.last_notified_at or 'Never'}")
                    st.markdown(f"**Delivery Health:** {s.successful_deliveries} Success, {s.failed_deliveries} Failed ({s.last_delivery_status or 'N/A'})")

                    col_t1, col_t2 = st.columns([1, 1])
                    with col_t1:
                        if st.button(f"🚀 Send Test Ping to {s.subscription_id}", key=f"ping_{s.subscription_id}"):
                            from models.subscription_models import WebhookEventPayload, SubscriptionEventType
                            test_event = WebhookEventPayload(
                                event_type=SubscriptionEventType.CREDENTIALING_COMPLETED,
                                subscription_id=s.subscription_id,
                                client_name=s.client_name,
                                data={"test": True, "message": "Manual test from Streamlit Dashboard"}
                            )
                            delivery_res = sub_svc.deliver_event(s, test_event)
                            if delivery_res.get("success"):
                                st.success(f"Ping delivered successfully! Status: {delivery_res.get('status_code')}")
                            else:
                                st.warning(f"Ping attempt finished. Result: {delivery_res}")
                    with col_t2:
                        if st.button(f"🗑️ Delete {s.subscription_id}", key=f"del_{s.subscription_id}"):
                            sub_svc.delete_subscription(s.subscription_id)
                            st.success(f"Deleted subscription {s.subscription_id}")
                            st.rerun()

    with tab_new:
        st.markdown("#### Register New Webhook Subscription")
        with st.form("new_subscription_form"):
            c_name = st.text_input("Subscribing System Name", value="Core Provider Management System (PMS)")
            w_url = st.text_input("Target Webhook URL", value="https://httpbin.org/post")
            selected_events = st.multiselect(
                "Subscribed Event Types",
                ["*", "BATCH_COMPLETED", "CREDENTIALING_COMPLETED", "RECREDENTIALING_ALERT", "CAQH_EXPIRATION_ALERT", "SANCTION_DETECTED"],
                default=["*"]
            )
            a_token = st.text_input("Authorization Bearer Token (Optional)", value="", type="password")
            s_key = st.text_input("HMAC Secret Key (Optional)", value="")
            sub_submit = st.form_submit_button("Register Subscription")

            if sub_submit:
                from models.subscription_models import SubscriptionRequest, SubscriptionEventType
                req_obj = SubscriptionRequest(
                    client_name=c_name,
                    webhook_url=w_url,
                    subscribed_events=[SubscriptionEventType(e) for e in selected_events],
                    auth_token=a_token or None,
                    secret_key=s_key or None,
                    is_active=True
                )
                new_s = sub_svc.register_subscription(req_obj)
                st.success(f"Subscription registered! ID: `{new_s.subscription_id}`")
                st.rerun()

    with tab_scan:
        st.markdown("#### Automated Continuous Monitoring Scanner")
        st.write("Evaluates active provider roster for NCQA 36-month recredentialing deadlines (<= 90 days), expired CAQH attestations (> 90 days old), and sanctions.")

        if st.button("⚡ Execute Alert Scan Now"):
            with st.spinner("Scanning provider rosters and dispatching webhooks..."):
                scan_res = orchestrator.run_credentialing_alert_scan()
                st.success(f"Scan complete at {scan_res.scan_timestamp}!")
                st.metric("Total Notifications Dispatched", scan_res.total_notifications_sent)
                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("90-Day Recredentialing Alerts", scan_res.recred_alerts_dispatched)
                sc2.metric("CAQH Expiration Alerts", scan_res.caqh_alerts_dispatched)
                sc3.metric("Sanction Alerts", scan_res.sanction_alerts_dispatched)

                if scan_res.details:
                    st.markdown("##### Alert Events Detail:")
                    st.json(scan_res.details)


# =============================================================
# MODE 7: STANDALONE VS APPIAN ARCHITECTURE
# =============================================================
elif nav_mode == "ℹ️ Standalone vs Appian Architecture":
    st.markdown('<div class="main-header">Standalone UI vs. Appian Enterprise Architecture</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Understanding how the Standalone UI replaces or integrates with Appian BPM.</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        ### 🟢 Standalone Operations UI (Active Mode)
        - **Zero Appian Requirement:** Complete credentialing operations running on pure Python & Streamlit.
        - **Intake & Case Management:** Drag-and-drop CSV/JSON roster parsing and immediate status tracking.
        - **Credentialing Committee Workbench:** Full human-in-the-loop review, deliberation recording, and electronic sign-off.
        - **Document Generation:** One-click generation and download of Medical Executive Committee (MEC) Dockets and HCQIA Adverse Action notices.
        - **Continuous Monitoring:** Real-time alert scans for NCQA 36-month cycles and CAQH 120-day currency.
        """)
    with col_b:
        st.markdown("""
        ### 🔵 Appian Enterprise Integration (Optional)
        - **Ready when needed:** If your organization introduces Appian later, the backend REST API (`/api/v1/...`) and OpenAPI schema remain 100% active.
        - **Process Models:** Connect Appian Process Models using the pre-built `openapi.json` contract.
        - **Hybrid Operation:** The standalone UI and Appian can operate simultaneously against the same agent engine.
        """)

    st.markdown("---")
    st.info("💡 **Quick Run Command:** `streamlit run ui/app.py` or double-click `run_ui.bat`.")
