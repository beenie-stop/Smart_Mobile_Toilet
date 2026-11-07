import pandas as pd
import streamlit as st

import config
from components import cards, charts, navbar
from services import analytics_service as an
from services import auth_service, booking_service, repo, van_service

user = navbar.setup("Admin Dashboard", "🛠️", roles=["admin"])
navbar.page_header("Service management console", "Fleet, bookings, people, quality and analytics.")


def done(ok, msg):
    (st.success if ok else st.error)(msg)
    if ok:
        st.rerun()


profiles = repo.select("profiles", order="created_at")
vans = van_service.list_vans()
bk = booking_service.list_bookings(user)
fb = booking_service.list_feedback(user, bk)
cp = booking_service.list_complaints(vans)
m = an.compute_metrics(profiles, vans, bk)
operators = [p for p in profiles if p["role"] == "operator"]
op_label = {p["id"]: f"{p['full_name'] or p['email']}" for p in operators}

tabs = st.tabs(["Overview", "Vans", "Stationed", "Users", "Bookings", "Cleaning & maintenance", "Feedback & complaints", "Analytics"])

with tabs[0]:
    rows = [[("Registered users", m["users"], config.TEAL), ("Total vans", m["vans"], config.BLUE),
             ("Available vans", m["available"], config.GREEN), ("Unavailable / busy", m["unavailable"], config.RED)],
            [("Total bookings", m["bookings"], config.TEAL), ("Active requests", m["active"], config.ORANGE),
             ("Completed", m["completed"], config.GREEN), ("Cancelled", m["cancelled"], config.RED)]]
    for row in rows:
        for col, (l, v, c) in zip(st.columns(4), row):
            col.markdown(cards.metric_card(l, v, c), unsafe_allow_html=True)
    a, b = st.columns([3, 2])
    a.plotly_chart(charts.trend(an.bookings_per_day(bk)), width="stretch")
    b.plotly_chart(charts.status_donut(an.status_counts(bk)), width="stretch")


def van_form(prefix, existing=None, force_type=None):
    e = existing
    ek = e["id"] if e is not None else "new"
    k = lambda n: f"{prefix}_{ek}_{n}"
    catalog = config.FACILITIES
    with st.form(k("form")):
        name = st.text_input("Name", value=e["van_name"] if e is not None else "", key=k("name"))
        types = list(config.SERVICE_LABELS)
        stype = force_type or st.selectbox("Service type", types, format_func=config.SERVICE_LABELS.get,
                                           index=types.index(e["service_type"]) if e is not None else 0, key=k("type"))
        addr = st.text_input("Address / location name", value=(e["address"] or "") if e is not None else "", key=k("addr"))
        a, b = st.columns(2)
        lat = a.number_input("Latitude", value=float(e["latitude"]) if e is not None else float(config.DEMO_LAT), format="%.6f", key=k("lat"))
        lon = b.number_input("Longitude", value=float(e["longitude"]) if e is not None else float(config.DEMO_LON), format="%.6f", key=k("lon"))
        c1, c2 = st.columns(2)
        avail = c1.selectbox("Availability", config.AVAILABILITY, key=k("av"),
                             index=config.AVAILABILITY.index(e["availability_status"]) if e is not None else 0)
        hours = c2.text_input("Operating hours", value=e["operating_hours"] if e is not None else "06:00-22:00", key=k("hrs"))
        d1, d2, d3, d4 = st.columns(4)
        wc = d1.number_input("Water capacity (L)", 1.0, value=float(e["water_capacity"]) if e is not None else 500.0, key=k("wc"))
        wl = d2.number_input("Water level (L)", 0.0, value=float(e["water_level"]) if e is not None else 0.0, key=k("wl"))
        sc = d3.number_input("Waste capacity (L)", 1.0, value=float(e["waste_capacity"]) if e is not None else 300.0, key=k("sc"))
        sl = d4.number_input("Waste level (L)", 0.0, value=float(e["waste_level"]) if e is not None else 0.0, key=k("sl"))
        ops = [None] + list(op_label)
        cur = e["operator_id"] if e is not None and e["operator_id"] in op_label else None
        op = st.selectbox("Assigned operator", ops, index=ops.index(cur), format_func=lambda x: "Unassigned" if x is None else op_label[x], key=k("op"))
        facs = st.multiselect("Facilities on this unit", catalog, default=list(e["facilities"]) if e is not None else catalog[:3], key=k("fac"))
        if st.form_submit_button("Save", type="primary"):
            data = {"van_name": name, "service_type": stype, "latitude": lat, "longitude": lon, "address": addr,
                    "availability_status": avail, "operating_hours": hours, "water_capacity": wc, "water_level": wl,
                    "waste_capacity": sc, "waste_level": sl, "operator_id": op}
            done(*van_service.save_van(data, facs, e["id"] if e is not None else None))


with tabs[1]:
    st.dataframe(vans[["van_name", "service_type", "availability_status", "operating_hours", "operator_name", "water_level", "waste_level", "facilities"]],
                 hide_index=True, width="stretch")
    choice = st.selectbox("Add or edit", ["➕ New van"] + list(vans["van_name"]), key="van_pick")
    existing = None if choice.startswith("➕") else vans[vans["van_name"] == choice].iloc[0]
    van_form("v", existing)
    if existing is not None:
        ok_del = st.checkbox(f"Confirm: permanently remove {existing['van_name']}")
        if st.button("Remove van", disabled=not ok_del):
            done(*van_service.delete_van(existing["id"]))

with tabs[2]:
    st.caption("Stationed locations are fixed units on highways, campuses, public areas or event sites.")
    st.dataframe(vans[vans["service_type"] == "stationed"][["van_name", "address", "availability_status", "operating_hours", "facilities"]],
                 hide_index=True, width="stretch")
    st.markdown("**Add a stationed location**")
    van_form("st", None, force_type="stationed")

with tabs[3]:
    people = pd.DataFrame(profiles, columns=["full_name", "email", "phone", "role", "created_at"])
    st.dataframe(people, hide_index=True, width="stretch")
    with st.form("role_form"):
        who = st.selectbox("User", [p["id"] for p in profiles if p["id"] != user["id"]],
                           format_func=lambda i: next(f"{p['full_name'] or p['email']} ({p['role']})" for p in profiles if p["id"] == i))
        role = st.selectbox("New role", ["customer", "operator", "admin"])
        if st.form_submit_button("Change role", type="primary"):
            try:
                repo.update("profiles", who, {"role": role})
                done(True, "Role updated.")
            except Exception as e:
                st.error(f"Could not change the role: {e}")
    st.caption("Assign operators to vans in the Vans tab. Promote your first admin with the SQL in rls_policies.sql.")

with tabs[4]:
    pick = st.multiselect("Status", list(config.STATUS_LABELS), default=list(config.STATUS_LABELS), format_func=config.STATUS_LABELS.get)
    v = bk[bk["status"].isin(pick)]
    st.dataframe(v[["requested_at", "customer_name", "van_name", "booking_type", "status_label", "notes"]], hide_index=True, width="stretch")

with tabs[5]:
    st.markdown("**Cleaning records**")
    st.dataframe(van_service.list_cleaning_logs(vans).sort_values("cleaned_at", ascending=False)[["cleaned_at", "van_name", "status", "cleaning_notes"]],
                 hide_index=True, width="stretch")
    st.markdown("**Maintenance records**")
    ml = van_service.list_maintenance_logs(vans).sort_values("reported_at", ascending=False)
    st.dataframe(ml[["reported_at", "van_name", "issue", "resolution_status"]], hide_index=True, width="stretch")
    if not ml.empty:
        with st.form("mt_admin"):
            i = st.selectbox("Issue", ml["id"], format_func=lambda x: f"{ml.set_index('id').loc[x, 'van_name']}: {ml.set_index('id').loc[x, 'issue']}")
            s = st.selectbox("Status", ["open", "in_progress", "resolved"])
            if st.form_submit_button("Update"):
                done(*van_service.set_maintenance_status(i, s))

with tabs[6]:
    if not fb.empty:
        st.metric("Average rating", f"{fb['rating'].mean():.2f} / 5", help=f"{len(fb)} reviews")
    st.markdown("**Feedback**")
    st.dataframe(fb.sort_values("created_at", ascending=False)[["created_at", "van_name", "rating", "comments"]], hide_index=True, width="stretch")
    st.markdown("**Complaints**")
    st.dataframe(cp.sort_values("created_at", ascending=False)[["created_at", "van_name", "complaint_type", "description", "status"]], hide_index=True, width="stretch")
    if not cp.empty:
        with st.form("cp_status"):
            i = st.selectbox("Complaint", cp["id"], format_func=lambda x: cp.set_index("id").loc[x, "description"][:60])
            s = st.selectbox("Status", ["open", "in_review", "resolved"])
            if st.form_submit_button("Update"):
                done(*booking_service.set_complaint_status(i, s))

with tabs[7]:
    a, b = st.columns(2)
    a.plotly_chart(charts.by_van(an.bookings_by_van(bk)), width="stretch")
    b.plotly_chart(charts.split(an.service_split(bk)), width="stretch")
    a.plotly_chart(charts.hourly(an.hourly_demand(bk)), width="stretch")
    b.plotly_chart(charts.ratings(an.rating_by_van(fb)), width="stretch")
