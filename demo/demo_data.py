"""In-memory DEMO data. Lives only in st.session_state; never touches Supabase."""
import random
from datetime import datetime, timedelta, timezone

import streamlit as st

import config

ALL = list(config.FACILITIES)
BASIC = ["Private toilet", "Running water", "Handwashing sink", "Proper lighting", "Ventilation"]
NO_ACCESS = [f for f in ALL if f != "Accessible facility"]

# name, type, dlat, dlon, address, availability, hours, facilities, operator
VAN_SPECS = [
    ("[DEMO] Aqua One", "on_demand", 0.010, 0.008, "Demo location · City centre", "available", "06:00-22:00", ALL, "demo-op-1"),
    ("[DEMO] Aqua Two", "on_demand", -0.014, -0.012, "Demo location · West side", "available", "06:00-22:00", NO_ACCESS, "demo-op-2"),
    ("[DEMO] Aqua Three", "on_demand", 0.020, -0.006, "Demo location · North market", "busy", "06:00-22:00", ALL, "demo-op-3"),
    ("[DEMO] Aqua Four", "on_demand", -0.006, 0.022, "Demo location · East bypass", "maintenance", "06:00-22:00", BASIC, "demo-op-3"),
    ("[DEMO] Highway Stop Unit", "stationed", 0.055, 0.045, "Demo location · Highway service lane", "available", "24x7", ALL, "demo-op-1"),
    ("[DEMO] Campus Gate Unit", "stationed", -0.025, 0.028, "Demo location · College main gate", "available", "07:00-20:00", NO_ACCESS, "demo-op-2"),
    ("[DEMO] Event Ground Unit", "stationed", 0.032, -0.030, "Demo location · Exhibition ground", "available", "08:00-23:00", ALL, "demo-op-3"),
    ("[DEMO] Market Square Unit", "stationed", -0.040, -0.020, "Demo location · Old market square", "unavailable", "06:00-21:00", BASIC, None),
]
COMMENTS = ["Clean and well stocked.", "Quick arrival, very helpful operator.", "Good facility, water pressure was low.",
            "Felt safe and private.", "Excellent for a highway stop.", "Could be cleaned more often.", ""]


def _iso(dt):
    return dt.isoformat()


def build_store():
    rng = random.Random(7)
    now = datetime.now(timezone.utc)
    lat0, lon0 = config.DEMO_LAT, config.DEMO_LON
    facilities = [{"id": i + 1, "name": n, "description": d} for i, (n, d) in enumerate(config.FACILITY_CATALOG)]
    fid = {f["name"]: f["id"] for f in facilities}

    profiles = [{"id": "demo-admin", "full_name": "Demo Admin", "email": "admin@demo.local", "phone": None,
                 "role": "admin", "created_at": _iso(now - timedelta(days=40))}]
    for i in range(1, 4):
        profiles.append({"id": f"demo-op-{i}", "full_name": f"Demo Operator {i}", "email": f"operator{i}@demo.local",
                         "phone": None, "role": "operator", "created_at": _iso(now - timedelta(days=35))})
    for i, n in enumerate(["A", "B", "C", "D", "E"], start=1):
        profiles.append({"id": f"demo-cust-{i}", "full_name": f"Demo Customer {n}", "email": f"customer{i}@demo.local",
                         "phone": None, "role": "customer", "created_at": _iso(now - timedelta(days=rng.randint(3, 30)))})

    vans, van_facilities = [], []
    for i, (name, stype, dlat, dlon, addr, avail, hours, facs, op) in enumerate(VAN_SPECS, start=1):
        vid = f"demo-van-{i}"
        wcap, scap = (500, 300) if stype == "on_demand" else (800, 500)
        vans.append({
            "id": vid, "van_name": name, "service_type": stype, "latitude": lat0 + dlat, "longitude": lon0 + dlon,
            "address": addr, "availability_status": avail, "water_capacity": wcap,
            "water_level": round(wcap * rng.uniform(0.35, 0.9)), "waste_capacity": scap,
            "waste_level": round(scap * rng.uniform(0.1, 0.65)), "last_cleaned_at": None,
            "operator_id": op, "operating_hours": hours, "created_at": _iso(now - timedelta(days=30)),
        })
        for f in facs:
            van_facilities.append({"id": f"{vid}-{fid[f]}", "van_id": vid, "facility_id": fid[f], "available": True})

    cleaning, maintenance = [], []
    for v in vans:
        last = None
        for k in range(3):
            t = now - timedelta(days=k * 2 + rng.random(), hours=rng.randint(0, 5))
            last = last or t
            cleaning.append({"id": f"demo-cl-{v['id']}-{k}", "van_id": v["id"], "operator_id": v["operator_id"],
                             "cleaned_at": _iso(t), "cleaning_notes": rng.choice(["Full clean and restock", "Floor and sink sanitised", "Bins emptied, supplies refilled"]),
                             "status": "completed"})
        v["last_cleaned_at"] = _iso(last)
    issues = [("demo-van-4", "Door latch broken", "open"), ("demo-van-2", "Water pump noisy", "in_progress"),
              ("demo-van-1", "Replace ventilation fan filter", "resolved"), ("demo-van-8", "Waste outlet blocked", "open")]
    for k, (vid, issue, st_) in enumerate(issues):
        op = next(v["operator_id"] for v in vans if v["id"] == vid)
        maintenance.append({"id": f"demo-mt-{k}", "van_id": vid, "operator_id": op, "issue": issue,
                            "reported_at": _iso(now - timedelta(days=k + 1)), "resolution_status": st_})

    bookings, feedback = [], []
    usable = [v for v in vans if v["availability_status"] != "unavailable"]
    for k in range(34):
        v = rng.choice(usable)
        t = now - timedelta(days=rng.randint(1, 13), hours=rng.randint(0, 11), minutes=rng.randint(0, 59))
        t = t.replace(hour=rng.choice([7, 8, 9, 10, 12, 13, 15, 17, 18, 19, 20]) % 24)
        status = rng.choices(["completed", "cancelled", "rejected"], [78, 14, 8])[0]
        bookings.append({
            "id": f"demo-bk-{k}", "customer_id": f"demo-cust-{rng.randint(1, 5)}", "van_id": v["id"],
            "booking_type": v["service_type"],
            "user_latitude": v["latitude"] + rng.uniform(-0.01, 0.01) if v["service_type"] == "on_demand" else None,
            "user_longitude": v["longitude"] + rng.uniform(-0.01, 0.01) if v["service_type"] == "on_demand" else None,
            "requested_at": _iso(t), "scheduled_at": _iso(t), "duration_minutes": 30,
            "slot_end": _iso(t + timedelta(minutes=30)), "status": status, "notes": "", "created_at": _iso(t)})
        if status == "completed" and rng.random() < 0.65:
            feedback.append({"id": f"demo-fb-{k}", "booking_id": f"demo-bk-{k}", "customer_id": bookings[-1]["customer_id"],
                             "rating": rng.choice([3, 4, 4, 5, 5, 5]), "comments": rng.choice(COMMENTS), "created_at": _iso(t + timedelta(hours=1))})

    def live(idn, cust, van, status, offset_min, notes):
        v = next(x for x in vans if x["id"] == van)
        t = now + timedelta(minutes=offset_min)
        on_demand = v["service_type"] == "on_demand"
        return {"id": idn, "customer_id": cust, "van_id": van, "booking_type": v["service_type"],
                "user_latitude": lat0 + 0.004 if on_demand else None, "user_longitude": lon0 + 0.003 if on_demand else None,
                "requested_at": _iso(now - timedelta(minutes=8)), "scheduled_at": _iso(t), "duration_minutes": 30,
                "slot_end": _iso(t + timedelta(minutes=30)), "status": status, "notes": notes, "created_at": _iso(now)}
    bookings += [
        live("demo-bk-live-1", "demo-cust-1", "demo-van-3", "on_the_way", -6, "Near the north market entrance"),
        live("demo-bk-live-2", "demo-cust-1", "demo-van-6", "requested", 24 * 60, "Visit after lectures"),
        live("demo-bk-live-3", "demo-cust-2", "demo-van-1", "requested", 0, "Please call on arrival"),
        live("demo-bk-live-4", "demo-cust-3", "demo-van-5", "requested", 26 * 60, "Highway trip stop"),
    ]
    complaints = [
        {"id": "demo-cp-1", "customer_id": "demo-cust-2", "van_id": "demo-van-2", "complaint_type": "Cleanliness",
         "description": "Floor was wet on arrival.", "status": "open", "created_at": _iso(now - timedelta(days=2))},
        {"id": "demo-cp-2", "customer_id": "demo-cust-4", "van_id": "demo-van-4", "complaint_type": "Maintenance",
         "description": "Door would not lock.", "status": "in_review", "created_at": _iso(now - timedelta(days=3))},
        {"id": "demo-cp-3", "customer_id": "demo-cust-5", "van_id": "demo-van-6", "complaint_type": "Water supply",
         "description": "Low water pressure.", "status": "resolved", "created_at": _iso(now - timedelta(days=6))},
    ]
    return {"profiles": profiles, "vans": vans, "facilities": facilities, "van_facilities": van_facilities,
            "bookings": bookings, "cleaning_logs": cleaning, "maintenance_logs": maintenance,
            "feedback": feedback, "complaints": complaints}


def get_store():
    if "demo_store" not in st.session_state:
        st.session_state["demo_store"] = build_store()
    return st.session_state["demo_store"]
