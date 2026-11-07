"""Central configuration. Secrets come from Streamlit secrets or environment variables."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # pragma: no cover
    pass
import streamlit as st


def get_setting(key, default=None):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


APP_NAME = "Smart Mobile Toilet Network"
TAGLINE = "Clean sanitation, wherever you need it."

# Only the public anon key is ever read. The service-role key is deliberately unsupported.
SUPABASE_URL = get_setting("SUPABASE_URL")
SUPABASE_ANON_KEY = get_setting("SUPABASE_ANON_KEY")

DEMO_CITY_NAME = get_setting("DEMO_CITY_NAME", "Hyderabad")
DEMO_LAT = float(get_setting("DEMO_CITY_LAT", 17.3850))
DEMO_LON = float(get_setting("DEMO_CITY_LON", 78.4867))
GEOCODING_ENABLED = str(get_setting("GEOCODING_ENABLED", "false")).lower() == "true"
TIMEZONE = get_setting("APP_TIMEZONE", "Asia/Kolkata")
DEFAULT_RADIUS_KM = 10

# Palette
TEAL, BLUE, GREEN, ORANGE, RED, SLATE = "#0B4F5C", "#1E6FD9", "#16A34A", "#F59E0B", "#DC2626", "#64748B"

SERVICE_LABELS = {"on_demand": "On-demand", "stationed": "Stationed"}
AVAILABILITY = ["available", "busy", "unavailable", "maintenance"]
AVAIL_COLORS = {"available": GREEN, "busy": ORANGE, "unavailable": RED, "maintenance": RED}

FACILITY_CATALOG = [
    ("Private toilet", "Fully enclosed private cubicle"),
    ("Running water", "Piped running water supply"),
    ("Handwashing sink", "Sink with soap"),
    ("Menstrual hygiene products", "Pads available on request"),
    ("Sanitary waste disposal", "Sealed sanitary waste bin"),
    ("Proper lighting", "Interior and entrance lighting"),
    ("Ventilation", "Mechanical or passive ventilation"),
    ("Accessible facility", "Wheelchair-accessible cubicle with ramp"),
]
FACILITIES = [n for n, _ in FACILITY_CATALOG]
WOMEN_FRIENDLY_REQUIRED = {"Private toilet", "Menstrual hygiene products", "Sanitary waste disposal", "Proper lighting"}
ACCESSIBLE_FACILITY = "Accessible facility"

STATUS_LABELS = {
    "requested": "Requested", "accepted": "Accepted", "assigned": "Assigned", "on_the_way": "On the way",
    "arrived": "Arrived", "completed": "Completed", "cancelled": "Cancelled", "rejected": "Rejected",
}
STATUS_COLORS = {
    "requested": ORANGE, "accepted": BLUE, "assigned": BLUE, "on_the_way": BLUE,
    "arrived": TEAL, "completed": GREEN, "cancelled": RED, "rejected": RED,
}
ACTIVE_STATUSES = ["requested", "accepted", "assigned", "on_the_way", "arrived"]
TRACK_STEPS = {
    "on_demand": ["requested", "accepted", "assigned", "on_the_way", "arrived", "completed"],
    "stationed": ["requested", "accepted", "arrived", "completed"],
}
# Allowed operator transitions per booking type
NEXT_STATUS = {
    "on_demand": {
        "requested": ["accepted", "rejected"], "accepted": ["assigned", "cancelled"],
        "assigned": ["on_the_way", "cancelled"], "on_the_way": ["arrived"], "arrived": ["completed"],
    },
    "stationed": {
        "requested": ["accepted", "rejected"], "accepted": ["arrived", "cancelled"], "arrived": ["completed"],
    },
}
CUSTOMER_CANCELLABLE = ["requested", "accepted"]
COMPLAINT_TYPES = ["Cleanliness", "Maintenance", "Water supply", "Safety", "Staff behaviour", "Other"]
BOOKING_DURATION_MIN = 30


def status_label(status, booking_type=None):
    if status == "arrived" and booking_type == "stationed":
        return "Checked in"
    return STATUS_LABELS.get(status, status)
