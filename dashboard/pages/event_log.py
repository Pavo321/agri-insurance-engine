import streamlit as st
import pandas as pd


def render():
    st.header("Trigger Event Log")
    st.caption("All parametric rule trigger events — Maharashtra pilot")

    col1, col2, col3 = st.columns(3)
    with col1:
        rule_filter = st.selectbox("Filter by Rule", [
            "All Rules",
            "DROUGHT_NDVI_30",
            "FLOOD_RAIN_48H",
            "DROUGHT_RAIN_14D",
            "FLOOD_MODIS",
            "DROUGHT_SOIL_VWC",
        ])
    with col2:
        event_type = st.selectbox("Event Type", ["All", "flood", "drought"])
    with col3:
        date_range = st.date_input("Date Range", [])

    # Placeholder data — replace with DB query in Phase 4
    sample_data = {
        "Date": ["2026-04-03", "2026-04-03"],
        "Rule": ["FLOOD_RAIN_48H", "DROUGHT_NDVI_30"],
        "Event Type": ["🌊 flood", "🌵 drought"],
        "District": ["Pune", "Nashik"],
        "Farms Affected": [142, 87],
        "Total Payout (₹)": ["₹12,45,000", "₹7,82,000"],
        "Status": ["✅ Paid", "🟡 Pending"],
    }

    df = pd.DataFrame(sample_data)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    st.caption("Live data available after Phase 4 (Rules Engine) implementation.")
