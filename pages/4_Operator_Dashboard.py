import random

import streamlit as st

import config
from components import cards, navbar
from services import auth_service, booking_service, van_service

user = navbar.setup("Operator Dashboard", "🚐", roles=["operator"])
navbar.page_header("Van operator dashboard", "Manage requests, your van, tanks and maintenance.")
demo = auth_service.is_demo()

vans = van_service.list_vans()
mine = vans[vans["operator_id"] == user["id"]].reset_index(drop=True)
if mine.empty:
    st.info("No van is assigned to your account yet. Ask an administrator to assign one.")
    st.stop()

label = st.selectbox("Your van", mine["van_name"]) if len(mine) > 1 else mine.loc[0, "van_name"]
van = mine[mine["van_name"] == label].iloc[0]
vid = van["id"]
bk = booking_service.list_bookings(user)
bk = bk[bk["van_id"] == vid]


def done(ok, msg):
    (st.success if ok else st.error)(msg)
    if ok:
        st.rerun()


kind = "Stationed facility" if van["service_type"] == "stationed" else "Mobile van"
st.markdown(f"**{van['van_name']}** · {kind} · {van['address']}  \n"
            f"{cards.availability_badge(van['availability_status'])} 🕒 {van['operating_hours']}", unsafe_allow_html=True)
c = st.columns(2)
for col, name, lvl, cap in [(c[0], "Water tank", van["water_level"], van["water_capacity"]),
                            (c[1], "Waste tank", van["waste_level"], van["waste_capacity"])]:
    col.progress(min(lvl / cap, 1.0), text=f"{name}: {lvl:.0f} / {cap:.0f} L")
st.caption("🧪 DEMO DATA: tank levels are simulated. No IoT sensors are connected." if demo
           else "Tank levels are entered manually by operators. No IoT sensors are connected in this MVP.")

t_req, t_act, t_van, t_clean, t_maint, t_hist = st.tabs(
    ["📥 New requests", "🚚 Active jobs", "⚙️ Van settings", "🧼 Cleaning & tanks", "🛠 Maintenance", "📜 History"])

with t_req:
    new = bk[bk["status"] == "requested"]
    if new.empty:
        st.info("No new requests right now.")
    for _, r in new.iterrows():
        when = r["scheduled_at"].tz_convert(config.TIMEZONE)
        st.markdown(f'<div class="card"><h4>{config.SERVICE_LABELS[r["booking_type"]]} request · {r["customer_name"]}</h4>'
                    f'<div class="muted">For {when:%d %b, %H:%M}'
                    + (f' · user at {r["user_latitude"]:.4f}, {r["user_longitude"]:.4f}' if r["booking_type"] == "on_demand" else "")
                    + (f'<br>Note: {r["notes"]}' if r["notes"] else "") + "</div></div>", unsafe_allow_html=True)
        a, b, _ = st.columns([1, 1, 3])
        if a.button("Accept", key=f"a_{r['id']}", type="primary"):
            done(*booking_service.update_status(user, r["id"], "accepted"))
        if b.button("Reject", key=f"r_{r['id']}"):
            done(*booking_service.update_status(user, r["id"], "rejected"))

with t_act:
    act = bk[bk["status"].isin(["accepted", "assigned", "on_the_way", "arrived"])]
    if act.empty:
        st.info("No active jobs.")
    for _, r in act.iterrows():
        st.markdown(f"**{r['customer_name']}** · {config.SERVICE_LABELS[r['booking_type']]}")
        st.markdown(cards.status_tracker(r["status"], r["booking_type"]), unsafe_allow_html=True)
        nxt = config.NEXT_STATUS[r["booking_type"]].get(r["status"], [])
        cols = st.columns(len(nxt) or 1)
        for col, s in zip(cols, nxt):
            if col.button(f"Mark {config.status_label(s, r['booking_type']).lower()}", key=f"s_{r['id']}_{s}"):
                done(*booking_service.update_status(user, r["id"], s))
        st.divider()
    st.caption("Status updates are manual. No live GPS dispatch is simulated or implied.")

with t_van:
    with st.form("van_settings"):
        avail = st.selectbox("Availability", config.AVAILABILITY, index=config.AVAILABILITY.index(van["availability_status"]))
        hours = st.text_input("Operating hours (06:00-22:00 or 24x7)", value=van["operating_hours"])
        addr = st.text_input("Location name / address", value=van["address"] or "")
        a, b = st.columns(2)
        lat = a.number_input("Latitude", value=float(van["latitude"]), format="%.6f", min_value=-90.0, max_value=90.0)
        lon = b.number_input("Longitude", value=float(van["longitude"]), format="%.6f", min_value=-180.0, max_value=180.0)
        if st.form_submit_button("Save changes", type="primary"):
            done(*van_service.operator_update(vid, availability_status=avail, operating_hours=hours,
                                              address=addr, latitude=lat, longitude=lon))
    st.caption("Location is updated manually. There is no live GPS feed in this MVP.")

with t_clean:
    if demo and st.button("Simulate sensor readings (DEMO DATA)"):
        done(*van_service.operator_update(vid, water_level=round(van["water_capacity"] * random.uniform(0.2, 0.95)),
                                          waste_level=round(van["waste_capacity"] * random.uniform(0.05, 0.8))))
    with st.form("levels"):
        a, b = st.columns(2)
        wl = a.number_input("Water level (L)", 0.0, float(van["water_capacity"]), float(van["water_level"]))
        sl = b.number_input("Waste level (L)", 0.0, float(van["waste_capacity"]), float(van["waste_level"]))
        if st.form_submit_button("Update tank levels"):
            done(*van_service.operator_update(vid, water_level=wl, waste_level=sl))
    with st.form("cleaning", clear_on_submit=True):
        notes = st.text_input("Cleaning notes", max_chars=300)
        partial = st.checkbox("Partial clean")
        e1, e2 = st.columns(2)
        emptied = e1.checkbox("Waste tank emptied")
        refilled = e2.checkbox("Water tank refilled")
        if st.form_submit_button("Record cleaning", type="primary"):
            done(*van_service.log_cleaning(vid, user["id"], notes, partial, emptied, refilled))
    logs = van_service.list_cleaning_logs(vans, {vid}).sort_values("cleaned_at", ascending=False)
    st.dataframe(logs[["cleaned_at", "status", "cleaning_notes"]].head(10), hide_index=True, width="stretch")

with t_maint:
    with st.form("maint", clear_on_submit=True):
        issue = st.text_area("Describe the maintenance requirement", max_chars=500)
        if st.form_submit_button("Report issue", type="primary"):
            done(*van_service.report_maintenance(vid, user["id"], issue))
    ml = van_service.list_maintenance_logs(vans, {vid}).sort_values("reported_at", ascending=False)
    st.dataframe(ml[["reported_at", "issue", "resolution_status"]], hide_index=True, width="stretch")
    open_ = ml[ml["resolution_status"] != "resolved"]
    if not open_.empty:
        with st.form("maint_status"):
            pick = st.selectbox("Update an issue", open_["id"], format_func=lambda i: open_.set_index("id").loc[i, "issue"])
            new_s = st.selectbox("New status", ["in_progress", "resolved"])
            if st.form_submit_button("Update status"):
                done(*van_service.set_maintenance_status(pick, new_s))

with t_hist:
    h = bk[bk["status"].isin(["completed", "cancelled", "rejected"])]
    st.dataframe(h[["requested_at", "customer_name", "booking_type", "status_label"]], hide_index=True, width="stretch")
