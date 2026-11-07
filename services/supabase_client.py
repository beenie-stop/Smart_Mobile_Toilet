import base64
import json

import streamlit as st

import config


def is_configured():
    return bool(config.SUPABASE_URL and config.SUPABASE_ANON_KEY)


def _is_privileged_key(key):
    if str(key).startswith("sb_secret_"):
        return True
    try:
        payload = key.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("role") == "service_role"
    except Exception:
        return False


def get_client():
    """One client PER browser session (holds that user's JWT, so RLS applies). Never cached globally."""
    if "sb_client" not in st.session_state:
        if not is_configured():
            raise RuntimeError("Supabase credentials are not configured. Add them to secrets or .env.")
        if _is_privileged_key(config.SUPABASE_ANON_KEY):
            raise RuntimeError("A service-role key was detected. Use the public anon key only.")
        from supabase import create_client
        st.session_state["sb_client"] = create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)
    return st.session_state["sb_client"]
