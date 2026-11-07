import pandas as pd

import config
from services import repo
from utils.distance import haversine_km
from utils.validation import clean_text, is_open_now, parse_hours, valid_coords

VAN_COLS = ["id", "van_name", "service_type", "latitude", "longitude", "address", "availability_status",
            "water_capacity", "water_level", "waste_capacity", "waste_level", "last_cleaned_at",
            "operator_id", "operating_hours", "facilities", "operator_name"]


def facilities_catalog():
    return repo.select("facilities", order="name", desc=False)


def list_vans():
    vans = repo.select("vans", order="van_name", desc=False)
    fac = {f["id"]: f["name"] for f in repo.select("facilities")}
    by_van = {}
    for vf in repo.select("van_facilities"):
        if vf.get("available"):
            by_van.setdefault(vf["van_id"], []).append(fac.get(vf["facility_id"], "?"))
    try:
        ops = {p["id"]: p["full_name"] or p["email"] for p in repo.select("profiles", eq={"role": "operator"})}
    except Exception:
        ops = {}
    for v in vans:
        v["facilities"] = sorted(by_van.get(v["id"], []))
        v["operator_name"] = ops.get(v.get("operator_id"))
    df = pd.DataFrame(vans, columns=VAN_COLS)
    for c in ["latitude", "longitude", "water_capacity", "water_level", "waste_capacity", "waste_level"]:
        df[c] = pd.to_numeric(df[c])
    return df


def with_distance(df, lat, lon):
    df = df.copy()
    df["distance_km"] = haversine_km(lat, lon, df["latitude"], df["longitude"]) if len(df) else []
    return df.sort_values("distance_km").reset_index(drop=True)


def filter_vans(df, radius_km, available_now=False, on_demand=False, stationed=False, women=False, accessible=False):
    df = df[df["distance_km"] <= radius_km]
    if on_demand != stationed:  # exactly one ticked
        df = df[df["service_type"] == ("on_demand" if on_demand else "stationed")]
    if available_now:
        df = df[(df["availability_status"] == "available") & df["operating_hours"].map(is_open_now)]
    if women:
        df = df[df["facilities"].map(lambda f: config.WOMEN_FRIENDLY_REQUIRED.issubset(set(f)))]
    if accessible:
        df = df[df["facilities"].map(lambda f: config.ACCESSIBLE_FACILITY in f)]
    return df.reset_index(drop=True)


def _validate_van(d):
    if len(d["van_name"]) < 2:
        return "Enter a van name (at least 2 characters)."
    if d["service_type"] not in config.SERVICE_LABELS:
        return "Invalid service type."
    if not valid_coords(d["latitude"], d["longitude"]):
        return "Latitude must be -90 to 90 and longitude -180 to 180."
    if d["availability_status"] not in config.AVAILABILITY:
        return "Invalid availability status."
    if not parse_hours(d["operating_hours"]):
        return "Operating hours must look like 06:00-22:00 or 24x7."
    if d["water_capacity"] <= 0 or d["waste_capacity"] <= 0:
        return "Tank capacities must be greater than zero."
    if not (0 <= d["water_level"] <= d["water_capacity"]) or not (0 <= d["waste_level"] <= d["waste_capacity"]):
        return "Tank levels must be between 0 and the tank capacity."
    return None


def save_van(data, facility_names, van_id=None):
    """Admin only (enforced by RLS). Returns (ok, message)."""
    d = dict(data)
    d["van_name"] = clean_text(d.get("van_name"), 100)
    d["address"] = clean_text(d.get("address"), 250)
    d["operating_hours"] = clean_text(d.get("operating_hours"), 20)
    err = _validate_van(d)
    if err:
        return False, err
    try:
        row = repo.update("vans", van_id, d) if van_id else repo.insert("vans", d)
        vid = row["id"]
        repo.delete("van_facilities", {"van_id": vid})
        ids = {f["name"]: f["id"] for f in facilities_catalog()}
        for name in facility_names:
            if name in ids:
                repo.insert("van_facilities", {"van_id": vid, "facility_id": ids[name], "available": True})
        return True, "Van saved."
    except Exception as e:
        return False, f"Could not save the van: {e}"


def delete_van(van_id):
    try:
        repo.delete("vans", {"id": van_id})
        return True, "Van removed."
    except Exception as e:
        return False, f"Could not remove the van: {e}"


def operator_update(van_id, **fields):
    """Operator/admin updates to live fields. RLS + guard trigger restrict what is accepted."""
    van = repo.select("vans", eq={"id": van_id})
    if not van:
        return False, "Van not found."
    van = van[0]
    allowed = {"availability_status", "latitude", "longitude", "address", "operating_hours", "water_level", "waste_level"}
    upd = {k: v for k, v in fields.items() if k in allowed}
    if "availability_status" in upd and upd["availability_status"] not in config.AVAILABILITY:
        return False, "Invalid availability status."
    if "latitude" in upd or "longitude" in upd:
        if not valid_coords(upd.get("latitude", van["latitude"]), upd.get("longitude", van["longitude"])):
            return False, "Invalid coordinates."
    if "operating_hours" in upd:
        upd["operating_hours"] = clean_text(upd["operating_hours"], 20)
        if not parse_hours(upd["operating_hours"]):
            return False, "Operating hours must look like 06:00-22:00 or 24x7."
    if "address" in upd:
        upd["address"] = clean_text(upd["address"], 250)
    if "water_level" in upd and not 0 <= upd["water_level"] <= van["water_capacity"]:
        return False, "Water level must be between 0 and the tank capacity."
    if "waste_level" in upd and not 0 <= upd["waste_level"] <= van["waste_capacity"]:
        return False, "Waste level must be between 0 and the tank capacity."
    try:
        repo.update("vans", van_id, upd)
        return True, "Van updated."
    except Exception as e:
        return False, f"Update failed: {e}"


def log_cleaning(van_id, operator_id, notes, partial=False, emptied_waste=False, refilled_water=False):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    try:
        repo.insert("cleaning_logs", {"van_id": van_id, "operator_id": operator_id, "cleaned_at": now,
                                      "cleaning_notes": clean_text(notes, 500),
                                      "status": "partial" if partial else "completed"})
        van = repo.select("vans", eq={"id": van_id})[0]
        upd = {"last_cleaned_at": now}
        if emptied_waste:
            upd["waste_level"] = 0
        if refilled_water:
            upd["water_level"] = van["water_capacity"]
        repo.update("vans", van_id, upd)
        return True, "Cleaning recorded."
    except Exception as e:
        return False, f"Could not record cleaning: {e}"


def report_maintenance(van_id, operator_id, issue):
    issue = clean_text(issue, 500)
    if len(issue) < 3:
        return False, "Describe the issue (at least 3 characters)."
    try:
        repo.insert("maintenance_logs", {"van_id": van_id, "operator_id": operator_id, "issue": issue,
                                         "resolution_status": "open"})
        return True, "Maintenance issue reported."
    except Exception as e:
        return False, f"Could not report the issue: {e}"


def set_maintenance_status(log_id, status):
    if status not in ("open", "in_progress", "resolved"):
        return False, "Invalid status."
    try:
        repo.update("maintenance_logs", log_id, {"resolution_status": status})
        return True, "Status updated."
    except Exception as e:
        return False, f"Update failed: {e}"


def _names(vans_df):
    return dict(zip(vans_df["id"], vans_df["van_name"]))


def list_cleaning_logs(vans_df, van_ids=None):
    rows = repo.select("cleaning_logs", order="cleaned_at")
    if van_ids is not None:
        rows = [r for r in rows if r["van_id"] in van_ids]
    df = pd.DataFrame(rows, columns=["id", "van_id", "operator_id", "cleaned_at", "cleaning_notes", "status"])
    df["van_name"] = df["van_id"].map(_names(vans_df)).fillna("Removed van")
    df["cleaned_at"] = pd.to_datetime(df["cleaned_at"], utc=True)
    return df


def list_maintenance_logs(vans_df, van_ids=None):
    rows = repo.select("maintenance_logs", order="reported_at")
    if van_ids is not None:
        rows = [r for r in rows if r["van_id"] in van_ids]
    df = pd.DataFrame(rows, columns=["id", "van_id", "operator_id", "issue", "reported_at", "resolution_status"])
    df["van_name"] = df["van_id"].map(_names(vans_df)).fillna("Removed van")
    df["reported_at"] = pd.to_datetime(df["reported_at"], utc=True)
    return df
