from html import escape

import config
from utils.validation import is_open_now


def _h(s):
    return "".join(line.strip() for line in s.splitlines())


def badge(text, color):
    return f'<span class="badge" style="background:{color}">{escape(str(text))}</span>'


def metric_card(label, value, color=config.TEAL):
    return _h(f'<div class="metric" style="--c:{color}"><div class="v">{escape(str(value))}</div>'
              f'<div class="l">{escape(label)}</div></div>')


def status_badge(status, booking_type=None):
    return badge(config.status_label(status, booking_type), config.STATUS_COLORS.get(status, config.SLATE))


def availability_badge(status):
    return badge(status.replace("_", " ").title(), config.AVAIL_COLORS.get(status, config.SLATE))


def van_card(row, show_distance=True):
    stationed = row["service_type"] == "stationed"
    tag = "📍 Stationed facility" if stationed else "🚐 Mobile van · on-demand"
    chips = "".join(f'<span class="chip">✓ {escape(f)}</span>' for f in row["facilities"])
    dist = f' · <b>{row["distance_km"]:.1f} km away</b>' if show_distance and "distance_km" in row else ""
    open_now = "Open now" if is_open_now(row["operating_hours"]) else "Closed now"
    cleaned = row["last_cleaned_at"]
    cleaned_txt = f' · Last cleaned {cleaned:%d %b, %H:%M}' if hasattr(cleaned, "strftime") else ""
    return _h(f'''<div class="card {'stationed' if stationed else 'mobile'}">
      <h4>{escape(row["van_name"])}</h4>
      <div>{availability_badge(row["availability_status"])}{badge(tag, config.BLUE if stationed else config.TEAL)}</div>
      <div class="muted" style="margin:.35rem 0">{escape(row["address"] or "")}{dist}<br>
      🕒 {escape(row["operating_hours"])} ({open_now}){cleaned_txt}</div>
      <div>{chips}</div></div>''')


def status_tracker(status, booking_type):
    steps = config.TRACK_STEPS[booking_type]
    if status in ("cancelled", "rejected"):
        return _h(f'<div class="muted">{status_badge(status, booking_type)} This booking is closed.</div>')
    cur = steps.index(status) if status in steps else 0
    out = []
    for i, s in enumerate(steps):
        cls = "done" if i < cur or status == "completed" else ("now" if i == cur else "")
        mark = "✓" if cls == "done" else str(i + 1)
        out.append(f'<div class="step {cls}"><div class="dot">{mark}</div>{escape(config.status_label(s, booking_type))}</div>')
    return f'<div class="tracker">{"".join(out)}</div>'
