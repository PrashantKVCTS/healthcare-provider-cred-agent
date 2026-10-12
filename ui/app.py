"""
Streamlit Web Dashboard for Healthcare Provider Credentialing Approval Agent.
Provides an interactive cockpit for Credentialing Specialists, Network Managers,
and Appian Integration Administrators.
"""

import streamlit as st
import pandas as pd
import json
import os
import sys

# Ensure current project directory is in python path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from agents.credentialing_orchestrator import CredentialingOrchestrator
from models.provider_models import RosterProviderItem

st.set_page_config(
    page_title="Healthcare Provider Credentialing Agent",
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
        margin-bottom: 5px;
    }
    .sub-header {
        font-size: 15px;
        color: #4b5563;
        margin-bottom: 20px;
    }
    .badge-approved {
        background-color: #dcfce7;
        color: #15803d;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 13px;
        border: 1px solid #86efac;
    }
    .badge-conditional {
        background-color: #fef9c3;
        color: #854d0e;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 13px;
        border: 1px solid #fde047;
    }
    .badge-review {
        background-color: #ffedd5;
        color: #9a3412;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 13px;
        border: 1px solid #fdba74;
    }
    .badge-denied {
        background-color: #fee2e2;
        color: #b91c1c;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 13px;
        border: 1px solid #fca5a5;
    }
    .card-metric {
        background: white;
        padding: 16px;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_orchestrator():
    return CredentialingOrchestrator()


orchestrator = get_orchestrator()

# Sidebar Navigation
st.sidebar.title("🏥 Credentialing Agent")
st.sidebar.caption("Healthcare Provider Management System (PMS)")

nav_mode = st.sidebar.radio(
    "Workflow Mode",
    [
        "📁 Roster Batch Ingestion",
        "🩺 On-Demand Single Provider",
        "🔔 Event Subscriptions & Webhooks",
        "⚡ Appian Integration Specs",
        "⚙️ Market Lines Rules"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info(
    "**Agent Capabilities:**\n"
    "• Ingests Provider Rosters (CSV/JSON)\n"
    "• PSV: CMS NPPES NPI Registry\n"
    "• PSV: CAQH ProView (120-day currency)\n"
    "• Captures Education & Work History\n"
    "• Captures Licenses, DEA, Board Certs\n"
    "• Malpractice & OIG/SAM Sanctions\n"
    "• Market Lines Approval & Dates\n"
    "• REST API for Appian Automation"
)

# -------------------------------------------------------------
# MODE 1: ROSTER BATCH INGESTION
# -------------------------------------------------------------
if nav_mode == "📁 Roster Batch Ingestion":
    st.markdown('<div class="main-header">Provider Roster Ingestion & Automated Approval</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload a roster file or run the default multi-scenario test roster. The Agent will execute Primary Source Verification and assign business market lines.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("Upload Roster CSV / JSON", type=["csv", "json"])
    with col2:
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
        with st.spinner("🤖 Credentialing Agentic Workflow in progress (Intake -> PSV -> Committee Rules)..."):
            batch_result = orchestrator.process_roster(roster_content, filename=filename)
            st.session_state["batch_results"] = batch_result
            st.session_state["last_processed_file"] = file_identifier

    if "batch_results" in st.session_state:
        res = st.session_state["batch_results"]

        # Executive Metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Providers", res.total_providers)
        m2.metric("Full Approvals", res.approved_count, delta="Approved", delta_color="normal")
        m3.metric("Conditional", res.conditional_count, delta="Pending CAQH", delta_color="off")
        m4.metric("Committee Review", res.committee_review_count, delta="Peer Review", delta_color="inverse")
        m5.metric("Denied", res.denied_count, delta="PSV Failures", delta_color="inverse")

        st.markdown("---")
        st.subheader("📋 Roster Decision Roster")

        # Summary Table
        summary_rows = []
        for p in res.results:
            summary_rows.append({
                "NPI": p.npi,
                "Provider Name": p.provider_name,
                "Specialty": p.npi_profile.primary_specialty if p.npi_profile else "N/A",
                "Decision": p.overall_decision.value,
                "CAQH Status": "Current (<=120d)" if p.caqh_profile and p.caqh_profile.is_attestation_current else "Expired",
                "Approved Lines": len(p.approved_market_lines),
                "Appian Case ID": p.appian_case_id,
                "Recredentialing Due": p.recredentialing_due_date
            })

        df_summary = pd.DataFrame(summary_rows)
        st.dataframe(df_summary, use_container_width=True)

        st.markdown("---")
        st.subheader("🔍 Deep-Dive Provider Dossier & Audit Trail")

        provider_names = [f"{p.provider_name} (NPI: {p.npi})" for p in res.results]
        selected_idx = st.selectbox("Select Provider to inspect:", range(len(provider_names)), format_func=lambda i: provider_names[i])

        p_sel = res.results[selected_idx]

        # Decision Header Banner
        badge_class = {
            "APPROVED": "badge-approved",
            "CONDITIONAL_APPROVAL": "badge-conditional",
            "COMMITTEE_REVIEW_REQUIRED": "badge-review",
            "DENIED": "badge-denied"
        }.get(p_sel.overall_decision.value, "badge-approved")

        st.markdown(f"""
        <div style="background:#f8fafc; padding:18px; border-radius:10px; border-left:6px solid #2563eb; margin-bottom:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3 style="margin:0; color:#0f172a;">{p_sel.provider_name}</h3>
                <span class="{badge_class}">{p_sel.overall_decision.value}</span>
            </div>
            <p style="margin-top:8px; margin-bottom:4px; font-weight:500; color:#334155;">{p_sel.decision_summary}</p>
            <div style="font-size:13px; color:#64748b;">
                <strong>Appian Case ID:</strong> {p_sel.appian_case_id} &nbsp;|&nbsp; 
                <strong>Decision Date:</strong> {p_sel.decision_date} &nbsp;|&nbsp; 
                <strong>Re-Credentialing Due:</strong> {p_sel.recredentialing_due_date} &nbsp;|&nbsp; 
                <strong>Ready for Contracting:</strong> {'YES' if p_sel.ready_for_pdm_contracting else 'NO'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Tabs for details
        t1, t2, t3, t4, t5 = st.tabs([
            "🏥 Approved Market Lines & Products",
            "🛡️ PSV Verification Checks",
            "🎓 Education & Work History",
            "📜 State Licenses & DEA",
            "🤖 Agent Audit Trail & Appian JSON"
        ])

        with t1:
            st.markdown("#### Business Market Lines with Approved Dates & Products")
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
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("#### 🎓 Education & Training")
                for e in p_sel.education_summary:
                    st.markdown(f"• **{e['degree']} ({e['type']})**")
                    st.markdown(f"  {e['institution']} - Graduated: {e['graduation_year']} {'(Verified)' if e['verified'] else ''}")
            with col_b:
                st.markdown("#### 💼 5-Year Work History")
                for w in p_sel.work_history_summary:
                    gap_alert = f"🚨 *Gap Flag: {w['gap_reason']}*" if w['gap_flag'] else ""
                    st.markdown(f"• **{w['position']}** at {w['organization']}")
                    st.markdown(f"  Dates: {w['start_date']} - {w['end_date']} {gap_alert}")

        with t4:
            col_c, col_d = st.columns(2)
            with col_c:
                st.markdown("#### 📜 State Medical Licenses")
                for lic in p_sel.licenses_summary:
                    st.markdown(f"• **State {lic['state']} - License #{lic['license_number']}** ({lic['type']})")
                    st.markdown(f"  Status: **{lic['status']}** | Expires: {lic['expiration_date']}")
            with col_d:
                st.markdown("#### 💊 DEA & Malpractice Insurance")
                if p_sel.caqh_profile and p_sel.caqh_profile.dea_records:
                    for d in p_sel.caqh_profile.dea_records:
                        st.markdown(f"• **DEA #{d.dea_number}** (Schedules: {', '.join(d.schedules)}) - {d.status}")
                if p_sel.caqh_profile and p_sel.caqh_profile.malpractice:
                    mp = p_sel.caqh_profile.malpractice
                    st.markdown(f"• **Carrier:** {mp.carrier} (Policy #{mp.policy_number})")
                    st.markdown(f"  Limits: ${mp.per_claim_limit:,.0f} / ${mp.aggregate_limit:,.0f}")
                    st.markdown(f"  Past 5-Year Claims: **{mp.claims_past_5_years}**")

        with t5:
            st.markdown("#### Agent Execution Audit Trail")
            for step in p_sel.audit_trail:
                st.markdown(f"- **[{step.agent_name}] {step.step_name}**: {step.action_taken} (*{step.status}*)")
            
            st.markdown("#### Appian JSON Output (Direct CDT Binding)")
            st.json(p_sel.model_dump())

# -------------------------------------------------------------
# MODE 2: ON-DEMAND SINGLE PROVIDER
# -------------------------------------------------------------
elif nav_mode == "🩺 On-Demand Single Provider":
    st.markdown('<div class="main-header">On-Demand Provider Credentialing Verification</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Enter single provider details or select a preset to evaluate credentialing live.</div>', unsafe_allow_html=True)

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
            st.markdown(f"**Appian Case ID:** `{res.appian_case_id}`")
            st.markdown(f"**Re-Credentialing Due:** `{res.recredentialing_due_date}`")

            st.markdown("### Approved Market Lines")
            st.table(pd.DataFrame([m.model_dump() for m in res.approved_market_lines]))

            st.markdown("### PSV Primary Source Verification Checks")
            st.table(pd.DataFrame([c.model_dump() for c in res.psv_checks]))

# -------------------------------------------------------------
# MODE 3: EVENT SUBSCRIPTIONS & WEBHOOKS (NEW!)
# -------------------------------------------------------------
elif nav_mode == "🔔 Event Subscriptions & Webhooks":
    st.markdown('<div class="main-header">Agent Credentialing Service Subscriptions</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Manage webhook subscriptions, test Appian endpoints, and run automated 90-day recredentialing / CAQH expiration scans.</div>', unsafe_allow_html=True)

    sub_svc = orchestrator.subscription_service
    subs = sub_svc.list_subscriptions()

    tab_subs, tab_new, tab_scan = st.tabs([
        "📋 Active Subscriptions",
        "➕ Register New Webhook",
        "🔍 Continuous Monitoring Alert Scanner"
    ])

    with tab_subs:
        st.markdown(f"#### Registered Appian & PMS Consumers ({len(subs)})")
        if not subs:
            st.info("No active subscriptions found. Register a webhook callback below to receive real-time notifications.")
        else:
            for s in subs:
                status_color = "#15803d" if s.is_active else "#9ca3af"
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
                            res = sub_svc.deliver_event(s, test_event)
                            if res.get("success"):
                                st.success(f"Ping delivered successfully! Status: {res.get('status_code')}")
                            else:
                                st.warning(f"Ping attempt finished. Result: {res}")
                    with col_t2:
                        if st.button(f"🗑️ Delete {s.subscription_id}", key=f"del_{s.subscription_id}"):
                            sub_svc.delete_subscription(s.subscription_id)
                            st.success(f"Deleted subscription {s.subscription_id}")
                            st.rerun()

    with tab_new:
        st.markdown("#### Register New Appian Web API Subscription")
        with st.form("new_subscription_form"):
            c_name = st.text_input("Subscribing Client / System Name", value="Appian Healthcare PDM Process Model")
            w_url = st.text_input("Target Webhook URL (e.g. Appian Web API)", value="https://myhealthplan.appiancloud.com/suite/webapi/credentialing-callback")
            selected_events = st.multiselect(
                "Subscribed Event Types",
                ["*", "BATCH_COMPLETED", "CREDENTIALING_COMPLETED", "RECREDENTIALING_ALERT", "CAQH_EXPIRATION_ALERT", "SANCTION_DETECTED"],
                default=["*"]
            )
            a_token = st.text_input("Authorization Bearer Token (Optional)", value="", type="password")
            s_key = st.text_input("HMAC Secret Key for 'X-CredAgent-Signature' (Optional)", value="")
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
        st.write("Evaluates active provider roster for NCQA 36-month recredentialing deadlines (<= 90 days), expired or expiring CAQH attestations (> 90 days old), and sanctions. Dispatches alert webhooks to all active subscribers.")

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

# -------------------------------------------------------------
# MODE 4: APPIAN INTEGRATION SPECS
# -------------------------------------------------------------
elif nav_mode == "⚡ Appian Integration Specs":
    st.markdown('<div class="main-header">Appian Workflow Integration & Automation</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Pre-configured REST endpoints and integration artifacts ready for Appian Designer.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.info("### 📡 Available Endpoints\n"
                "• `POST /api/v1/roster/process`: Ingests multipart CSV file.\n"
                "• `POST /api/v1/roster/process-base64`: Ingests Base64 document string from Appian `a!documentToBase64()`.\n"
                "• `POST /api/v1/provider/credential`: Single provider on-demand credentialing decision.\n"
                "• `GET /api/v1/market-lines`: Business approved lines & product rules.\n"
                "• `GET /api/v1/health`: Ping & connection check.")

    with col2:
        st.success("### 🚀 Appian Quick Start\n"
                   "1. Start the API: `python api/appian_api.py`\n"
                   "2. Import [`openapi.json`](file:///C:/Users/866223/.gemini/antigravity/scratch/provider_cred_agent/appian/openapi.json) into Appian Designer.\n"
                   "3. Read the complete guide in [`appian_integration_guide.md`](file:///C:/Users/866223/.gemini/antigravity/scratch/provider_cred_agent/appian/appian_integration_guide.md).")

    openapi_path = os.path.join(current_dir, "appian", "openapi.json")
    if os.path.exists(openapi_path):
        with open(openapi_path, "r", encoding="utf-8") as f:
            st.download_button(
                label="📥 Download Appian OpenAPI 3.0 Specification",
                data=f.read(),
                file_name="appian_cred_agent_openapi.json",
                mime="application/json"
            )

# -------------------------------------------------------------
# MODE 5: MARKET LINES RULES
# -------------------------------------------------------------
elif nav_mode == "⚙️ Market Lines Rules":
    st.markdown('<div class="main-header">Business Market Lines & Product Configuration</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Healthcare Payer Lines of Business (LOB), NCQA standards, and product network tiers.</div>', unsafe_allow_html=True)

    st.json(orchestrator.rules_agent.market_lines_config)
