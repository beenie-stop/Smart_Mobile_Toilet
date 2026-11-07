import streamlit as st

import config
from components import cards, navbar
from services import booking_service, van_service

user = navbar.setup("Customer Dashboard", "🏠", roles=["customer"])
navbar.page_header(f"Hello, {user['full_name'].split()[0]}", config.TAGLINE)

tab_home, tab_report = st.tabs(["Overview", "Report an issue"])
with tab_home:
    st.page_link("pages/2_Find_Toilet.py", label="Find a Toilet Near Me", icon="🔎", width="stretch")
    a, b = st.columns(2)
    a.markdown('<div class="card mobile"><h4>🚐 On-demand</h4><div class="muted">Request a van to come to your '
               'location. Status updates appear under My Bookings.</div></div>', unsafe_allow_html=True)
    b.markdown('<div class="card stationed"><h4>📍 Stationed</h4><div class="muted">Visit a facility on your route '
               'or reserve a time slot. No van is dispatched.</div></div>', unsafe_allow_html=True)

    bk = booking_service.list_bookings(user)
    active = bk[bk["status"].isin(config.ACTIVE_STATUSES)]
    c = st.columns(3)
    c[0].markdown(cards.metric_card("Active bookings", len(active), config.ORANGE), unsafe_allow_html=True)
    c[1].markdown(cards.metric_card("Completed", int((bk["status"] == "completed").sum()), config.GREEN), unsafe_allow_html=True)
    c[2].markdown(cards.metric_card("Total bookings", len(bk), config.TEAL), unsafe_allow_html=True)

    st.markdown("#### Your latest active booking")
    if active.empty:
        st.info("No active bookings. Use Find a Toilet Near Me to request a van or reserve a visit.")
    else:
        r = active.iloc[0]
        st.markdown(f"**{r['van_name']}** · {config.SERVICE_LABELS[r['booking_type']]} · "
                    f"{r['scheduled_at'].tz_convert(config.TIMEZONE):%d %b %Y, %H:%M}")
        st.markdown(cards.status_tracker(r["status"], r["booking_type"]), unsafe_allow_html=True)
        st.page_link("pages/3_My_Bookings.py", label="See all bookings", icon="📋")

with tab_report:
    vans = van_service.list_vans()
    with st.form("report_issue", clear_on_submit=True):
        options = {"Not specific to one van": None} | dict(zip(vans["van_name"], vans["id"]))
        van_label = st.selectbox("Which van or facility?", list(options))
        kind = st.selectbox("Issue type", config.COMPLAINT_TYPES)
        desc = st.text_area("What happened?", max_chars=500)
        if st.form_submit_button("Send report", type="primary"):
            ok, msg = booking_service.submit_complaint(user, options[van_label], kind, desc)
            (st.success if ok else st.error)(msg)
