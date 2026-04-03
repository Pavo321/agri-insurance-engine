import streamlit as st
import folium
from streamlit_folium import st_folium


def render():
    st.header("Farm Map — Maharashtra Pilot")
    st.caption("Farm polygons coloured by NDVI health | Red markers = triggered events")

    # Maharashtra center coordinates
    MH_CENTER = [19.7515, 75.7139]

    m = folium.Map(
        location=MH_CENTER,
        zoom_start=7,
        tiles="CartoDB positron",
    )

    # Sample farm polygon — Pune district
    sample_farm = {
        "type": "Feature",
        "properties": {"farmer": "Ramesh Patil", "ndvi": 0.42, "status": "TRIGGERED"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [73.856, 18.520],
                [73.860, 18.520],
                [73.860, 18.524],
                [73.856, 18.524],
                [73.856, 18.520],
            ]]
        }
    }

    folium.GeoJson(
        sample_farm,
        style_function=lambda f: {
            "fillColor": "#e74c3c" if f["properties"]["status"] == "TRIGGERED" else "#2ecc71",
            "color": "#2c3e50",
            "weight": 1.5,
            "fillOpacity": 0.5,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["farmer", "ndvi", "status"],
            aliases=["Farmer", "NDVI", "Status"],
        ),
    ).add_to(m)

    # Pulsing marker for triggered farm
    folium.CircleMarker(
        location=[18.522, 73.858],
        radius=15,
        color="#e74c3c",
        fill=True,
        fill_color="#e74c3c",
        fill_opacity=0.6,
        popup="⚡ FLOOD_RAIN_48H triggered — Ramesh Patil",
    ).add_to(m)

    # Layer control
    folium.LayerControl().add_to(m)

    st_folium(m, width=None, height=550, returned_objects=[])

    st.caption("Live farm polygons load after database has registered farmers (Phase 1).")
