import streamlit as st

st.set_page_config(
    page_title="Agri Insurance Engine",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Animated header ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@keyframes pulse {
    0%   { opacity: 1; }
    50%  { opacity: 0.4; }
    100% { opacity: 1; }
}
.live-badge {
    display: inline-block;
    background: #e74c3c;
    color: white;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
    animation: pulse 1.5s infinite;
    margin-left: 10px;
}
.metric-card {
    background: linear-gradient(135deg, #1a5276, #2e86c1);
    border-radius: 12px;
    padding: 20px;
    color: white;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

st.title("🌾 Agricultural Micro-Insurance Engine")
st.markdown('<span class="live-badge">● LIVE</span>', unsafe_allow_html=True)
st.caption("Pilot: Maharashtra | 24-hour payout SLA | Satellite + Sensor powered")

# ── Navigation ─────────────────────────────────────────────────────────────────
page = st.sidebar.selectbox(
    "Navigate",
    ["Overview", "Event Log", "Payout Status", "Map View"],
)

if page == "Overview":
    from dashboard.pages.overview import render
    render()
elif page == "Event Log":
    from dashboard.pages.event_log import render
    render()
elif page == "Payout Status":
    from dashboard.pages.payout_status import render
    render()
elif page == "Map View":
    from dashboard.pages.map_view import render
    render()
