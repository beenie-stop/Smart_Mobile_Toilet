import streamlit as st

import config
from components import navbar
from services import auth_service, supabase_client

user = navbar.setup("Home", "🚻")

st.markdown(f"""<div class="hero"><h1>{config.APP_NAME}</h1>
<div class="tag">{config.TAGLINE}</div>
<p>A network of mobile toilet vans and stationed facilities. Find a clean, private, accessible toilet near you,
request a van to come to you, or reserve a visit at a facility on your route.</p></div>""".replace("\n", ""), unsafe_allow_html=True)

if user:
    st.success(f"Welcome back, {user['full_name']}.")
    st.page_link(auth_service.ROLE_HOME[user["role"]], label="Open my dashboard", icon="🏠")
    if user["role"] == "customer":
        st.page_link("pages/2_Find_Toilet.py", label="Find a Toilet Near Me", icon="🔎")
else:
    if st.button("🔎 Find a Toilet Near Me", type="primary"):
        st.info("Sign in or create an account below, or try demo mode, to search for toilets.")

st.markdown("### How it works")
c1, c2, c3, c4 = st.columns(4)
for col, (icon, title, text) in zip([c1, c2, c3, c4], [
    ("📍", "Share your location", "Enter coordinates or a place name. We never guess where you are."),
    ("🗺️", "Discover nearby", "See vans and stationed facilities on a map, sorted by distance."),
    ("🚐", "Request or reserve", "Call an on-demand van to you, or reserve a visit at a stationed unit."),
    ("⭐", "Rate the service", "Track your booking, then rate it or report an issue."),
]):
    col.markdown(f'<div class="card"><h4>{icon} {title}</h4><div class="muted">{text}</div></div>', unsafe_allow_html=True)

m1, m2 = st.columns(2)
m1.markdown('<div class="card mobile"><h4>🚐 Model A · On-demand</h4><div class="muted">A van travels to your '
            'location. The operator accepts, assigns and updates the status as the job progresses.</div></div>', unsafe_allow_html=True)
m2.markdown('<div class="card stationed"><h4>📍 Model B · Stationed</h4><div class="muted">Vans placed at highways, '
            'colleges, public areas and events. Check hours and facilities, then visit or reserve.</div></div>', unsafe_allow_html=True)

if not user:
    st.markdown("### Get started")
    left, right = st.columns([3, 2])
    with left:
        tab_in, tab_up = st.tabs(["Sign in", "Create account"])
        with tab_in:
            with st.form("signin"):
                email = st.text_input("Email")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("Sign in", type="primary"):
                    ok, msg = auth_service.sign_in(email, pw)
                    if ok:
                        st.switch_page(auth_service.ROLE_HOME[st.session_state["user"]["role"]])
                    st.error(msg)
        with tab_up:
            with st.form("signup"):
                name = st.text_input("Full name")
                email2 = st.text_input("Email", key="su_email")
                phone = st.text_input("Phone (optional)")
                pw2 = st.text_input("Password (8+ characters, letters and numbers)", type="password", key="su_pw")
                if st.form_submit_button("Create account", type="primary"):
                    ok, msg = auth_service.sign_up(name, email2, phone, pw2)
                    if ok and st.session_state.get("user"):
                        st.switch_page(auth_service.ROLE_HOME["customer"])
                    (st.success if ok else st.error)(msg)
        if not supabase_client.is_configured():
            st.warning("Supabase is not configured yet, so sign-in is unavailable. Demo mode works without it.")
    with right:
        st.markdown('<div class="card"><h4>🧪 Try demo mode</h4><div class="muted">Explore every dashboard with '
                    f'clearly labelled sample data around {config.DEMO_CITY_NAME}. No account needed and nothing is '
                    'saved to the database.</div></div>', unsafe_allow_html=True)
        for role, label in [("customer", "Customer"), ("operator", "Van operator"), ("admin", "Admin")]:
            if st.button(f"Enter as {label}", key=f"demo_{role}", width="stretch"):
                auth_service.start_demo(role)
                st.switch_page(auth_service.ROLE_HOME[role])
