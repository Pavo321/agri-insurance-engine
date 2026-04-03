import streamlit as st
import time


def render():
    st.header("System Overview")

    # Auto-refresh every 30 seconds
    st_autorefresh = st.empty()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Farms Monitored", "0", help="Active farms with policies in Maharashtra")
    with col2:
        st.metric("Events Today", "0", help="Trigger events fired today")
    with col3:
        st.metric("Payouts Today (₹)", "0", help="Total INR paid out today")
    with col4:
        st.metric("Pending Payouts", "0", help="Payouts awaiting UPI confirmation")

    st.divider()

    st.subheader("Pipeline Status")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("**IMD Weather Ingestion**")
        st.success("Last run: --")

    with col_b:
        st.markdown("**NDVI Processing**")
        st.info("Last run: --")

    with col_c:
        st.markdown("**Rules Engine**")
        st.info("Last run: --")

    st.divider()
    st.caption("Data updates every 30 seconds. Connect database to see live data.")
