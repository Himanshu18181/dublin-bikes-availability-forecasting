"""
make_dashboard_extras.py
Precompute the small analytical CSVs consumed by the dashboard's advanced tabs.

Pure pandas aggregation of the hourly table - NO model fitting - so it is cheap
and safe to re-run any time. Outputs (under <out>/dashboard/):

  citywide_heatmap.csv  - mean occupancy / bikes by (day_of_week, hour)
  daily_series.csv      - citywide daily trend: occupancy + empty/full pressure
  station_stats.csv     - per-station reliability + commuter-role classification

Run:  python src/make_dashboard_extras.py --data-dir data/raw --out outputs
"""
import os
import argparse

import numpy as np
import pandas as pd

from data_loader import load_hourly, EMPTY_THRESHOLD, FULL_THRESHOLD

AM_PEAK = (7, 9)     # inclusive commuter morning window (weekdays)
PM_PEAK = (16, 19)   # inclusive commuter evening window (weekdays)
ROLE_MARGIN = 0.08   # min AM-vs-PM occupancy gap to call a station "commuter"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/raw")
    ap.add_argument("--out", default="outputs")
    args = ap.parse_args()
    dash = os.path.join(args.out, "dashboard")
    os.makedirs(dash, exist_ok=True)

    h = load_hourly(args.data_dir)
    print(f"hourly rows: {len(h):,}")
    h["empty"] = h["bikes_available"] <= EMPTY_THRESHOLD
    h["full"] = h["docks_available"] <= FULL_THRESHOLD

    # 1. Citywide rhythm: hour x day-of-week ------------------------------
    heat = (h.groupby(["day_of_week", "hour"], as_index=False)
              .agg(mean_occupancy=("occupancy", "mean"),
                   mean_bikes=("bikes_available", "mean"),
                   pct_hours_empty=("empty", "mean")))
    heat.to_csv(os.path.join(dash, "citywide_heatmap.csv"), index=False)

    # 2. Daily citywide series (trend + service pressure) -----------------
    daily = (h.groupby("date", as_index=False)
               .agg(mean_occupancy=("occupancy", "mean"),
                    pct_hours_empty=("empty", "mean"),
                    pct_hours_full=("full", "mean"),
                    month=("month", "first")))
    daily.to_csv(os.path.join(dash, "daily_series.csv"), index=False)

    # 3. Station personality / reliability --------------------------------
    wk = h[h["day_of_week"] < 5]
    am = (wk[wk["hour"].between(*AM_PEAK)]
          .groupby("station_id")["occupancy"].mean().rename("am_occ"))
    pm = (wk[wk["hour"].between(*PM_PEAK)]
          .groupby("station_id")["occupancy"].mean().rename("pm_occ"))

    stats = (h.groupby("station_id", as_index=False)
               .agg(name=("name", "first"),
                    lat=("lat", "median"),
                    lon=("lon", "median"),
                    capacity=("capacity", "median"),
                    mean_occupancy=("occupancy", "mean"),
                    pct_hours_empty=("empty", "mean"),
                    pct_hours_full=("full", "mean"),
                    volatility=("occupancy", "std")))
    stats = (stats.merge(am, on="station_id", how="left")
                  .merge(pm, on="station_id", how="left"))

    diff = stats["am_occ"] - stats["pm_occ"]
    stats["role"] = np.select(
        [diff >= ROLE_MARGIN, diff <= -ROLE_MARGIN],
        ["Commuter destination (fills in AM)", "Commuter origin (fills in PM)"],
        default="Balanced")
    stats.to_csv(os.path.join(dash, "station_stats.csv"), index=False)

    print("wrote citywide_heatmap.csv, daily_series.csv, station_stats.csv "
          f"-> {dash}")
    print(stats["role"].value_counts().to_string())


if __name__ == "__main__":
    main()
