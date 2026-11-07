import re
from datetime import datetime
from zoneinfo import ZoneInfo

import config

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9]{10,13}$")


def clean_text(value, max_len=500):
    return re.sub(r"\s+", " ", str(value or "")).strip()[:max_len]


def valid_email(email):
    return bool(email) and len(email) <= 254 and bool(EMAIL_RE.match(email))


def clean_phone(phone):
    return re.sub(r"[\s\-()]", "", phone or "")


def valid_phone(phone):
    return bool(PHONE_RE.match(phone or ""))


def valid_password(pw):
    return bool(pw) and len(pw) >= 8 and bool(re.search(r"[A-Za-z]", pw)) and bool(re.search(r"\d", pw))


def valid_coords(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return -90 <= lat <= 90 and -180 <= lon <= 180


def parse_hours(text):
    """'06:00-22:00' or '24x7' -> (start_min, end_min) or None."""
    t = (text or "").strip().lower()
    if t in ("24x7", "24/7", "24 hours"):
        return (0, 1440)
    m = re.match(r"^(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})$", t)
    if not m:
        return None
    h1, m1, h2, m2 = map(int, m.groups())
    if h1 > 23 or h2 > 23 or m1 > 59 or m2 > 59:
        return None
    return (h1 * 60 + m1, h2 * 60 + m2)


def is_open_now(text):
    parsed = parse_hours(text)
    if not parsed:
        return False
    now = datetime.now(ZoneInfo(config.TIMEZONE))
    minute = now.hour * 60 + now.minute
    start, end = parsed
    if start == end:
        return True
    return start <= minute < end if start < end else (minute >= start or minute < end)
