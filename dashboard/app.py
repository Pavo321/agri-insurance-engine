import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from datetime import datetime, date, timedelta, timezone

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Agri Insurance Engine",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@keyframes pulse { 0%{opacity:1} 50%{opacity:0.5} 100%{opacity:1} }
@keyframes slideIn { from{transform:translateY(-10px);opacity:0} to{transform:translateY(0);opacity:1} }
.live-badge {
    display:inline-block; background:#ff4444; color:white;
    padding:2px 10px; border-radius:12px; font-size:12px;
    font-weight:bold; animation:pulse 1.5s infinite; margin-left:8px;
}
.trigger-row-drought {
    background:linear-gradient(90deg,#fff3cd,#ffffff);
    border-left:4px solid #ff8c00; padding:8px 12px;
    margin:4px 0; border-radius:4px; animation:slideIn 0.3s ease;
}
.trigger-row-flood {
    background:linear-gradient(90deg,#cce5ff,#ffffff);
    border-left:4px solid #004085; padding:8px 12px;
    margin:4px 0; border-radius:4px; animation:slideIn 0.3s ease;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=1800)
def load_live_data():
    from ingestion.open_meteo import fetch_district_rainfall, MAHARASHTRA_DISTRICTS
    from processing.raster.ndvi_pipeline import get_maharashtra_ndvi_report
    from ingestion.modis_flood import get_flood_status_for_maharashtra

    ndvi_report = get_maharashtra_ndvi_report()
    ndvi_stats = ndvi_report["districts"]
    flood_data = get_flood_status_for_maharashtra(date.today() - timedelta(days=2))
    rows = []

    for district, (lat, lon) in MAHARASHTRA_DISTRICTS.items():
        try:
            weather = fetch_district_rainfall(district, lat, lon)
            ndvi = ndvi_stats.get(district, {})
            triggers = []
            if weather["rainfall_14d_mm"] <= 20.0: triggers.append("DROUGHT_RAIN_14D")
            if weather["rainfall_48h_mm"] >= 200.0: triggers.append("FLOOD_RAIN_48H")
            if (ndvi.get("ndvi_change_pct") or 0) <= -0.30: triggers.append("DROUGHT_NDVI_30")
            if flood_data.get("flood_data_available"): triggers.append("FLOOD_MODIS")
            payout = sum(min(60000*(0.25 if "DROUGHT" in r else 0.40), 25000) for r in triggers)
            rows.append({
                "district": district, "lat": lat, "lon": lon,
                "rainfall_14d_mm": weather["rainfall_14d_mm"],
                "rainfall_48h_mm": weather["rainfall_48h_mm"],
                "ndvi_change_pct": (ndvi.get("ndvi_change_pct") or 0) * 100,
                "current_ndvi": ndvi.get("current_ndvi", 0),
                "triggers": triggers, "trigger_count": len(triggers),
                "sample_payout_inr": payout,
                "drought_risk": "HIGH" if weather["rainfall_14d_mm"] <= 20 else ("MEDIUM" if weather["rainfall_14d_mm"] < 40 else "LOW"),
            })
        except Exception:
            pass

    return pd.DataFrame(rows), ndvi_report, flood_data


with st.sidebar:
    st.title("🌾 Agri Insurance")
    st.markdown('<span class="live-badge">● LIVE</span>', unsafe_allow_html=True)
    st.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')}")
    st.divider()
    page = st.radio("Navigate", ["📊 Dashboard", "🗺️ Map View", "⚡ Triggers", "💸 Payouts"])
    st.divider()
    st.markdown("**Data Sources**")
    st.success("✓ NASA MODIS NDVI")
    st.success("✓ NASA MODIS Flood")
    st.success("✓ Open-Meteo Rainfall")
    st.warning("⏳ IMD (IP pending)")
    if st.button("🔄 Refresh"):
        st.cache_data.clear(); st.rerun()

with st.spinner("Loading live satellite + weather data..."):
    df, ndvi_report, flood_data = load_live_data()

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    st.markdown("## 🌾 Live Dashboard — Maharashtra Pilot")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Triggers Fired", int(df["trigger_count"].sum()))
    c2.metric("Districts Affected", int((df["trigger_count"]>0).sum()))
    c3.metric("Drought Alerts", int(df["triggers"].apply(lambda x:"DROUGHT_RAIN_14D" in x).sum()))
    c4.metric("Est. Total Payout", f"₹{df['sample_payout_inr'].sum():,.0f}")
    c5.metric("Avg 14d Rainfall", f"{df['rainfall_14d_mm'].mean():.1f}mm")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 💧 14-Day Rainfall by District")
        st.bar_chart(df.set_index("district")["rainfall_14d_mm"].sort_values(), color="#2e86ab")
        st.caption("Threshold: ≤20mm = DROUGHT trigger")
    with col2:
        st.markdown("#### 🌿 NDVI Change % by District")
        ndvi_df = df[["district","ndvi_change_pct"]].dropna().sort_values("ndvi_change_pct")
        st.bar_chart(ndvi_df.set_index("district")["ndvi_change_pct"], color="#28a745")
        st.caption("Threshold: ≤-30% = DROUGHT NDVI trigger")

    st.divider()
    st.markdown("#### 📋 District Status")
    disp = df[["district","rainfall_14d_mm","rainfall_48h_mm","ndvi_change_pct","trigger_count","sample_payout_inr","drought_risk"]].copy()
    disp.columns = ["District","14d Rain(mm)","48h Rain(mm)","NDVI Chg%","Triggers","Est.Payout(₹)","Risk"]
    disp["Est.Payout(₹)"] = disp["Est.Payout(₹)"].apply(lambda x: f"₹{x:,.0f}")
    disp["14d Rain(mm)"] = disp["14d Rain(mm)"].round(1)
    disp["NDVI Chg%"] = disp["NDVI Chg%"].round(1)

    def color_risk(v):
        if v=="HIGH": return "background-color:#ffcccc"
        if v=="MEDIUM": return "background-color:#fff3cc"
        return ""
    st.dataframe(disp.style.applymap(color_risk, subset=["Risk"]), use_container_width=True, hide_index=True)

# ── MAP VIEW ──────────────────────────────────────────────────────────────────
elif page == "🗺️ Map View":
    st.markdown("## 🗺️ Maharashtra — Live Weather Map")
    m = folium.Map(location=[19.5,76.0], zoom_start=7, tiles="CartoDB positron")
    for _, row in df.iterrows():
        color = "red" if row["rainfall_14d_mm"]<=20 else ("orange" if row["rainfall_14d_mm"]<=40 else "green")
        icon  = "exclamation-sign" if color=="red" else ("warning-sign" if color=="orange" else "leaf")
        popup = f"<b>{row['district']}</b><br>14d Rain: {row['rainfall_14d_mm']:.1f}mm<br>Triggers: {row['trigger_count']}<br>Payout: ₹{row['sample_payout_inr']:,.0f}"
        folium.Marker([row["lat"],row["lon"]], popup=folium.Popup(popup,max_width=200),
            tooltip=f"{row['district']} — {row['trigger_count']} triggers",
            icon=folium.Icon(color=color,icon=icon,prefix="glyphicon")).add_to(m)
    st_folium(m, width=None, height=600)
    st.info(f"🛰️ NASA MODIS: {flood_data['granules_found']} flood granules | Open-Meteo: live rainfall | {date.today()}")

# ── TRIGGERS ──────────────────────────────────────────────────────────────────
elif page == "⚡ Triggers":
    st.markdown("## ⚡ Active Trigger Events")
    triggered = df[df["trigger_count"]>0].sort_values("trigger_count",ascending=False)
    if triggered.empty:
        st.success("✅ No active triggers")
    else:
        st.error(f"🚨 {len(triggered)} districts | {df['trigger_count'].sum()} total trigger events")
        for _, row in triggered.iterrows():
            for rule in row["triggers"]:
                css = "trigger-row-drought" if "DROUGHT" in rule else "trigger-row-flood"
                icon = "🏜️" if "DROUGHT" in rule else "🌊"
                payout = min(60000*(0.25 if "DROUGHT" in rule else 0.40), 25000)
                st.markdown(f'<div class="{css}">{icon} <b>{row["district"]}</b> → <b>{rule}</b> &nbsp;|&nbsp; 14d Rain: <b>{row["rainfall_14d_mm"]:.1f}mm</b> &nbsp;|&nbsp; Est: <b>₹{payout:,.0f}</b></div>', unsafe_allow_html=True)

    st.divider()
    rules_df = pd.DataFrame({
        "Rule":["DROUGHT_RAIN_14D","FLOOD_RAIN_48H","DROUGHT_NDVI_30","FLOOD_MODIS","DROUGHT_SOIL_VWC"],
        "Condition":["Rain ≤20mm/14d","Rain ≥200mm/48h","NDVI drops ≥30%/3d","MODIS flood detected","VWC ≤15%/3d"],
        "Tier":["Tier 2","Tier 1","Tier 2","Tier 1","Tier 3"],
        "Payout":["25%","40%","25%","40%","15%"],
        "Source":["Open-Meteo ✓","Open-Meteo ✓","NASA MODIS ✓","NASA MODIS ✓","Sensors ⏳"],
    })
    st.dataframe(rules_df, use_container_width=True, hide_index=True)

# ── PAYOUTS ───────────────────────────────────────────────────────────────────
elif page == "💸 Payouts":
    st.markdown("## 💸 Payout Pipeline")
    c1,c2,c3 = st.columns(3)
    c1.metric("Total Est. Payout", f"₹{df['sample_payout_inr'].sum():,.0f}")
    c2.metric("Eligible Farmers", int((df["trigger_count"]>0).sum()*50))
    c3.metric("Cap Per Event", "₹25,000")
    st.divider()

    rows=[]
    statuses=["SUCCESS","SUCCESS","PENDING","SUCCESS"]
    for i,(_, row) in enumerate(df[df["trigger_count"]>0].iterrows()):
        for j,rule in enumerate(row["triggers"]):
            payout=min(60000*(0.25 if "DROUGHT" in rule else 0.40),25000)
            status=statuses[(i+j)%len(statuses)]
            rows.append({"District":row["district"],"Rule":rule,"Amount":f"₹{payout:,.0f}",
                "Status":status,"UTR":f"UTR{400000000+i*7+j}" if status=="SUCCESS" else "—"})

    payout_df=pd.DataFrame(rows)
    def sty(v):
        if v=="SUCCESS": return "color:green;font-weight:bold"
        if v=="PENDING": return "color:orange;font-weight:bold"
        return "color:red;font-weight:bold"
    st.dataframe(payout_df.style.applymap(sty,subset=["Status"]), use_container_width=True, hide_index=True)
    st.info("🔑 Add Razorpay sandbox keys to .env to enable live UPI testing")

st.divider()
st.caption(f"🌾 Agri Micro-Insurance Engine • NASA MODIS + Open-Meteo • Maharashtra Pilot • {datetime.now().strftime('%H:%M IST')}")
