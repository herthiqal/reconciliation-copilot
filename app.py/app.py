import streamlit as st
import pandas as pd
import io

st.set_page_config(
    page_title="Reconciliation Copilot",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ Reconciliation Copilot")
st.caption("AI-powered transaction matching, exception explanation, and audit reporting.")

# --- SIDEBAR & DEMO DATA GENERATION ---
st.sidebar.header("1. Data Input")

def get_demo_data():
    bank_df = pd.DataFrame([
        {"TXN_ID": "TXN001", "Date": "2026-07-20", "Amount": 1500.00, "Description": "Payout - Merchant A"},
        {"TXN_ID": "TXN002", "Date": "2026-07-21", "Amount": 850.50, "Description": "Payout - Merchant B"},
        {"TXN_ID": "TXN003", "Date": "2026-07-21", "Amount": 2200.00, "Description": "Wire Transfer Ref 99"},
        {"TXN_ID": "TXN004", "Date": "2026-07-22", "Amount": 430.00, "Description": "Payout - Merchant C"},
    ])
    
    internal_df = pd.DataFrame([
        {"REF_ID": "TXN001", "Date": "2026-07-20", "Amount": 1500.00, "Ledger_Account": "Sales Revenue"},
        {"REF_ID": "TXN002", "Date": "2026-07-21", "Amount": 800.50, "Ledger_Account": "Sales Revenue"}, # $50 fee mismatch
        {"REF_ID": "TXN003", "Date": "2026-07-21", "Amount": 2200.00, "Ledger_Account": "Direct Deposit"},
        {"REF_ID": "TXN005", "Date": "2026-07-22", "Amount": 1200.00, "Ledger_Account": "Vendor Payment"}, # Missing from Bank
    ])
    return bank_df, internal_df

use_demo = st.sidebar.checkbox("Use Demo Benchmark Dataset", value=True)

if use_demo:
    bank_data, internal_data = get_demo_data()
else:
    bank_file = st.sidebar.file_uploader("Upload Bank Statement (CSV)", type=["csv"])
    internal_file = st.sidebar.file_uploader("Upload Internal Ledger (CSV)", type=["csv"])
    if bank_file and internal_file:
        bank_data = pd.read_csv(bank_file)
        internal_data = pd.read_csv(internal_file)
    else:
        st.info("Please upload CSV files or check 'Use Demo Benchmark Dataset'.")
        st.stop()

# Display Raw Inputs
col1, col2 = st.columns(2)
with col1:
    st.subheader("Bank Statement Data")
    st.dataframe(bank_data, use_container_width=True)

with col2:
    st.subheader("Internal Ledger Data")
    st.dataframe(internal_data, use_container_width=True)

st.markdown("---")

# --- RECONCILIATION ENGINE ---
st.header("2. Automated Matching & Exception Analysis")

# Merge on ID
merged = pd.merge(
    bank_data,
    internal_data,
    left_on="TXN_ID",
    right_on="REF_ID",
    how="outer",
    suffixes=("_Bank", "_Internal")
)

def analyze_status(row):
    if pd.isna(row["TXN_ID"]):
        return "Missing in Bank"
    elif pd.isna(row["REF_ID"]):
        return "Missing in Internal Ledger"
    elif row["Amount_Bank"] != row["Amount_Internal"]:
        return "Amount Mismatch"
    else:
        return "Matched"

merged["Status"] = merged.apply(analyze_status, axis=1)

# Metrics
matched_cnt = len(merged[merged["Status"] == "Matched"])
mismatch_cnt = len(merged[merged["Status"] != "Matched"])

m1, m2, m3 = st.columns(3)
m1.metric("Total Processed", len(merged))
m2.metric("Matched Records", matched_cnt)
m3.metric("Exceptions Found", mismatch_cnt, delta_color="inverse")

st.subheader("Reconciliation Table")
st.dataframe(merged[["TXN_ID", "REF_ID", "Amount_Bank", "Amount_Internal", "Status"]], use_container_width=True)

# --- COPILOT EXPLANATIONS ---
st.subheader("🤖 Copilot Exception Explanations")

exceptions = merged[merged["Status"] != "Matched"]

if len(exceptions) == 0:
    st.success("All records matched perfectly!")
else:
    for idx, row in exceptions.iterrows():
        status = row["Status"]
        if status == "Amount Mismatch":
            diff = row["Amount_Bank"] - row["Amount_Internal"]
            explanation = (
                f"**Transaction {row['TXN_ID']}:** Bank records show **${row['Amount_Bank']:,.2f}** "
                f"while Internal Ledger shows **${row['Amount_Internal']:,.2f}** (Variance: **${diff:,.2f}**). "
                f"\n*Copilot Diagnosis:* Possible standard processing fee or commission deduction during settlement."
            )
            st.warning(explanation)
        elif status == "Missing in Internal Ledger":
            explanation = (
                f"**Transaction {row['TXN_ID']}:** Received **${row['Amount_Bank']:,.2f}** in bank, "
                f"but no corresponding entry exists in internal ledger. "
                f"\n*Copilot Diagnosis:* Unrecorded incoming transaction or delayed batch ledger posting."
            )
            st.error(explanation)
        elif status == "Missing in Bank":
            explanation = (
                f"**Internal Ref {row['REF_ID']}:** Expected payout of **${row['Amount_Internal']:,.2f}** logged, "
                f"but missing from bank statement. "
                f"\n*Copilot Diagnosis:* Transaction pending bank clearance or canceled payment."
            )
            st.error(explanation)

st.markdown("---")

# --- AUDITABLE REPORT GENERATION ---
st.header("3. Auditable Report Generation")

report_df = merged.copy()
report_df["Audit_Notes"] = report_df["Status"].apply(
    lambda x: "Verified by Copilot" if x == "Matched" else "Requires Manager Approval"
)

csv_buffer = io.StringIO()
report_df.to_csv(csv_buffer, index=False)

st.download_button(
    label="📥 Download Auditable CSV Report",
    data=csv_buffer.getvalue(),
    file_name="reconciliation_audit_report.csv",
    mime="text/csv"
)