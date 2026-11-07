import config
from utils.validation import clean_text


def geocode(query):
    """Place name -> (lat, lon, label) via OpenStreetMap Nominatim. None if disabled/not found."""
    if not config.GEOCODING_ENABLED:
        return None
    q = clean_text(query, 200)
    if len(q) < 3:
        return None
    try:
        from geopy.geocoders import Nominatim
        loc = Nominatim(user_agent="smart-mobile-toilet-network", timeout=8).geocode(q)
    except Exception:
        return None
    return (loc.latitude, loc.longitude, loc.address) if loc else None
