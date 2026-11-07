from datetime import datetime, timedelta, timezone

import pandas as pd

import config
from services import repo
from services.auth_service import is_demo
from utils.validation import clean_text, valid_coords

BOOKING_COLS = ["id", "customer_id", "van_id", "booking_type", "user_latitude", "user_longitude", "requested_at",
                "scheduled_at", "duration_minutes", "status", "notes"]


def _now():
    return datetime.now(timezone.utc)


def _friendly(e):
    m = str(e).lower()
    if "bookings_no_overlap" in m or "exclusion constraint" in m:
        return "This van was just booked for that time. Choose another van or time."
    if "not available" in m:
        return "This van is no longer available."
    if "row-level security" in m or "permission" in m or "not permitted" in m:
        return "You do not have permission to do that."
    return "Something went wrong. Please try again."


def my_van_ids(user):
    return {v["id"] for v in repo.select("vans", eq={"operator_id": user["id"]})}


def list_bookings(user):
    role = user["role"]
    if role == "customer":
        rows = repo.select("bookings", eq={"customer_id": user["id"]}, order="requested_at")
    else:
        rows = repo.select("bookings", order="requested_at")
        if role == "operator":
            ids = my_van_ids(user)
            rows = [r for r in rows if r["van_id"] in ids]
    vans = {v["id"]: v["van_name"] for v in repo.select("vans")}
    try:
        names = {p["id"]: p["full_name"] or p["email"] for p in repo.select("profiles")}
    except Exception:
        names = {}
    df = pd.DataFrame(rows, columns=BOOKING_COLS)
    df["van_name"] = df["van_id"].map(vans).fillna("Removed van")
    df["customer_name"] = df["customer_id"].map(names).fillna("Customer")
    df["status_label"] = [config.status_label(s, t) for s, t in zip(df["status"], df["booking_type"])]
    for c in ("requested_at", "scheduled_at"):
        df[c] = pd.to_datetime(df[c], utc=True)
    return df.sort_values("requested_at", ascending=False).reset_index(drop=True)


def _overlap_exists(van_id, start, end):
    for b in repo.select("bookings", eq={"van_id": van_id}):
        if b["status"] in config.ACTIVE_STATUSES:
            s = pd.to_datetime(b["scheduled_at"], utc=True).to_pydatetime()
            e = s + timedelta(minutes=b.get("duration_minutes") or config.BOOKING_DURATION_MIN)
            if s < end and start < e:
                return True
    return False


def create_booking(user, van_id, booking_type, lat=None, lon=None, scheduled_at=None, notes=""):
    if user["role"] != "customer":
        return False, "Only customers can make bookings."
    van = repo.select("vans", eq={"id": van_id})
    if not van:
        return False, "That van no longer exists."
    van = van[0]
    if van["service_type"] != booking_type:
        return False, "Booking type does not match this van."
    if van["availability_status"] in ("unavailable", "maintenance") or (
            booking_type == "on_demand" and van["availability_status"] != "available"):
        return False, "This van is not available right now."
    notes = clean_text(notes, 500)
    now = _now()
    if booking_type == "on_demand":
        if not valid_coords(lat, lon):
            return False, "Set your location first."
        start = now
    else:
        start = scheduled_at
        if start is None or start < now - timedelta(minutes=5):
            return False, "Choose a visit time in the future."
        if start > now + timedelta(days=7):
            return False, "Visits can be reserved up to 7 days ahead."
    end = start + timedelta(minutes=config.BOOKING_DURATION_MIN)
    mine = [b for b in repo.select("bookings", eq={"customer_id": user["id"]}) if b["status"] in config.ACTIVE_STATUSES]
    if len(mine) >= 3:
        return False, "You already have 3 active bookings. Complete or cancel one first."
    if _overlap_exists(van_id, start, end):
        return False, "This van is already booked for that time. Choose another van or time."
    row = {"customer_id": user["id"], "van_id": van_id, "booking_type": booking_type,
           "user_latitude": float(lat) if booking_type == "on_demand" else None,
           "user_longitude": float(lon) if booking_type == "on_demand" else None,
           "scheduled_at": start.isoformat(), "duration_minutes": config.BOOKING_DURATION_MIN, "notes": notes}
    if is_demo():
        row.update({"status": "requested", "requested_at": now.isoformat(), "slot_end": end.isoformat()})
    try:
        repo.insert("bookings", row)
    except Exception as e:
        return False, _friendly(e)
    return True, "Request sent. The operator will review it shortly."


def _set_demo_van(van_id, to, only_if):
    v = repo.select("vans", eq={"id": van_id})
    if v and v[0]["availability_status"] == only_if:
        repo.update("vans", van_id, {"availability_status": to})


def update_status(user, booking_id, new_status):
    rows = repo.select("bookings", eq={"id": booking_id})
    if not rows:
        return False, "Booking not found."
    b = rows[0]
    role, cur = user["role"], b["status"]
    if role == "customer":
        if b["customer_id"] != user["id"] or new_status != "cancelled" or cur not in config.CUSTOMER_CANCELLABLE:
            return False, "You can only cancel your own booking before it is assigned."
    elif role == "operator":
        if b["van_id"] not in my_van_ids(user):
            return False, "This booking is not for your van."
        if new_status not in config.NEXT_STATUS[b["booking_type"]].get(cur, []):
            return False, "That status change is not allowed."
    elif role == "admin":
        if new_status not in config.NEXT_STATUS[b["booking_type"]].get(cur, []) + ["cancelled"]:
            return False, "That status change is not allowed."
    try:
        repo.update("bookings", booking_id, {"status": new_status})
    except Exception as e:
        return False, _friendly(e)
    if is_demo() and b["booking_type"] == "on_demand":  # real mode: handled by DB trigger
        if new_status in ("accepted", "assigned", "on_the_way", "arrived"):
            _set_demo_van(b["van_id"], "busy", "available")
        elif new_status in ("completed", "cancelled", "rejected"):
            _set_demo_van(b["van_id"], "available", "busy")
    return True, f"Booking marked {config.status_label(new_status, b['booking_type']).lower()}."


def submit_feedback(user, booking_id, rating, comments):
    if rating not in (1, 2, 3, 4, 5):
        return False, "Choose a rating from 1 to 5."
    b = repo.select("bookings", eq={"id": booking_id})
    if not b or b[0]["customer_id"] != user["id"] or b[0]["status"] != "completed":
        return False, "You can rate only your own completed bookings."
    if repo.select("feedback", eq={"booking_id": booking_id}):
        return False, "You already rated this booking."
    try:
        repo.insert("feedback", {"booking_id": booking_id, "customer_id": user["id"], "rating": int(rating),
                                 "comments": clean_text(comments, 500)})
        return True, "Thanks for your feedback."
    except Exception as e:
        return False, _friendly(e)


def list_feedback(user, bookings_df):
    rows = repo.select("feedback", order="created_at")
    df = pd.DataFrame(rows, columns=["id", "booking_id", "customer_id", "rating", "comments", "created_at"])
    m = bookings_df.set_index("id")
    df["van_name"] = df["booking_id"].map(m["van_name"]).fillna("Removed van")
    df["customer_name"] = df["customer_id"].map(dict(zip(bookings_df["customer_id"], bookings_df["customer_name"]))).fillna("Customer")
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    return df


def submit_complaint(user, van_id, complaint_type, description):
    description = clean_text(description, 500)
    if complaint_type not in config.COMPLAINT_TYPES:
        return False, "Choose a valid issue type."
    if len(description) < 5:
        return False, "Describe the issue (at least 5 characters)."
    try:
        repo.insert("complaints", {"customer_id": user["id"], "van_id": van_id or None,
                                   "complaint_type": complaint_type, "description": description, "status": "open"})
        return True, "Report sent. Our team will review it."
    except Exception as e:
        return False, _friendly(e)


def list_complaints(vans_df):
    rows = repo.select("complaints", order="created_at")
    df = pd.DataFrame(rows, columns=["id", "customer_id", "van_id", "complaint_type", "description", "status", "created_at"])
    df["van_name"] = df["van_id"].map(dict(zip(vans_df["id"], vans_df["van_name"]))).fillna("Not specified")
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    return df


def set_complaint_status(complaint_id, status):
    if status not in ("open", "in_review", "resolved"):
        return False, "Invalid status."
    try:
        repo.update("complaints", complaint_id, {"status": status})
        return True, "Complaint updated."
    except Exception as e:
        return False, _friendly(e)
