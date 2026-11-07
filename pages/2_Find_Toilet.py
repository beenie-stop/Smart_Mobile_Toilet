from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import streamlit as st

import config
from components import cards, maps, navbar
from services import booking_service, van_service
from utils.location import geocode
from utils.validation import valid_coords

user = navbar.setup("Find a Toilet", "🔎", roles=["customer"])
navbar.page_header("Find a toilet near you", "Tell us where you are. We never assume or invent your location.")

with st.container(border=True):
    t1, t2, t3 = st.tabs(["📍 Coordinates", "🔤 Place name", f"🏙️ {config.DEMO_CITY_NAME} centre"])
    with t1:
        c1, c2 = st.columns(2)
        lat = c1.number_input("Latitude", value=None, min_value=-90.0, max_value=90.0, format="%.6f", placeholder="e.g. 17.385000")
        lon = c2.number_input("Longitude", value=None, min_value=-180.0, max_value=180.0, format="%.6f", placeholder="e.g. 78.486700")
        if st.button("Use these coordinates"):
            if lat is None or lon is None or not valid_coords(lat, lon):
                st.error("Enter both latitude and longitude.")
            else:
                st.session_state["loc"] = (lat, lon, "Your coordinates")
                st.rerun()
    with t2:
        if config.GEOCODING_ENABLED:
            q = st.text_input("Area, landmark or address")
            if st.button("Search place"):
                hit = geocode(q)
                if hit:
                    st.session_state["loc"] = hit
                    st.rerun()
                st.error("Place not found. Try more detail or enter coordinates.")
        else:
            st.info("Place-name search is off. Set GEOCODING_ENABLED=true to enable it, or use coordinates.")
    with t3:
        st.caption("Sample locations around this city are labelled DEMO.")
        if st.button(f"Use {config.DEMO_CITY_NAME} city centre"):
            st.session_state["loc"] = (config.DEMO_LAT, config.DEMO_LON, f"{config.DEMO_CITY_NAME} city centre")
            st.rerun()

loc = st.session_state.get("loc")
if not loc:
    st.info("Set your location above to see nearby toilets.")
    st.stop()

st.success(f"Searching around **{loc[2]}** ({loc[0]:.5f}, {loc[1]:.5f})")
radius = st.slider("Search radius (km)", 1, 100, config.DEFAULT_RADIUS_KM)
f = st.columns(5)
avail_now = f[0].checkbox("Available now")
on_demand = f[1].checkbox("On-demand")
stationed = f[2].checkbox("Stationed")
women = f[3].checkbox("Women-friendly")
access = f[4].checkbox("Accessible")

vans = van_service.with_distance(van_service.list_vans(), loc[0], loc[1])
res = van_service.filter_vans(vans, radius, avail_now, on_demand, stationed, women, access)
st.markdown(f"**{len(res)} result(s)** within {radius} km, nearest first.  \n"
            "🚐 Truck marker = mobile on-demand van · 🏢 Building marker = fixed stationed facility.")
maps.show_map(maps.build_map(res, [loc[0], loc[1]], radius, (loc[0], loc[1])), key="find_map")

if res.empty:
    st.warning("Nothing matches. Try a larger radius or fewer filters.")
tz = ZoneInfo(config.TIMEZONE)
for _, v in res.head(20).iterrows():
    st.markdown(cards.van_card(v), unsafe_allow_html=True)
    on = v["service_type"] == "on_demand"
    with st.expander(("Request this van" if on else "Reserve a visit") + f" · {v['van_name']}"):
        with st.form(f"book_{v['id']}"):
            if on:
                st.caption("A van is requested to your searched location. The operator must accept first. "
                           "This MVP has no live GPS tracking; you will see status updates only.")
                when = None
            else:
                st.caption("You visit this facility yourself. No van is dispatched.")
                today = datetime.now(tz).date()
                d = st.date_input("Visit date", value=today, min_value=today, max_value=today + timedelta(days=7), key=f"d_{v['id']}")
                t = st.time_input("Visit time", value=time(10, 0), key=f"t_{v['id']}")
                when = datetime.combine(d, t, tzinfo=tz)
            notes = st.text_input("Notes for the operator (optional)", max_chars=200, key=f"n_{v['id']}")
            label = "Request this van" if on else "Reserve visit"
            if st.form_submit_button(label, type="primary", disabled=v["availability_status"] != "available" and on):
                ok, msg = booking_service.create_booking(
                    user, v["id"], v["service_type"], loc[0], loc[1], when.astimezone(ZoneInfo("UTC")) if when else None, notes)
                if ok:
                    st.success(msg)
                    st.page_link("pages/3_My_Bookings.py", label="Track it in My Bookings", icon="📋")
                else:
                    st.error(msg)
