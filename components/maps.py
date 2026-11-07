import folium
from streamlit_folium import st_folium

import config


def build_map(vans, center, radius_km=None, user_point=None):
    m = folium.Map(location=center, zoom_start=12, tiles="OpenStreetMap", control_scale=True)
    if user_point:
        folium.Marker(user_point, tooltip="Your searched location", icon=folium.Icon(color="darkblue", icon="user", prefix="fa")).add_to(m)
        if radius_km:
            folium.Circle(user_point, radius=radius_km * 1000, color=config.BLUE, weight=1, fill=True, fill_opacity=0.05).add_to(m)
    color_map = {"available": "green", "busy": "orange", "unavailable": "red", "maintenance": "red"}
    for _, v in vans.iterrows():
        stationed = v["service_type"] == "stationed"
        kind = "Stationed facility (fixed)" if stationed else "Mobile van (on-demand)"
        dist = f"<br>{v['distance_km']:.1f} km away" if "distance_km" in v else ""
        html = f"<b>{v['van_name']}</b><br>{kind}<br>Status: {v['availability_status']}<br>Hours: {v['operating_hours']}{dist}"
        folium.Marker(
            [v["latitude"], v["longitude"]], tooltip=v["van_name"], popup=folium.Popup(html, max_width=240),
            icon=folium.Icon(color=color_map.get(v["availability_status"], "gray"),
                             icon="building" if stationed else "truck", prefix="fa"),
        ).add_to(m)
    return m


def show_map(m, height=430, key="map"):
    st_folium(m, height=height, use_container_width=True, returned_objects=[], key=key)
