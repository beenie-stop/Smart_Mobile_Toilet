import pandas as pd


def compute_metrics(profiles, vans, bookings):
    roles = pd.Series([p["role"] for p in profiles]) if profiles else pd.Series(dtype=str)
    st_ = bookings["status"]
    return {
        "customers": int((roles == "customer").sum()), "operators": int((roles == "operator").sum()),
        "users": int(len(profiles)), "vans": int(len(vans)),
        "available": int((vans["availability_status"] == "available").sum()),
        "unavailable": int((vans["availability_status"] != "available").sum()),
        "bookings": int(len(bookings)),
        "active": int(st_.isin(["requested", "accepted", "assigned", "on_the_way", "arrived"]).sum()),
        "completed": int((st_ == "completed").sum()), "cancelled": int((st_ == "cancelled").sum()),
    }


def bookings_per_day(bookings, days=30):
    idx = pd.date_range(end=pd.Timestamp.now(tz="UTC").normalize(), periods=days, freq="D")
    if bookings.empty:
        return pd.DataFrame({"date": idx.date, "bookings": 0})
    s = bookings.groupby(bookings["requested_at"].dt.normalize()).size().reindex(idx, fill_value=0)
    return pd.DataFrame({"date": idx.date, "bookings": s.values})


def status_counts(bookings):
    if bookings.empty:
        return pd.DataFrame({"status": [], "count": []})
    c = bookings["status_label"].value_counts().reset_index()
    c.columns = ["status", "count"]
    return c


def bookings_by_van(bookings):
    if bookings.empty:
        return pd.DataFrame({"van": [], "bookings": []})
    c = bookings["van_name"].value_counts().reset_index()
    c.columns = ["van", "bookings"]
    return c


def hourly_demand(bookings):
    hrs = pd.Series(0, index=range(24))
    if not bookings.empty:
        local = bookings["requested_at"].dt.tz_convert("Asia/Kolkata").dt.hour
        hrs = local.value_counts().reindex(range(24), fill_value=0)
    return pd.DataFrame({"hour": hrs.index, "bookings": hrs.values})


def rating_by_van(feedback):
    if feedback.empty:
        return pd.DataFrame({"van": [], "avg_rating": []})
    g = feedback.groupby("van_name")["rating"].mean().round(2).reset_index()
    g.columns = ["van", "avg_rating"]
    return g.sort_values("avg_rating")


def service_split(bookings):
    if bookings.empty:
        return pd.DataFrame({"type": [], "count": []})
    c = bookings["booking_type"].map({"on_demand": "On-demand", "stationed": "Stationed"}).value_counts().reset_index()
    c.columns = ["type", "count"]
    return c
