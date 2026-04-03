import streamlit as st
import pandas as pd


STATUS_COLORS = {
    "SUCCESS": "🟢",
    "PENDING": "🟡",
    "FAILED": "🔴",
    "QUEUED": "⚪",
}


def render():
    st.header("Payout Status")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Successful", "0", delta=None)
    with col2:
        st.metric("Pending", "0")
    with col3:
        st.metric("Failed", "0")

    st.divider()

    # Placeholder — replace with payout_records DB query in Phase 5
    sample = {
        "Farmer": ["Ramesh Patil", "Sunita Jadhav"],
        "Farm ID": ["...abc123", "...def456"],
        "Rule": ["FLOOD_RAIN_48H", "DROUGHT_NDVI_30"],
        "Amount (₹)": ["₹20,000", "₹12,500"],
        "UPI ID": ["r.patil@upi", "s.jadhav@upi"],
        "UTR": ["UPI12345678", "–"],
        "Status": ["SUCCESS", "PENDING"],
    }
    df = pd.DataFrame(sample)

    # Color-code status column
    def color_status(val):
        colors = {"SUCCESS": "background-color: #d5f5e3",
                  "PENDING": "background-color: #fef9e7",
                  "FAILED":  "background-color: #fdedec"}
        return colors.get(val, "")

    styled = df.style.applymap(color_status, subset=["Status"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.caption("Live data available after Phase 5 (Payout Engine) implementation.")
