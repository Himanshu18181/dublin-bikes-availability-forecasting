"""
data_loader.py
Load and reshape the real dublinbikes station-status feed into an hourly,
station-level table ready for demand / availability modelling.

Dataset: dublinbikes historical station status (Smart Dublin open data)
  https://data.smartdublin.ie/dataset/dublinbikes-api
Each raw file (dublin-bikes_station_status_MMYYYY.csv) holds 5-minute snapshots
for every station with columns:
  system_id, last_reported, station_id, num_bikes_available,
  num_docks_available, is_installed, is_renting, is_returning, name,
  short_name, address, lat, lon, region_id, capacity

We aggregate the 5-minute snapshots to an HOURLY mean per station and attach
calendar features. The learning task is:

    predict the average number of bikes available at a given station,
    for a given hour-of-day and day-of-week.

Everything here is human-readable (no black-box embeddings) so the model,
and the dashboard built on top of it, stays fully interpretable.
"""
from __future__ import annotations
import os
import glob
import pandas as pd

# --- Columns we actually read from the raw 5-minute files -------------------
RAW_USECOLS = [
    "last_reported", "station_id", "num_bikes_available",
    "num_docks_available", "is_renting", "name", "lat", "lon", "capacity",
]

# --- Model feature contract (shared with train_model.py and app.py) ---------
# hour and day_of_week are treated as CATEGORICAL (one-hot) so a linear model
# can learn their non-linear daily rhythm just as well as the tree models
# (fair contest). This is the exact contract the saved model in
# outputs/model/ was trained with - keep it in sync with meta.json.
CATEGORICAL_FEATURES = ["station_id", "hour", "day_of_week"]
NUMERIC_FEATURES = ["capacity"]
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET = "bikes_available"

# Human-readable buckets for the hour of day (used in EDA / the dashboard only).
PART_OF_DAY_BINS = [-1, 5, 9, 15, 19, 23]
PART_OF_DAY_LABELS = ["Night", "AM peak", "Midday", "PM peak", "Evening"]


def part_of_day(hour: pd.Series) -> pd.Series:
    """Map an integer hour to a readable part-of-day label."""
    return pd.cut(hour, bins=PART_OF_DAY_BINS, labels=PART_OF_DAY_LABELS)

# Station metadata carried through for the map / dashboard (not model inputs).
META_COLS = ["station_id", "name", "lat", "lon", "capacity"]

# Operational thresholds for the rebalancing / business layer.
EMPTY_THRESHOLD = 2   # <= this many bikes  -> a rider cannot pick up a bike
FULL_THRESHOLD = 2    # <= this many docks  -> a rider cannot return a bike


def _find_files(data_dir: str) -> list[str]:
    files = sorted(glob.glob(os.path.join(data_dir, "dublin-bikes_station_status_*.csv")))
    if not files:
        raise FileNotFoundError(
            f"No 'dublin-bikes_station_status_*.csv' files found in '{data_dir}'.\n"
            "Download one or more monthly files from Smart Dublin open data:\n"
            "  https://data.smartdublin.ie/dataset/dublinbikes-api\n"
            "and place them in the data directory (default: data/raw)."
        )
    return files


def load_raw(data_dir: str) -> pd.DataFrame:
    """Read and concatenate every monthly 5-minute snapshot file."""
    frames = []
    for path in _find_files(data_dir):
        df = pd.read_csv(path, usecols=RAW_USECOLS)
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True)
    # station_id as string -> clean one-hot categories, never treated as a number
    raw["station_id"] = raw["station_id"].astype(str)
    return raw


def to_hourly(raw: pd.DataFrame) -> pd.DataFrame:
    """Collapse 5-minute snapshots to one row per (station, date, hour)."""
    df = raw.copy()

    # Drop the rare offline snapshot(s) where the station was not renting.
    if "is_renting" in df:
        df = df[df["is_renting"] != False]  # noqa: E712  (handles bool + 'False' text)

    df["ts"] = pd.to_datetime(df["last_reported"])
    df["date"] = df["ts"].dt.normalize()
    df["hour"] = df["ts"].dt.hour

    hourly = df.groupby(["station_id", "date", "hour"], as_index=False).agg(
        bikes_available=("num_bikes_available", "mean"),
        docks_available=("num_docks_available", "mean"),
        capacity=("capacity", "median"),
        name=("name", "first"),
        lat=("lat", "median"),
        lon=("lon", "median"),
        n_obs=("num_bikes_available", "size"),
    )

    # Calendar features from the (date, hour) key.
    stamp = hourly["date"] + pd.to_timedelta(hourly["hour"], unit="h")
    hourly["day_of_week"] = stamp.dt.dayofweek          # Mon=0 .. Sun=6
    hourly["is_weekend"] = (hourly["day_of_week"] >= 5).astype(int)
    hourly["month"] = stamp.dt.month

    # Normalised occupancy (share of docks holding a bike), clipped to [0, 1].
    hourly["occupancy"] = (hourly["bikes_available"] / hourly["capacity"]).clip(0, 1)

    # hour / day_of_week kept as strings for stable one-hot categories.
    hourly["hour"] = hourly["hour"].astype(int)
    hourly["day_of_week"] = hourly["day_of_week"].astype(int)
    return hourly


def load_hourly(data_dir: str) -> pd.DataFrame:
    """Convenience: raw files -> tidy hourly modelling table."""
    return to_hourly(load_raw(data_dir))


def station_table(hourly: pd.DataFrame) -> pd.DataFrame:
    """One row per station with its coordinates and capacity (for the map)."""
    tbl = (hourly.groupby("station_id", as_index=False)
                 .agg(name=("name", "first"),
                      lat=("lat", "median"),
                      lon=("lon", "median"),
                      capacity=("capacity", "median")))
    return tbl.sort_values("station_id").reset_index(drop=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/raw")
    args = ap.parse_args()

    h = load_hourly(args.data_dir)
    print(f"Hourly rows: {len(h):,}")
    print(f"Stations   : {h['station_id'].nunique()}")
    print(f"Date range : {h['date'].min().date()} -> {h['date'].max().date()}")
    print(f"Months     : {sorted(h['month'].unique().tolist())}")
    print(f"Bikes avail: mean={h[TARGET].mean():.1f}  "
          f"median={h[TARGET].median():.1f}  max={h[TARGET].max():.1f}")
    print(f"Occupancy  : mean={h['occupancy'].mean():.2f}")
    empty = (h['bikes_available'] <= EMPTY_THRESHOLD).mean() * 100
    full = (h['docks_available'] <= FULL_THRESHOLD).mean() * 100
    print(f"Station-hours empty (<= {EMPTY_THRESHOLD} bikes): {empty:.1f}%")
    print(f"Station-hours full  (<= {FULL_THRESHOLD} docks): {full:.1f}%")
