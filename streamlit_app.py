import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from database.database import SessionLocal
from backend.app.models.entities import (
    Customer, Document, RiskRating, ReviewCase,
    Alert, AuditEvent, BeneficialOwner
)
from backend.app.engines.kyc_engine import check_customer_compliance
from backend.app.engines.dashboard_engine import get_dashboard_summary
from backend.app.engines.anomaly_engine import detect_anomalies
from backend.app.ai.copilot import (
    generate_compliance_explanation,
    answer_compliance_question
)

st.set_page_config(
    page_title="KYC Compliance Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stApp {background-color:#0b1220;color:#e5e7eb}
[data-testid="stSidebar"] {background-color:#111c30}
.metric-card {
    background:#17243a;
    border:1px solid #293b57;
    border-radius:12px;
    padding:18px;
}
.metric-label {color:#9caec7;font-size:13px}
.metric-value {color:#ffffff;font-size:27px;font-weight:700}
.section-title {font-size:22px;font-weight:700;color:#e5edf9}
.small-muted {color:#9caec7;font-size:13px}
</style>
""", unsafe_allow_html=True)


def metric_card(label, value):
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'</div>',
        unsafe_allow_html=True
    )


def records_to_df(records, fields):
    return pd.DataFrame([
        {field: getattr(record, field, None) for field in fields}
        for record in records
    ])


def customer_options(db):
    return db.query(Customer).order_by(Customer.customer_id).all()


st.sidebar.title("🛡️ KYC INTELLIGENCE")
st.sidebar.caption("Compliance Monitoring Platform")
page = st.sidebar.radio(
    "NAVIGATION",
    [
        "Executive Dashboard",
        "Customer 360",
        "Document Intelligence",
        "Risk Intelligence",
        "Anomaly Investigation",
        "Review Management",
        "Alerts Center",
        "Audit Trail",
        "AI Compliance Copilot"
    ]
)

st.sidebar.divider()
st.sidebar.caption("KYC Compliance AI System")
st.sidebar.caption("Rules-based compliance intelligence")


with SessionLocal() as db:

    if page == "Executive Dashboard":
        st.title("Executive Dashboard")
        st.caption("Live compliance intelligence from the KYC database")

        with st.spinner("Calculating compliance metrics..."):
            summary = get_dashboard_summary(db)

        columns = st.columns(4)
        metrics = [
            ("Total Customers", summary["total_customers"]),
            ("Compliant Customers", summary["compliant_customers"]),
            ("Non-Compliant", summary["non_compliant_customers"]),
            ("High Risk Customers", summary["high_risk_customers"]),
            ("Open Alerts", summary["active_alerts"]),
            ("Open Reviews", summary["open_reviews"]),
            ("Overdue Reviews", summary["overdue_reviews"]),
            ("Detected Anomalies", summary["total_anomalies"])
        ]

        for index, (label, value) in enumerate(metrics):
            with columns[index % 4]:
                metric_card(label, f"{value:,}")
            if index % 4 == 3 and index != len(metrics) - 1:
                columns = st.columns(4)

        st.divider()
        left, right = st.columns(2)

        with left:
            st.subheader("Customer Compliance")
            compliance_df = pd.DataFrame({
                "Status": ["Compliant", "Non-Compliant"],
                "Customers": [
                    summary["compliant_customers"],
                    summary["non_compliant_customers"]
                ]
            })
            fig = px.pie(
                compliance_df,
                names="Status",
                values="Customers",
                hole=0.62,
                title="Compliance Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)

        with right:
            st.subheader("Operational Risk")
            risk_df = pd.DataFrame({
                "Metric": ["High Risk", "Open Alerts", "Overdue Reviews"],
                "Count": [
                    summary["high_risk_customers"],
                    summary["active_alerts"],
                    summary["overdue_reviews"]
                ]
            })
            fig = px.bar(
                risk_df,
                x="Metric",
                y="Count",
                color="Metric",
                title="Risk and Exception Overview"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.info(summary["message"])

    elif page == "Customer 360":
        st.title("Customer 360")
        st.caption("Customer profile, compliance evidence and history")

        search = st.text_input(
            "Search customer by ID, name or email",
            placeholder="Example: CUS-000001"
        )

        query = db.query(Customer)
        if search:
            query = query.filter(
                (Customer.customer_id.ilike(f"%{search}%")) |
                (Customer.full_name.ilike(f"%{search}%")) |
                (Customer.email.ilike(f"%{search}%"))
            )

        customers = query.order_by(Customer.customer_id).limit(100).all()

        if not customers:
            st.warning("No matching customers found.")
        else:
            selected_id = st.selectbox(
                "Select customer",
                options=[c.customer_id for c in customers],
                format_func=lambda cid: next(
                    f"{c.customer_id} — {c.full_name}" for c in customers
                    if c.customer_id == cid
                )
            )

            customer = db.query(Customer).filter(
                Customer.customer_id == selected_id
            ).first()

            compliance = check_customer_compliance(db, selected_id)

            st.subheader(customer.full_name)
            a, b, c, d = st.columns(4)
            a.metric("Customer ID", customer.customer_id)
            b.metric("Customer Type", customer.customer_type_id)
            c.metric("Account Status", customer.status)
            d.metric("KYC Compliance", compliance["compliance_status"])

            st.divider()
            st.subheader("Compliance Assessment")

            if compliance["compliance_status"] == "COMPLIANT":
                st.success("All evaluated compliance checks passed.")
            else:
                st.error("Compliance exceptions detected.")

            st.json(compliance)

            st.subheader("Customer Documents")
            documents = db.query(Document).filter(
                Document.customer_id == selected_id
            ).all()
            st.dataframe(
                records_to_df(documents, [
                    "document_id", "document_type", "document_number",
                    "issue_date", "expiry_date", "verification_status"
                ]),
                use_container_width=True,
                hide_index=True
            )

            st.subheader("Beneficial Ownership")
            owners = db.query(BeneficialOwner).filter(
                BeneficialOwner.customer_id == selected_id
            ).all()
            st.dataframe(
                records_to_df(owners, [
                    "beneficial_owner_id", "owner_name",
                    "ownership_percentage"
                ]),
                use_container_width=True,
                hide_index=True
            )

    elif page == "Document Intelligence":
        st.title("Document Intelligence")
        st.caption("KYC evidence inventory and verification status")

        total = db.query(Document).count()
        verified = db.query(Document).filter(
            Document.verification_status == "VERIFIED"
        ).count()
        pending = db.query(Document).filter(
            Document.verification_status == "PENDING"
        ).count()
        rejected = db.query(Document).filter(
            Document.verification_status == "REJECTED"
        ).count()

        a, b, c, d = st.columns(4)
        a.metric("Total Documents", f"{total:,}")
        b.metric("Verified", f"{verified:,}")
        c.metric("Pending", f"{pending:,}")
        d.metric("Rejected", f"{rejected:,}")

        status_filter = st.selectbox(
            "Verification status",
            ["ALL", "VERIFIED", "PENDING", "REJECTED"]
        )
        doc_query = db.query(Document)
        if status_filter != "ALL":
            doc_query = doc_query.filter(
                Document.verification_status == status_filter
            )

        docs = doc_query.order_by(
            Document.created_at.desc()
        ).limit(1000).all()

        st.dataframe(
            records_to_df(docs, [
                "document_id", "customer_id", "document_type",
                "document_number", "issue_date", "expiry_date",
                "verification_status", "file_reference"
            ]),
            use_container_width=True,
            hide_index=True
        )
        st.caption("Showing up to 1,000 matching records.")

    elif page == "Risk Intelligence":
        st.title("Risk Intelligence")
        st.caption("Customer risk ratings and risk-score distribution")

        risks = db.query(RiskRating).order_by(
            RiskRating.assessed_at.desc()
        ).all()

        latest = {}
        for risk in risks:
            if risk.customer_id not in latest:
                latest[risk.customer_id] = risk

        risk_records = list(latest.values())
        risk_df = records_to_df(risk_records, [
            "customer_id", "risk_level", "risk_score",
            "reason", "rules_version", "assessed_at"
        ])

        if not risk_df.empty:
            counts = risk_df["risk_level"].value_counts().reset_index()
            counts.columns = ["Risk Level", "Customers"]

            left, right = st.columns(2)
            with left:
                st.plotly_chart(
                    px.pie(counts, names="Risk Level",
                           values="Customers", hole=0.55),
                    use_container_width=True
                )
            with right:
                st.plotly_chart(
                    px.histogram(
                        risk_df, x="risk_score",
                        nbins=20, title="Risk Score Distribution"
                    ),
                    use_container_width=True
                )

            selected_risk = st.selectbox(
                "Filter risk level",
                ["ALL"] + sorted(risk_df["risk_level"].dropna().unique().tolist())
            )
            if selected_risk != "ALL":
                risk_df = risk_df[
                    risk_df["risk_level"] == selected_risk
                ]

            st.dataframe(risk_df, use_container_width=True, hide_index=True)

    elif page == "Anomaly Investigation":
        st.title("Anomaly Investigation")
        st.caption("Rule-based detection of KYC control exceptions")

        with st.spinner("Running anomaly detection rules..."):
            anomalies = detect_anomalies(db)

        st.metric("Total Detected Anomalies", len(anomalies))

        if anomalies:
            anomaly_df = pd.DataFrame(anomalies)
            anomaly_types = ["ALL"] + sorted(
                anomaly_df["anomaly_type"].unique().tolist()
            )
            selected_type = st.selectbox("Anomaly type", anomaly_types)

            if selected_type != "ALL":
                anomaly_df = anomaly_df[
                    anomaly_df["anomaly_type"] == selected_type
                ]

            st.dataframe(
                anomaly_df,
                use_container_width=True,
                hide_index=True
            )
            st.download_button(
                "Download anomaly report",
                anomaly_df.to_csv(index=False),
                "kyc_anomaly_report.csv",
                "text/csv"
            )
        else:
            st.success("No anomalies detected by the current rules.")

    elif page == "Review Management":
        st.title("Review Management")

        reviews = db.query(ReviewCase).order_by(
            ReviewCase.due_date.asc()
        ).limit(2000).all()

        review_df = records_to_df(reviews, [
            "review_case_id", "customer_id", "review_type",
            "risk_level", "opened_date", "due_date",
            "status", "resolution", "closed_date"
        ])

        if not review_df.empty:
            today = date.today()
            overdue = sum(
                1 for r in reviews
                if r.status != "CLOSED" and r.due_date < today
            )
            a, b, c = st.columns(3)
            a.metric("Review Cases", len(reviews))
            b.metric("Open Reviews", sum(r.status != "CLOSED" for r in reviews))
            c.metric("Overdue Reviews", overdue)

            st.dataframe(
                review_df, use_container_width=True, hide_index=True
            )

    elif page == "Alerts Center":
        st.title("Alerts Center")
        alerts = db.query(Alert).order_by(
            Alert.created_date.desc()
        ).limit(2000).all()

        alert_df = records_to_df(alerts, [
            "alert_id", "customer_id", "document_id",
            "review_id", "alert_type", "severity",
            "description", "status", "created_date"
        ])

        if not alert_df.empty:
            open_count = sum(a.status == "OPEN" for a in alerts)
            a, b = st.columns(2)
            a.metric("Total Alerts", len(alerts))
            b.metric("Open Alerts", open_count)

            severity_filter = st.selectbox(
                "Severity",
                ["ALL"] + sorted(
                    alert_df["severity"].dropna().unique().tolist()
                )
            )
            if severity_filter != "ALL":
                alert_df = alert_df[
                    alert_df["severity"] == severity_filter
                ]

            st.dataframe(
                alert_df, use_container_width=True, hide_index=True
            )
        else:
            st.success("No alerts found.")

    elif page == "Audit Trail":
        st.title("Audit Trail")
        st.caption("Historical traceability of customer events")

        customer_id = st.text_input(
            "Customer ID",
            placeholder="CUS-000001"
        )

        if customer_id:
            events = db.query(AuditEvent).filter(
                AuditEvent.customer_id == customer_id
            ).order_by(
                AuditEvent.created_at.desc()
            ).limit(500).all()

            st.metric("Audit Events", len(events))
            st.dataframe(
                records_to_df(events, [
                    "audit_event_id", "entity_type", "entity_id",
                    "action", "actor_role", "event_data", "created_at"
                ]),
                use_container_width=True,
                hide_index=True
            )

    elif page == "AI Compliance Copilot":
        st.title("AI Compliance Copilot")
        st.caption("Customer-specific explanations using deterministic KYC rules")

        customer_id = st.text_input(
            "Customer ID",
            placeholder="CUS-000001"
        )

        if customer_id:
            if st.button("Generate Compliance Explanation"):
                with st.spinner("Analysing customer compliance..."):
                    explanation = generate_compliance_explanation(
                        db, customer_id
                    )
                st.session_state["copilot_explanation"] = explanation

            if "copilot_explanation" in st.session_state:
                st.json(st.session_state["copilot_explanation"])

            st.divider()
            st.subheader("Ask the Compliance Copilot")
            question = st.text_input(
                "Your question",
                placeholder="Which documents are missing?"
            )

            if st.button("Ask Copilot"):
                if question.strip():
                    with st.spinner("Checking customer records..."):
                        answer = answer_compliance_question(
                            db, customer_id, question
                        )
                    st.info(answer["answer"])
                    st.caption("Source: " + answer["source"])
                else:
                    st.warning("Enter a question first.")

st.sidebar.divider()
st.sidebar.caption("Data source: Existing KYC database")
st.sidebar.caption("Read-only demonstration interface")
