"""
app.py - Dublin Bikes availability dashboard (Streamlit).

Operational view of the trained availability model plus city-level analytics:

  1. Operations map     - predicted bikes / alert status / station roles
  2. Rebalancing planner- concrete "move X bikes from A to B" plan + download
  3. Station explorer   - 24h profile, reliability card, station comparison
  4. City patterns      - weekly rhythm heatmap, daily trend, commuter roles
  5. Model performance  - honest held-out metrics, confusion matrix, figures

Everything is served from small precomputed CSVs in outputs/dashboard/
(built by train_model.py and make_dashboard_extras.py), so the app starts
instantly and never loads the heavy fitted model.

Run:  streamlit run app.py
"""
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE = Path(__file__).resolve().parent
DASH = BASE / "outputs" / "dashboard"
MET = BASE / "outputs" / "metrics"
FIGS = BASE / "outputs" / "figures"

DOW_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
             "Saturday", "Sunday"]
DOW_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ---- validated palette (dataviz method; checked on this dark surface) -------
S1, S2, S3 = "#3987e5", "#d95926", "#199e70"        # categorical slots 1-3
CRIT, SERIOUS, NEUTRAL = "#d03b3b", "#ec835a", "#64748b"  # status + recessive
INK, MUTED = "#e2e8f0", "#8b94a7"
GRID = "rgba(148,163,184,0.10)"
AXIS = "rgba(148,163,184,0.28)"
# sequential blue, dark-mode direction: low recedes into the surface
SEQ = ["#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"]
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

st.set_page_config(page_title="Dublin Bikes - Availability Forecast",
                   page_icon="🚲", layout="wide")


def style(fig, height=420, legend=False, ltitle=None):
    """One shared look: transparent surface, hairline grid, system sans."""
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=INK, size=13),
        title_font=dict(size=15, color=INK),
        margin=dict(l=8, r=8, t=54 if fig.layout.title.text else 16, b=8),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0,
                    title=ltitle, bgcolor="rgba(0,0,0,0)",
                    font=dict(size=12, color=INK)),
        hoverlabel=dict(font=dict(family=FONT, size=12)),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=AXIS,
                     tickfont=dict(color=MUTED), title_font=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=AXIS,
                     tickfont=dict(color=MUTED), title_font=dict(color=MUTED))
    return fig


def section(title, caption=None):
    """Uniform section header used across every tab."""
    st.markdown(f'<div class="sec-h">{title}</div>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<div class="sec-c">{caption}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- data access
@st.cache_data
def load_data():
    stations = pd.read_csv(DASH / "stations.csv")
    grid = pd.read_csv(DASH / "predictions_grid.csv")
    actual = pd.read_csv(DASH / "actual_profiles.csv")
    metrics = pd.read_csv(MET / "model_metrics.csv")
    risk = json.loads((MET / "empty_risk_report.json").read_text())
    meta = json.loads((BASE / "outputs" / "model" / "meta.json").read_text())
    grid = grid.merge(stations[["station_id", "name", "lat", "lon"]],
                      on="station_id", how="left")
    return stations, grid, actual, metrics, risk, meta


@st.cache_data
def load_extras():
    """Analytical extras from make_dashboard_extras.py (may be absent)."""
    try:
        heat = pd.read_csv(DASH / "citywide_heatmap.csv")
        daily = pd.read_csv(DASH / "daily_series.csv", parse_dates=["date"])
        sstats = pd.read_csv(DASH / "station_stats.csv")
        return heat, daily, sstats
    except FileNotFoundError:
        return None, None, None


def haversine_km(lat1, lon1, lat2, lon2):
    p = np.radians
    dlat, dlon = p(lat2 - lat1), p(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(p(lat1)) * np.cos(p(lat2)) * np.sin(dlon / 2) ** 2)
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


stations, grid, actual, metrics, risk, meta = load_data()
heat, daily, sstats = load_extras()
best_model = meta["best_model"]
best_row = metrics.loc[metrics["model"] == best_model].iloc[0]
EMPTY_THR = int(meta.get("empty_threshold", 2))

# ---------------------------------------------------------------- global css
DATASET_URL = "https://data.smartdublin.ie/dataset/dublinbikes-api"

st.markdown("""
<style>
.block-container { padding-top: 1.1rem; padding-bottom: 2.5rem;
                   max-width: 1350px; }
.stTabs [data-baseweb="tab-list"] { gap: 4px;
    border-bottom: 1px solid rgba(148,163,184,0.15); }
.stTabs [data-baseweb="tab"] { padding: 8px 14px;
    border-radius: 8px 8px 0 0; }
.stTabs [aria-selected="true"] { background: rgba(59,130,246,0.10); }

.page-head { display: flex; justify-content: space-between;
             align-items: flex-end; gap: 1rem; flex-wrap: wrap;
             margin-bottom: 0.4rem; }
.ph-title { font-size: 1.45rem; font-weight: 700; color: #f1f5f9;
            line-height: 1.1; }
.ph-sub   { font-size: 0.85rem; color: #8b94a7; margin-top: 3px; }
.ph-badges { display: flex; gap: 8px; flex-wrap: wrap; }
.chip { font-size: 0.78rem; color: #cbd5e1; background: #111c2e;
        border: 1px solid rgba(148,163,184,0.18); border-radius: 999px;
        padding: 4px 12px; white-space: nowrap; }
.chip-blue { border-color: rgba(59,130,246,0.5);
             background: rgba(59,130,246,0.12); color: #93c5fd; }

.sec-h { font-size: 1.0rem; font-weight: 600; color: #e2e8f0;
         margin: 0.15rem 0 0.05rem 0; }
.sec-c { font-size: 0.78rem; color: #8b94a7; margin-bottom: 0.55rem; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0e1729 0%, #0b1220 45%);
    border-right: 1px solid rgba(148,163,184,0.12);
}
[data-testid="stSidebar"] .stButton button {
    font-size: 0.78rem; padding: 0.28rem 0.3rem; width: 100%;
    background: #111c2e; border: 1px solid rgba(148,163,184,0.18);
    color: #cbd5e1; border-radius: 8px; transition: border-color .15s;
}
[data-testid="stSidebar"] .stButton button:hover {
    border-color: #3b82f6; color: #f1f5f9;
}
.sb-brand { display: flex; gap: 0.7rem; align-items: center;
            padding: 0.15rem 0 0.35rem 0; }
.sb-logo  { width: 42px; height: 42px; border-radius: 12px; flex: none;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.35rem;
            background: linear-gradient(135deg, #1d4ed8, #3b82f6);
            box-shadow: 0 4px 14px rgba(59,130,246,0.35); }
.sb-title { font-size: 1.02rem; font-weight: 700; color: #f1f5f9;
            line-height: 1.15; }
.sb-sub   { font-size: 0.72rem; color: #8b94a7; }
.sb-section { font-size: 0.68rem; letter-spacing: 0.14em;
              text-transform: uppercase; color: #64748b; font-weight: 600;
              margin: 1.0rem 0 0.15rem 0; }
.sb-foot { font-size: 0.72rem; color: #64748b; line-height: 1.55;
           margin-top: 0.5rem; }
.sb-foot a { color: #3b82f6; text-decoration: none; }
.sb-foot a:hover { text-decoration: underline; }
</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------------- sidebar
if "dow_sel" not in st.session_state:
    st.session_state.dow_sel = "Wednesday"
if "hour_sel" not in st.session_state:
    st.session_state.hour_sel = 8


def jump(day=None, hr=None):
    """Preset-button callback: move the scenario controls."""
    if day is not None:
        st.session_state.dow_sel = day
    if hr is not None:
        st.session_state.hour_sel = hr


def jump_now():
    now = datetime.now()
    jump(DOW_NAMES[now.weekday()], now.hour)


with st.sidebar:
    st.markdown(
        '<div class="sb-brand"><div class="sb-logo">🚲</div>'
        '<div><div class="sb-title">Dublin Bikes</div>'
        '<div class="sb-sub">Availability Intelligence</div></div></div>',
        unsafe_allow_html=True)

    st.markdown('<p class="sb-section">Forecast scenario</p>',
                unsafe_allow_html=True)
    dow_name = st.selectbox("Day of week", DOW_NAMES, key="dow_sel")
    dow = DOW_NAMES.index(dow_name)
    hour = st.slider("Hour of day", 0, 23, key="hour_sel", format="%d:00")

    r1c1, r1c2 = st.columns(2)
    r1c1.button("🌅 AM peak", on_click=jump, kwargs={"hr": 8},
                help="Jump to 08:00 — the morning commuter crunch")
    r1c2.button("☀️ Midday", on_click=jump, kwargs={"hr": 13})
    r2c1, r2c2 = st.columns(2)
    r2c1.button("🌆 PM peak", on_click=jump, kwargs={"hr": 17},
                help="Jump to 17:00 — the evening tide turns")
    r2c2.button("🌙 Night", on_click=jump, kwargs={"hr": 23})
    st.button("📍 Jump to now", on_click=jump_now,
              help="Set the scenario to the current weekday and hour")

    st.markdown('<p class="sb-section">Alerting</p>', unsafe_allow_html=True)
    thr = st.slider("Empty-risk threshold (bikes)", 0, 6, EMPTY_THR,
                    help="A station predicted at or below this many bikes "
                         "raises an empty-risk alert.")

    situation = st.container()   # filled below, once the snapshot exists

    with st.expander("ℹ️ About the model"):
        st.markdown(
            f"**{best_model}** trained on hourly station data, April-May 2026, "
            f"evaluated on the unseen June 2026 month.\n"
            f"* MAE **{best_row['mae']:.2f} bikes** · R² **{best_row['r2']:.3f}**\n"
            f"* Alert precision **{risk[best_model]['precision']:.0%}**\n"
            f"* 1.86M raw snapshots → 249,940 station-hours, 0 missing values")

    st.markdown(
        f'<div class="sb-foot"><b>{len(stations)} stations</b> · '
        f"{meta['date_range'][0]} → {meta['date_range'][1]}<br>"
        f'Data: <a href="{DATASET_URL}" target="_blank">'
        'Smart Dublin open data ↗</a></div>', unsafe_allow_html=True)

# Snapshot for the selected (day, hour) + alert states
snap = grid[(grid["day_of_week"] == dow) & (grid["hour"] == hour)].copy()
snap["docks_pred"] = (snap["capacity"] - snap["pred_bikes"]).clip(lower=0)
snap["empty_risk"] = snap["pred_bikes"] <= thr
snap["full_risk"] = snap["docks_pred"] <= EMPTY_THR
snap["status"] = np.select([snap["empty_risk"], snap["full_risk"]],
                           ["Empty-risk", "Full-risk"], default="Healthy")
if sstats is not None:
    snap = snap.merge(sstats[["station_id", "role"]], on="station_id", how="left")

prev = grid[(grid["day_of_week"] == dow) & (grid["hour"] == (hour - 1) % 24)]
prev_empty = int((prev["pred_bikes"] <= thr).sum())
prev_full = int(((prev["capacity"] - prev["pred_bikes"]).clip(lower=0)
                 <= EMPTY_THR).sum())
n_empty, n_full = int(snap["empty_risk"].sum()), int(snap["full_risk"].sum())

# Sidebar situation strip: live alert count + a 24h citywide sparkline.
with situation:
    st.markdown('<p class="sb-section">Situation</p>', unsafe_allow_html=True)
    s1c, s2c = st.columns(2)
    s1c.metric("Alerts", n_empty, delta=n_empty - prev_empty,
               delta_color="inverse", border=True,
               help=f"Empty-risk stations at {hour:02d}:00 vs {(hour - 1) % 24:02d}:00")
    s2c.metric("Occupancy", f"{snap['pred_occupancy'].mean():.0%}", border=True,
               help="Citywide mean predicted occupancy at the selected hour")

    day_prof = (grid[grid["day_of_week"] == dow]
                .groupby("hour")["pred_bikes"].mean())
    spark = go.Figure()
    spark.add_trace(go.Scatter(
        x=day_prof.index, y=day_prof.values, mode="lines",
        line=dict(color=S1, width=2),
        fill="tozeroy", fillcolor="rgba(57,135,229,0.12)",
        hovertemplate="%{x}:00 · %{y:.1f} bikes<extra></extra>"))
    spark.add_trace(go.Scatter(
        x=[hour], y=[float(day_prof.loc[hour])], mode="markers",
        marker=dict(size=9, color="#cde2fb", line=dict(width=2, color=S1)),
        hoverinfo="skip"))
    spark.update_layout(
        height=92, margin=dict(l=0, r=2, t=4, b=0), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=MUTED, size=10))
    spark.update_xaxes(showgrid=False, zeroline=False, showline=False,
                       tickvals=[0, 6, 12, 18, 23], tickfont=dict(color=MUTED))
    spark.update_yaxes(visible=False)
    st.plotly_chart(spark, use_container_width=True,
                    config={"displayModeBar": False})
    st.caption(f"Citywide mean predicted bikes · {dow_name}s")

# ---------------------------------------------------------------- page header
st.markdown(
    f'<div class="page-head">'
    f'<div><div class="ph-title">Operations dashboard</div>'
    f'<div class="ph-sub">Hourly availability forecast and rebalancing '
    f'intelligence for the dublinbikes network</div></div>'
    f'<div class="ph-badges">'
    f'<span class="chip chip-blue">📅 {dow_name} {hour:02d}:00</span>'
    f'<span class="chip">🌲 {best_model} · MAE {best_row["mae"]:.2f}</span>'
    f'<span class="chip">🎯 Alert precision '
    f'{risk[best_model]["precision"]:.0%}</span>'
    f'</div></div>', unsafe_allow_html=True)

tabs = st.tabs(["🗺️ Operations map", "🚚 Rebalancing planner",
                "📈 Station explorer", "🏙️ City patterns",
                "🧪 Model performance"])

# ============================================================ 1 · OPERATIONS
with tabs[0]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stations", f"{len(snap)}", border=True)
    c2.metric("Empty-risk alerts", n_empty, delta=n_empty - prev_empty,
              delta_color="inverse", border=True,
              help=f"Predicted ≤ {thr} bikes · delta vs {(hour - 1) % 24:02d}:00")
    c3.metric("Full-risk alerts", n_full, delta=n_full - prev_full,
              delta_color="inverse", border=True,
              help=f"Predicted ≤ {EMPTY_THR} free docks · returns blocked")
    c4.metric("Avg predicted occupancy", f"{snap['pred_occupancy'].mean():.0%}",
              border=True)

    with st.container(border=True):
        section(f"City map — {dow_name} {hour:02d}:00",
                "Bubble size reflects dock capacity — hover any station for "
                "exact values. Switch views to see alerts or commuter roles.")
        view = st.radio("Map view",
                        ["Predicted bikes", "Alert status", "Station role"],
                        horizontal=True, label_visibility="collapsed")

        hover = {"lat": False, "lon": False, "capacity": True,
                 "pred_bikes": ":.1f", "pred_occupancy": ":.0%"}
        map_fig = None
        if view == "Predicted bikes":
            map_fig = px.scatter_mapbox(
                snap, lat="lat", lon="lon", color="pred_bikes", size="capacity",
                color_continuous_scale=SEQ, range_color=[0, 20],
                hover_name="name", hover_data=hover,
                zoom=12.4, height=500, mapbox_style="carto-darkmatter")
            map_fig.update_layout(coloraxis_colorbar=dict(
                title="Bikes", tickfont=dict(color=MUTED), outlinewidth=0))
        elif view == "Alert status":
            map_fig = px.scatter_mapbox(
                snap, lat="lat", lon="lon", color="status", size="capacity",
                color_discrete_map={"Empty-risk": CRIT, "Full-risk": SERIOUS,
                                    "Healthy": NEUTRAL},
                category_orders={"status": ["Empty-risk", "Full-risk", "Healthy"]},
                hover_name="name", hover_data=hover,
                zoom=12.4, height=500, mapbox_style="carto-darkmatter")
        elif "role" in snap:
            map_fig = px.scatter_mapbox(
                snap, lat="lat", lon="lon", color="role", size="capacity",
                color_discrete_map={
                    "Commuter destination (fills in AM)": S1,
                    "Commuter origin (fills in PM)": S2,
                    "Balanced": NEUTRAL},
                hover_name="name", hover_data=hover,
                zoom=12.4, height=500, mapbox_style="carto-darkmatter")
        else:
            st.info("Run `python src/make_dashboard_extras.py` to enable roles.")
        if map_fig is not None:
            map_fig.update_layout(
                margin=dict(l=0, r=0, t=4, b=4),
                font=dict(family=FONT, color=INK),
                legend=dict(orientation="h", y=0.02, x=0.02,
                            bgcolor="rgba(11,18,32,0.75)", font=dict(color=INK)))
            st.plotly_chart(map_fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            section("🔴 Refill first",
                    "Lowest predicted bikes at the selected hour")
            empty_tbl = (snap.sort_values("pred_bikes").head(10)
                         [["name", "pred_bikes", "capacity", "pred_occupancy"]]
                         .rename(columns={"name": "Station",
                                          "pred_bikes": "Pred. bikes",
                                          "capacity": "Docks",
                                          "pred_occupancy": "Occupancy"}))
            st.dataframe(empty_tbl, hide_index=True, use_container_width=True,
                         column_config={
                             "Pred. bikes": st.column_config.NumberColumn(format="%.1f"),
                             "Occupancy": st.column_config.ProgressColumn(
                                 format="percent", min_value=0, max_value=1)})
    with right:
        with st.container(border=True):
            section("🟠 Collect first",
                    "Almost no free docks — returns about to be blocked")
            full_tbl = (snap.sort_values("docks_pred").head(10)
                        [["name", "docks_pred", "capacity", "pred_occupancy"]]
                        .rename(columns={"name": "Station",
                                         "docks_pred": "Pred. free docks",
                                         "capacity": "Docks",
                                         "pred_occupancy": "Occupancy"}))
            st.dataframe(full_tbl, hide_index=True, use_container_width=True,
                         column_config={
                             "Pred. free docks": st.column_config.NumberColumn(format="%.1f"),
                             "Occupancy": st.column_config.ProgressColumn(
                                 format="percent", min_value=0, max_value=1)})

# ======================================================== 2 · REBALANCING
with tabs[1]:
    section(f"Suggested rebalancing plan — {dow_name} {hour:02d}:00",
            "Keep every station inside a 25-75% occupancy comfort band: "
            "collect from stations predicted above the band, refill those "
            "below it, pairing each refill with the nearest surplus stock.")

    plan = snap.copy()
    plan["lo"] = np.floor(0.25 * plan["capacity"])
    plan["hi"] = np.ceil(0.75 * plan["capacity"])
    plan["need"] = np.ceil((plan["lo"] - plan["pred_bikes"]).clip(lower=0)).astype(int)
    plan["spare"] = np.floor((plan["pred_bikes"] - plan["hi"]).clip(lower=0)).astype(int)

    deficits = plan[plan["need"] > 0].sort_values("need", ascending=False)
    surplus = plan[plan["spare"] > 0].set_index("station_id")
    stock = surplus["spare"].to_dict()

    moves = []
    for _, d in deficits.iterrows():
        need = int(d["need"])
        while need > 0 and any(v > 0 for v in stock.values()):
            avail = surplus[surplus.index.map(lambda s: stock.get(s, 0) > 0)]
            dist = haversine_km(d["lat"], d["lon"], avail["lat"], avail["lon"])
            src = avail.index[int(np.argmin(dist))]
            qty = min(need, stock[src])
            moves.append({"From": surplus.loc[src, "name"], "To": d["name"],
                          "Bikes": qty,
                          "Distance (km)": round(float(np.min(dist)), 2)})
            stock[src] -= qty
            need -= qty

    moves_df = pd.DataFrame(moves)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Stations below band", int((plan['need'] > 0).sum()), border=True)
    k2.metric("Stations above band", int((plan['spare'] > 0).sum()), border=True)
    k3.metric("Bikes to move", int(moves_df["Bikes"].sum()) if len(moves_df) else 0,
              border=True)
    k4.metric("Truck distance", (f"{moves_df['Distance (km)'].sum():.1f} km"
                                 if len(moves_df) else "0 km"), border=True)

    mcol, tcol = st.columns([1.15, 1])
    with mcol:
        with st.container(border=True):
            section("Band status map",
                    "Red = refill, blue = collect, grey = inside the band")
            plan["band"] = np.select([plan["need"] > 0, plan["spare"] > 0],
                                     ["Refill (below band)", "Collect (above band)"],
                                     default="In band")
            band_fig = px.scatter_mapbox(
                plan, lat="lat", lon="lon", color="band", size="capacity",
                color_discrete_map={"Refill (below band)": CRIT,
                                    "Collect (above band)": S1,
                                    "In band": NEUTRAL},
                category_orders={"band": ["Refill (below band)",
                                          "Collect (above band)", "In band"]},
                hover_name="name",
                hover_data={"lat": False, "lon": False, "pred_bikes": ":.1f",
                            "need": True, "spare": True},
                zoom=12.1, height=440, mapbox_style="carto-darkmatter")
            band_fig.update_layout(
                margin=dict(l=0, r=0, t=4, b=4),
                font=dict(family=FONT, color=INK),
                legend=dict(orientation="h", y=0.02, x=0.02,
                            bgcolor="rgba(11,18,32,0.75)", font=dict(color=INK)))
            st.plotly_chart(band_fig, use_container_width=True)
    with tcol:
        with st.container(border=True):
            section("Move list", "Nearest-surplus pairing, ready for dispatch")
            if len(moves_df):
                st.dataframe(moves_df, hide_index=True, use_container_width=True,
                             height=395)
                st.download_button(
                    "⬇️ Download plan (CSV)",
                    moves_df.to_csv(index=False).encode(),
                    file_name=f"rebalancing_{DOW_SHORT[dow]}_{hour:02d}00.csv",
                    mime="text/csv", use_container_width=True)
            else:
                st.success("No moves needed — every station is inside its "
                           "comfort band at this hour.")

# ======================================================= 3 · STATION EXPLORER
with tabs[2]:
    csel, ccmp = st.columns([1, 1.4])
    names = stations.sort_values("name")["name"].tolist()
    pick = csel.selectbox("Station", names)
    compare = ccmp.multiselect("Compare with (typical actual profiles)",
                               [n for n in names if n != pick], max_selections=2)

    sid = int(stations.loc[stations["name"] == pick, "station_id"].iloc[0])
    cap = float(stations.loc[stations["station_id"] == sid, "capacity"].iloc[0])

    if sstats is not None:
        row = sstats[sstats["station_id"] == sid].iloc[0]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Role", row["role"].split(" (")[0], border=True,
                  help=row["role"])
        m2.metric("Hours empty (Apr-Jun)", f"{row['pct_hours_empty']:.0%}",
                  border=True, help="Share of station-hours at ≤ 2 bikes")
        m3.metric("Hours full", f"{row['pct_hours_full']:.0%}", border=True,
                  help="Share of station-hours at ≤ 2 free docks")
        m4.metric("Docks", f"{cap:.0f}", border=True)

    prof_pred = (grid[(grid["station_id"] == sid) & (grid["day_of_week"] == dow)]
                 .sort_values("hour"))
    prof_act = (actual[(actual["station_id"] == sid) &
                       (actual["day_of_week"] == dow)].sort_values("hour"))

    with st.container(border=True):
        section(f"{pick.title()} — {dow_name} profile",
                f"Shaded band = empty-risk zone (≤ {thr} bikes). "
                "Hover any point for exact values.")
        fig = go.Figure()
        fig.add_hrect(y0=0, y1=thr, fillcolor="rgba(208,59,59,0.10)", line_width=0)
        if not compare:
            fig.add_trace(go.Scatter(
                x=prof_act["hour"], y=prof_act["actual_bikes"],
                mode="lines+markers",
                name="Typical actual (Apr-Jun mean)",
                line=dict(color=MUTED, width=2), marker=dict(size=7)))
            fig.add_trace(go.Scatter(
                x=prof_pred["hour"], y=prof_pred["pred_bikes"],
                mode="lines+markers",
                name=f"Model prediction ({best_model})",
                line=dict(color=S1, width=2), marker=dict(size=7)))
        else:
            palette = [S1, S2, S3]
            for i, nm in enumerate([pick] + compare):
                s = int(stations.loc[stations["name"] == nm, "station_id"].iloc[0])
                pa = (actual[(actual["station_id"] == s) &
                             (actual["day_of_week"] == dow)].sort_values("hour"))
                fig.add_trace(go.Scatter(
                    x=pa["hour"], y=pa["actual_bikes"], mode="lines+markers",
                    name=nm.title(), line=dict(color=palette[i], width=2),
                    marker=dict(size=7)))
        fig.add_hline(y=cap, line_dash="dot", line_color=AXIS,
                      annotation_text="capacity", annotation_font_color=MUTED)
        fig.update_xaxes(dtick=2, title="Hour of day")
        fig.update_yaxes(title="Bikes available", rangemode="tozero")
        st.plotly_chart(style(fig, height=420, legend=True),
                        use_container_width=True)

    risky = prof_pred[prof_pred["pred_bikes"] <= thr]["hour"].tolist()
    if risky:
        st.warning("⚠️ Predicted empty-risk hours on "
                   f"{dow_name}s: " + ", ".join(f"{h:02d}:00" for h in risky))
    else:
        st.success(f"No predicted empty-risk hours at this station on {dow_name}s.")

# ========================================================= 4 · CITY PATTERNS
with tabs[3]:
    if heat is None:
        st.info("Run `python src/make_dashboard_extras.py` to build the "
                "city-pattern datasets.")
    else:
        a, b = st.columns([1, 1.15])
        with a:
            with st.container(border=True):
                section("Weekly rhythm",
                        "The commuter tide: docks drain through the morning "
                        "peak and refill through the evening, weekdays only.")
                hm = heat.pivot(index="hour", columns="day_of_week",
                                values="mean_occupancy")
                hfig = go.Figure(go.Heatmap(
                    z=hm.values, x=DOW_SHORT, y=hm.index,
                    colorscale=[[i / (len(SEQ) - 1), c]
                                for i, c in enumerate(SEQ)],
                    zmin=0.2, zmax=0.55,
                    colorbar=dict(title="Occupancy", tickformat=".0%",
                                  tickfont=dict(color=MUTED), outlinewidth=0),
                    hovertemplate="%{x} %{y}:00<br>occupancy %{z:.0%}"
                                  "<extra></extra>"))
                hfig.update_yaxes(dtick=4, title="Hour of day")
                st.plotly_chart(style(hfig, height=400), use_container_width=True)
        with b:
            with st.container(border=True):
                section("Daily citywide occupancy, April → June 2026",
                        "A stable weekly cycle with no drift between training "
                        "months and the held-out June — the temporal split is fair.")
                dfig = go.Figure()
                dfig.add_vrect(x0="2026-06-01", x1="2026-06-30",
                               fillcolor="rgba(57,135,229,0.08)", line_width=0)
                dfig.add_trace(go.Scatter(
                    x=daily["date"], y=daily["mean_occupancy"], mode="lines",
                    name="Mean occupancy", line=dict(color=S1, width=2)))
                dfig.add_annotation(x="2026-06-15", y=1.02, yref="paper",
                                    showarrow=False, text="held-out test month",
                                    font=dict(color=MUTED, size=12))
                dfig.update_yaxes(tickformat=".0%", title="Occupancy")
                dfig.update_xaxes(title=None)
                st.plotly_chart(style(dfig, height=400), use_container_width=True)

        c, d = st.columns([1.15, 1])
        with c:
            with st.container(border=True):
                section("Station roles — who fills when?",
                        "Weekday AM-peak vs PM-peak occupancy per station; "
                        "bubble size = dock capacity.")
                rfig = px.scatter(
                    sstats, x="am_occ", y="pm_occ", color="role",
                    size="capacity",
                    color_discrete_map={
                        "Commuter destination (fills in AM)": S1,
                        "Commuter origin (fills in PM)": S2,
                        "Balanced": NEUTRAL},
                    hover_name="name",
                    hover_data={"am_occ": ":.0%", "pm_occ": ":.0%",
                                "capacity": True, "role": False},
                    labels={"am_occ": "AM-peak occupancy (7-9h)",
                            "pm_occ": "PM-peak occupancy (16-19h)"})
                rfig.add_shape(type="line", x0=0, y0=0, x1=1, y1=1,
                               line=dict(color=AXIS, width=1))
                rfig.update_traces(marker=dict(
                    line=dict(width=1, color="#0b1220")))
                rfig.update_xaxes(tickformat=".0%", range=[0, 1])
                rfig.update_yaxes(tickformat=".0%", range=[0, 1])
                st.plotly_chart(style(rfig, height=420, legend=True),
                                use_container_width=True)
        with d:
            with st.container(border=True):
                section("Most under-served stations",
                        "Share of all hours spent at ≤ 2 bikes, April-June")
                worst = (sstats.sort_values("pct_hours_empty", ascending=False)
                         .head(10).iloc[::-1])
                wfig = go.Figure(go.Bar(
                    x=worst["pct_hours_empty"], y=worst["name"].str.title(),
                    orientation="h", marker_color=S1,
                    text=[f"{v:.0%}" for v in worst["pct_hours_empty"]],
                    textposition="outside",
                    textfont=dict(color=INK, size=12),
                    hovertemplate="%{y}: empty %{x:.0%} of hours"
                                  "<extra></extra>"))
                wfig.update_xaxes(tickformat=".0%",
                                  range=[0, worst["pct_hours_empty"].max() * 1.25])
                st.plotly_chart(style(wfig, height=420), use_container_width=True)

# ======================================================= 5 · MODEL PERFORMANCE
with tabs[4]:
    section("Honest evaluation — unseen June 2026 test month",
            "Models trained on April + May 2026 only; every number below is "
            "measured on the held-out June 2026 month (temporal split, no leakage).")

    a, b = st.columns([1.15, 1])
    with a:
        with st.container(border=True):
            section("Model comparison",
                    "Mean absolute error in bikes — lower is better")
            order = metrics.sort_values("mae", ascending=False)
            short = [m.split(" (")[0] for m in order["model"]]
            colors = [S1 if m == best_model else "rgba(139,148,167,0.45)"
                      for m in order["model"]]
            mfig = go.Figure(go.Bar(
                x=order["mae"], y=short, orientation="h", marker_color=colors,
                text=[f"{v:.2f}" for v in order["mae"]], textposition="outside",
                textfont=dict(color=INK, size=12),
                hovertemplate="%{y}: MAE %{x:.2f} bikes<extra></extra>"))
            mfig.update_xaxes(range=[0, order["mae"].max() * 1.18])
            st.plotly_chart(style(mfig, height=300), use_container_width=True)
            show = metrics.rename(columns={"model": "Model", "mae": "MAE (bikes)",
                                           "rmse": "RMSE (bikes)", "r2": "R²"})
            st.dataframe(show, hide_index=True, use_container_width=True,
                         column_config={
                             "MAE (bikes)": st.column_config.NumberColumn(format="%.2f"),
                             "RMSE (bikes)": st.column_config.NumberColumn(format="%.2f"),
                             "R²": st.column_config.NumberColumn(format="%.3f")})
    with b:
        with st.container(border=True):
            section(f"Empty-risk alert quality — {best_model}",
                    f"Alert = predicted ≤ {risk[best_model]['threshold_bikes']} bikes")
            er = risk[best_model]
            cm = er["confusion"]
            z = [[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]]
            total = sum(cm.values())
            txt = [[f"TN {cm['tn']:,}<br>{cm['tn'] / total:.0%}",
                    f"FP {cm['fp']:,}<br>{cm['fp'] / total:.0%}"],
                   [f"FN {cm['fn']:,}<br>{cm['fn'] / total:.0%}",
                    f"TP {cm['tp']:,}<br>{cm['tp'] / total:.0%}"]]
            cfig = go.Figure(go.Heatmap(
                z=z, x=["Predicted OK", "Predicted empty-risk"],
                y=["Actually OK", "Actually empty-risk"],
                colorscale=[[i / (len(SEQ) - 1), c]
                            for i, c in enumerate(SEQ)],
                showscale=False, text=txt, texttemplate="%{text}",
                textfont=dict(color=INK, size=13),
                hovertemplate="%{y} / %{x}: %{z:,}<extra></extra>"))
            cfig.update_yaxes(autorange="reversed")
            st.plotly_chart(style(cfig, height=300), use_container_width=True)

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Precision", f"{er['precision']:.0%}", border=True,
                      help="When an alert fires, how often the station really "
                           "was empty-risk.")
            k2.metric("Recall", f"{er['recall']:.0%}", border=True,
                      help="Share of truly empty station-hours the alert caught.")
            k3.metric("F1", f"{er['f1']:.2f}", border=True)
            k4.metric("Base rate", f"{er['positive_rate_actual']:.0%}",
                      border=True,
                      help="Share of June station-hours that actually ran empty.")

    tcol, fcol = st.columns([1, 1.15])
    with tcol:
        with st.container(border=True):
            section("Alert workload vs threshold",
                    "Operations lever: a lower threshold means fewer, "
                    "higher-confidence alerts; a higher one catches more "
                    "outages at the cost of crew time.")
            rows = []
            for t in range(0, 7):
                rows.append({"threshold": t,
                             "alerts": int((snap["pred_bikes"] <= t).sum())})
            tdf = pd.DataFrame(rows)
            tfig = go.Figure(go.Scatter(
                x=tdf["threshold"], y=tdf["alerts"], mode="lines+markers",
                line=dict(color=S1, width=2), marker=dict(size=8),
                hovertemplate="≤ %{x} bikes → %{y} alerts<extra></extra>"))
            tfig.add_vline(x=thr, line_dash="dot", line_color=SERIOUS,
                           annotation_text="current",
                           annotation_font_color=SERIOUS)
            tfig.update_xaxes(dtick=1, title="Alert threshold (bikes)")
            tfig.update_yaxes(title=f"Stations flagged ({dow_name} {hour:02d}:00)")
            st.plotly_chart(style(tfig, height=300), use_container_width=True)
    with fcol:
        with st.container(border=True):
            section("Static report figures", "As submitted with the paper")
            with st.expander("📄 Show figures", expanded=False):
                figs = sorted(FIGS.glob("*.png"))
                for i in range(0, len(figs), 2):
                    cols = st.columns(2)
                    for col, f in zip(cols, figs[i:i + 2]):
                        col.image(str(f), caption=f.stem.replace("_", " "),
                                  use_container_width=True)
