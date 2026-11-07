import streamlit as st

import config
from components import cards, navbar
from services import booking_service, repo

user = navbar.setup("My Bookings", "📋", roles=["customer"])
navbar.page_header("My bookings", "Track status, cancel, and rate completed visits.")

bk = booking_service.list_bookings(user)
if bk.empty:
    st.info("No bookings yet. Use Find a Toilet Near Me to make your first one.")
    st.page_link("pages/2_Find_Toilet.py", label="Find a Toilet Near Me", icon="🔎")
    st.stop()

show = st.radio("Show", ["Active", "Completed", "Cancelled / rejected", "All"], horizontal=True)
sel = {"Active": config.ACTIVE_STATUSES, "Completed": ["completed"], "Cancelled / rejected": ["cancelled", "rejected"],
       "All": list(config.STATUS_LABELS)}[show]
view = bk[bk["status"].isin(sel)]
rated = {f["booking_id"]: f for f in repo.select("feedback", eq={"customer_id": user["id"]})}

if view.empty:
    st.info("Nothing in this view.")
for _, r in view.iterrows():
    when = r["scheduled_at"].tz_convert(config.TIMEZONE)
    with st.expander(f"{r['van_name']} · {config.SERVICE_LABELS[r['booking_type']]} · {when:%d %b, %H:%M} · {r['status_label']}",
                     expanded=r["status"] in config.ACTIVE_STATUSES):
        st.markdown(cards.status_tracker(r["status"], r["booking_type"]), unsafe_allow_html=True)
        if r["notes"]:
            st.caption(f"Your note: {r['notes']}")
        if r["status"] in config.CUSTOMER_CANCELLABLE and st.button("Cancel booking", key=f"c_{r['id']}"):
            ok, msg = booking_service.update_status(user, r["id"], "cancelled")
            (st.success if ok else st.error)(msg)
            if ok:
                st.rerun()
        if r["status"] == "completed":
            if r["id"] in rated:
                st.success(f"You rated this {rated[r['id']]['rating']}/5.")
            else:
                with st.form(f"fb_{r['id']}"):
                    rating = st.select_slider("Rating", options=[1, 2, 3, 4, 5], value=5, format_func=lambda x: "⭐" * x)
                    comment = st.text_area("Comments (optional)", max_chars=500)
                    if st.form_submit_button("Submit feedback", type="primary"):
                        ok, msg = booking_service.submit_feedback(user, r["id"], rating, comment)
                        (st.success if ok else st.error)(msg)
                        if ok:
                            st.rerun()
