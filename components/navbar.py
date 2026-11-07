import streamlit as st

import config
from services import auth_service

ROLE_PAGES = {"customer": ["Customer_Dashboard", "Find_Toilet", "My_Bookings"],
              "operator": ["Operator_Dashboard"], "admin": ["Admin_Dashboard"]}
ALL_PAGES = ["Customer_Dashboard", "Find_Toilet", "My_Bookings", "Operator_Dashboard", "Admin_Dashboard"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, .stApp, [class*="css"] {font-family:'Plus Jakarta Sans',system-ui,sans-serif;}
.block-container {padding-top:2rem; max-width:1200px;}
h1,h2,h3 {color:#0B4F5C; letter-spacing:-0.01em;}
.hero {background:linear-gradient(135deg,#0B4F5C 0%,#0E6E7E 55%,#1E6FD9 100%); color:#fff; border-radius:22px;
       padding:3rem 2.5rem; margin-bottom:1.2rem;}
.hero h1 {color:#fff; font-size:2.7rem; font-weight:800; margin:0 0 .5rem; line-height:1.12;}
.hero .tag {font-size:1.3rem; font-weight:600; opacity:.95; margin-bottom:.6rem;}
.hero p {max-width:620px; opacity:.88; font-size:1.02rem; margin:0;}
.card {background:#fff; border:1px solid #DCE7EA; border-radius:16px; padding:1rem 1.2rem; margin-bottom:.6rem;}
.card h4 {margin:0 0 .2rem; color:#0B4F5C; font-size:1.05rem;}
.card.stationed {border-left:6px solid #1E6FD9;}
.card.mobile {border-left:6px solid #0B4F5C;}
.muted {color:#64748B; font-size:.86rem;}
.metric {background:#fff; border:1px solid #DCE7EA; border-left:6px solid var(--c,#0B4F5C); border-radius:14px;
         padding:.9rem 1.1rem; margin-bottom:.6rem;}
.metric .v {font-size:1.9rem; font-weight:800; color:#0F2A33; line-height:1.1;}
.metric .l {font-size:.8rem; color:#64748B; font-weight:600;}
.badge {display:inline-block; padding:.12rem .6rem; border-radius:999px; font-size:.75rem; font-weight:700; color:#fff; margin-right:.3rem;}
.chip {display:inline-block; background:#E6F2F3; color:#0B4F5C; border-radius:8px; padding:.08rem .5rem; font-size:.75rem; margin:.1rem .15rem .1rem 0;}
.demo-banner {background:#FFF4DB; border:1px solid #F59E0B; color:#7A4B00; border-radius:12px; padding:.55rem .9rem;
              font-size:.88rem; font-weight:600; margin-bottom:.8rem;}
.tracker {display:flex; gap:.2rem; margin:.5rem 0 .2rem;}
.step {flex:1; text-align:center; font-size:.7rem; color:#94A3B8; min-width:0;}
.step .dot {width:26px; height:26px; border-radius:50%; background:#DCE7EA; margin:0 auto .2rem; line-height:26px; color:#fff; font-weight:700; font-size:.75rem;}
.step.done {color:#0B4F5C;} .step.done .dot {background:#16A34A;}
.step.now {color:#1E6FD9; font-weight:700;} .step.now .dot {background:#1E6FD9;}
div.stButton > button, div[data-testid="stFormSubmitButton"] > button {border-radius:12px; font-weight:600;}
@media (max-width:640px) {
  .hero {padding:1.8rem 1.3rem;} .hero h1 {font-size:1.8rem;} .hero .tag {font-size:1.05rem;}
  .step {font-size:.6rem;} .metric .v {font-size:1.5rem;}
}
</style>
"""


def inject_css(role=None):
    hide = [p for p in ALL_PAGES if p not in ROLE_PAGES.get(role, [])]
    rules = "".join(f'[data-testid="stSidebarNav"] li:has(a[href*="{p}"]){{display:none;}}' for p in hide)
    st.markdown(CSS + f"<style>{rules}</style>", unsafe_allow_html=True)  # cosmetic only; DB enforces access


def render_sidebar(user):
    with st.sidebar:
        st.markdown(f"### 🚻 {config.APP_NAME}")
        if not user:
            st.caption("Not signed in")
            return
        st.caption(f"{user['full_name']} · {user['role'].title()}")
        if user.get("demo"):
            roles = ["customer", "operator", "admin"]
            pick = st.selectbox("Demo role", roles, index=roles.index(user["role"]), format_func=str.title, key="demo_role_pick")
            if pick != user["role"]:
                auth_service.start_demo(pick)
                st.switch_page(auth_service.ROLE_HOME[pick])
        if st.button("Sign out", key="signout", width="stretch"):
            auth_service.sign_out()
            st.switch_page("app.py")


def setup(title, icon="🚻", roles=None):
    """Page chrome + access gate. Call first on every page."""
    st.set_page_config(page_title=f"{title} · {config.APP_NAME}", page_icon=icon, layout="wide")
    user = auth_service.current_user()
    inject_css(user["role"] if user else None)
    render_sidebar(user)
    if user and user.get("demo"):
        st.markdown('<div class="demo-banner">🧪 DEMO MODE: sample data only. Nothing here is saved to Supabase.</div>',
                    unsafe_allow_html=True)
    if roles is not None:
        user = auth_service.require_role(roles)
    return user


def page_header(title, subtitle=""):
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)
