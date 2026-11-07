import plotly.express as px

import config

PAL = [config.TEAL, config.BLUE, config.GREEN, config.ORANGE, config.RED, "#7C93A1"]


def _style(fig, h=300):
    fig.update_layout(template="plotly_white", height=h, margin=dict(l=10, r=10, t=40, b=10),
                      font=dict(family="Plus Jakarta Sans, sans-serif"), legend_title_text="")
    return fig


def trend(df):
    return _style(px.area(df, x="date", y="bookings", title="Bookings per day (last 30 days)", color_discrete_sequence=[config.BLUE]))


def status_donut(df):
    fig = px.pie(df, names="status", values="count", hole=0.55, title="Bookings by status", color_discrete_sequence=PAL)
    return _style(fig)


def by_van(df):
    return _style(px.bar(df, x="bookings", y="van", orientation="h", title="Usage by van", color_discrete_sequence=[config.TEAL]))


def hourly(df):
    return _style(px.bar(df, x="hour", y="bookings", title="Demand by hour of day (IST)", color_discrete_sequence=[config.BLUE]))


def ratings(df):
    fig = px.bar(df, x="avg_rating", y="van", orientation="h", title="Average rating by van", color_discrete_sequence=[config.GREEN])
    fig.update_xaxes(range=[0, 5])
    return _style(fig)


def split(df):
    return _style(px.pie(df, names="type", values="count", hole=0.55, title="On-demand vs stationed", color_discrete_sequence=[config.TEAL, config.BLUE]))
