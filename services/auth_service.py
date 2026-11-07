import streamlit as st

import config
from services import supabase_client
from utils.validation import clean_phone, clean_text, valid_email, valid_password, valid_phone

ROLE_HOME = {
    "customer": "pages/1_Customer_Dashboard.py",
    "operator": "pages/4_Operator_Dashboard.py",
    "admin": "pages/5_Admin_Dashboard.py",
}


def current_user():
    return st.session_state.get("user")


def is_demo():
    return bool(st.session_state.get("demo_mode"))


def _load_profile(client, auth_user):
    rows = client.table("profiles").select("*").eq("id", auth_user.id).execute().data
    if not rows:
        return False, "Your profile was not found. Contact the administrator."
    p = rows[0]
    st.session_state["user"] = {"id": p["id"], "email": p["email"], "full_name": p["full_name"] or p["email"],
                                "role": p["role"], "demo": False}
    return True, "Signed in."


def sign_in(email, password):
    email = clean_text(email, 254).lower()
    if not valid_email(email) or not password:
        return False, "Enter a valid email address and your password."
    try:
        client = supabase_client.get_client()
    except RuntimeError as e:
        return False, str(e)
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        return _load_profile(client, res.user)
    except Exception:
        return False, "Invalid email or password."


def sign_up(full_name, email, phone, password):
    full_name, email, phone = clean_text(full_name, 120), clean_text(email, 254).lower(), clean_phone(phone)
    if len(full_name) < 2:
        return False, "Enter your full name."
    if not valid_email(email):
        return False, "Enter a valid email address."
    if phone and not valid_phone(phone):
        return False, "Phone must be 10-13 digits, optionally starting with +."
    if not valid_password(password):
        return False, "Password needs at least 8 characters with a letter and a number."
    try:
        client = supabase_client.get_client()
        res = client.auth.sign_up({"email": email, "password": password,
                                   "options": {"data": {"full_name": full_name, "phone": phone}}})
    except RuntimeError as e:
        return False, str(e)
    except Exception:
        return False, "Could not create the account. The email may already be registered."
    if res.session and res.user:
        return _load_profile(client, res.user)
    return True, "Account created. Check your email to confirm it, then sign in."


def start_demo(role):
    st.session_state.clear()
    ids = {"customer": ("demo-cust-1", "Demo Customer A"), "operator": ("demo-op-1", "Demo Operator 1"),
           "admin": ("demo-admin", "Demo Admin")}[role]
    st.session_state["demo_mode"] = True
    st.session_state["user"] = {"id": ids[0], "email": f"{role}@demo.local", "full_name": ids[1], "role": role, "demo": True}


def sign_out():
    if not is_demo():
        try:
            supabase_client.get_client().auth.sign_out()
        except Exception:
            pass
    st.session_state.clear()


def require_role(roles):
    user = current_user()
    if not user:
        st.warning("Please sign in (or try demo mode) from the home page.")
        st.page_link("app.py", label="Go to sign in", icon="🔐")
        st.stop()
    if user["role"] not in roles:
        st.error("Your account does not have access to this page.")
        st.page_link(ROLE_HOME[user["role"]], label="Go to your dashboard", icon="🏠")
        st.stop()
    return user
