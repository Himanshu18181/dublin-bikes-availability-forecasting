"""
train_model.py
Predict station-level bike availability for dublinbikes and turn the
predictions into an operational rebalancing signal.

Learning task (regression):
    target  = average number of bikes available at a station in a given hour
    inputs  = station_id, hour-of-day, day-of-week, station capacity

Model ladder (each a genuine alternative, so the choice is justified):
    0. Naive baseline  - historical mean bikes by (station, day-of-week, hour)
    1. LinearRegression - interpretable, one-hot calendar + station effects
    2. RandomForest     - non-linear interactions
    3. XGBoost          - regularised gradient boosting

Honest evaluation:
    * TEMPORAL split - train on April+May 2026, test on the UNSEEN June 2026.
    * Regression metrics: MAE, RMSE, R2 (bikes).
    * Business layer: convert predictions to "empty-risk" alerts
      (<= 2 bikes) and report Precision / Recall / F1 - this is what an
      operations team would actually act on.

Outputs (under <out>/):
    metrics/model_metrics.csv|json, metrics/empty_risk_report.json
    figures/*.png
    model/best_model.joblib (+ meta.json)
    dashboard/stations.csv, dashboard/actual_profiles.csv,
              dashboard/predictions_grid.csv

Run:  python src/train_model.py --data-dir data/raw --out outputs
"""
import os
import json
import argparse
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (mean_squared_error, mean_absolute_error, r2_score,
                             precision_score, recall_score, f1_score,
                             confusion_matrix)
from xgboost import XGBRegressor

from data_loader import (load_hourly, station_table, FEATURES,
                         CATEGORICAL_FEATURES, NUMERIC_FEATURES, TARGET,
                         EMPTY_THRESHOLD)

RANDOM_STATE = 42
TRAIN_MONTHS = [4, 5]   # April + May 2026
TEST_MONTHS = [6]       # June 2026 (held out)

# Consistent, professional palette shared with the dashboard.
BLUE, GREEN, RED, AMBER, SLATE = "#2563eb", "#16a34a", "#dc2626", "#f59e0b", "#334155"
DOW_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def ensure_dir(d):
    os.makedirs(d, exist_ok=True)


def build_preprocessor():
    cat = OneHotEncoder(handle_unknown="ignore")
    num = StandardScaler()
    return ColumnTransformer([("cat", cat, CATEGORICAL_FEATURES),
                              ("num", num, NUMERIC_FEATURES)])


def build_models():
    return {
        "LinearRegression": LinearRegression(),
        "RandomForest": RandomForestRegressor(
            n_estimators=200, max_depth=None, min_samples_leaf=3,
            n_jobs=-1, random_state=RANDOM_STATE),
        "XGBoost": XGBRegressor(
            n_estimators=500, learning_rate=0.05, max_depth=7,
            subsample=0.9, colsample_bytree=0.9, n_jobs=-1,
            random_state=RANDOM_STATE, tree_method="hist"),
    }


def reg_metrics(name, y_true, y_pred):
    return {
        "model": name,
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def empty_risk_report(y_true_bikes, y_pred_bikes, thr=EMPTY_THRESHOLD):
    """Treat 'station will be empty (<= thr bikes)' as the positive class."""
    yt = (np.asarray(y_true_bikes) <= thr).astype(int)
    yp = (np.asarray(y_pred_bikes) <= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(yt, yp, labels=[0, 1]).ravel()
    return {
        "threshold_bikes": thr,
        "positive_rate_actual": float(yt.mean()),
        "precision": float(precision_score(yt, yp, zero_division=0)),
        "recall": float(recall_score(yt, yp, zero_division=0)),
        "f1": float(f1_score(yt, yp, zero_division=0)),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/raw")
    ap.add_argument("--out", default="outputs")
    args = ap.parse_args()

    fig_dir = os.path.join(args.out, "figures")
    met_dir = os.path.join(args.out, "metrics")
    mod_dir = os.path.join(args.out, "model")
    dash_dir = os.path.join(args.out, "dashboard")
    for d in (fig_dir, met_dir, mod_dir, dash_dir):
        ensure_dir(d)

    # ---------------------------------------------------------------- data
    data = load_hourly(args.data_dir)
    train = data[data["month"].isin(TRAIN_MONTHS)].reset_index(drop=True)
    test = data[data["month"].isin(TEST_MONTHS)].reset_index(drop=True)
    print(f"Hourly rows: {len(data):,}  | train {len(train):,} (months {TRAIN_MONTHS})"
          f"  | test {len(test):,} (months {TEST_MONTHS})")

    X_train, y_train = train[FEATURES], train[TARGET].to_numpy()
    X_test, y_test = test[FEATURES], test[TARGET].to_numpy()

    # ------------------------------------------------- 0. naive baseline
    base_tbl = (train.groupby(["station_id", "day_of_week", "hour"])[TARGET]
                     .mean().rename("pred").reset_index())
    global_mean = float(train[TARGET].mean())
    base_pred = (test.merge(base_tbl, on=["station_id", "day_of_week", "hour"],
                            how="left")["pred"].fillna(global_mean).to_numpy())

    results = [reg_metrics("Naive baseline (station x day x hour mean)",
                           y_test, base_pred)]
    fitted = {}

    # ------------------------------------------------- 1-3. ML models
    for name, model in build_models().items():
        pipe = Pipeline([("prep", build_preprocessor()), ("model", model)])
        pipe.fit(X_train, y_train)
        pred = np.clip(pipe.predict(X_test), 0, None)
        results.append(reg_metrics(name, y_test, pred))
        fitted[name] = (pipe, pred)
        r = results[-1]
        print(f"[{name}] MAE={r['mae']:.2f}  RMSE={r['rmse']:.2f}  R2={r['r2']:.3f}")

    res_df = pd.DataFrame(results).sort_values("mae").reset_index(drop=True)
    res_df.to_csv(os.path.join(met_dir, "model_metrics.csv"), index=False)
    with open(os.path.join(met_dir, "model_metrics.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("\n=== Ranked by MAE (lower is better) ===")
    print(res_df.to_string(index=False))

    # Best among the deployable ML models (exclude the lookup baseline).
    ml_df = res_df[~res_df["model"].str.startswith("Naive")]
    best = ml_df.iloc[0]["model"]
    best_pipe, best_pred = fitted[best]
    print(f"\nBest deployable model: {best}")

    # ------------------------------------------------- business layer
    er = empty_risk_report(y_test, best_pred)
    er_base = empty_risk_report(y_test, base_pred)
    with open(os.path.join(met_dir, "empty_risk_report.json"), "w") as f:
        json.dump({"best_model": best, best: er, "naive_baseline": er_base}, f, indent=2)
    print(f"\nEmpty-risk (<= {EMPTY_THRESHOLD} bikes) | {best}: "
          f"P={er['precision']:.2f} R={er['recall']:.2f} F1={er['f1']:.2f}")

    # ================================================== FIGURES ==========
    plt.rcParams.update({"axes.grid": True, "grid.alpha": 0.25,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "font.size": 11})

    # 1. EDA heatmap: mean occupancy by hour x day-of-week
    piv = (data.pivot_table(index="hour", columns="day_of_week",
                            values="occupancy", aggfunc="mean")
               .reindex(columns=range(7)))
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(piv.values, aspect="auto", origin="lower", cmap="RdYlGn",
                   vmin=0, vmax=1)
    ax.set_xticks(range(7)); ax.set_xticklabels(DOW_NAMES)
    ax.set_yticks(range(0, 24, 2)); ax.set_yticklabels(range(0, 24, 2))
    ax.set_xlabel("Day of week"); ax.set_ylabel("Hour of day")
    ax.set_title("Average station occupancy (green = bikes available)")
    fig.colorbar(im, ax=ax, label="Occupancy (bikes / capacity)")
    fig.tight_layout(); fig.savefig(os.path.join(fig_dir, "eda_occupancy_heatmap.png"), dpi=150)
    plt.close(fig)

    # 2. Model comparison (MAE)
    fig, ax = plt.subplots(figsize=(7, 4))
    order = res_df.sort_values("mae", ascending=True)
    colors = [SLATE if m.startswith("Naive") else BLUE for m in order["model"]]
    short = [m.split(" (")[0] for m in order["model"]]
    ax.barh(short, order["mae"], color=colors)
    ax.invert_yaxis()
    ax.set_xlabel("Mean Absolute Error (bikes)  - lower is better")
    ax.set_title("Model comparison on unseen June 2026")
    for y, v in enumerate(order["mae"]):
        ax.text(v + 0.02, y, f"{v:.2f}", va="center", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(fig_dir, "model_comparison.png"), dpi=150)
    plt.close(fig)

    # 3. Predicted vs actual (best model)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(y_test, best_pred, s=5, alpha=0.15, color=BLUE)
    lim = max(y_test.max(), best_pred.max())
    ax.plot([0, lim], [0, lim], "--", color=RED, lw=1)
    ax.set_xlabel("Actual bikes available"); ax.set_ylabel("Predicted bikes available")
    ax.set_title(f"Predicted vs actual - {best} (June)")
    fig.tight_layout(); fig.savefig(os.path.join(fig_dir, "predicted_vs_actual.png"), dpi=150)
    plt.close(fig)

    # 4. One station's typical weekday profile: actual vs predicted
    #    (pick the busiest commuter station by occupancy swing)
    swing = (train.groupby("station_id")["occupancy"]
                  .agg(lambda s: s.max() - s.min())).sort_values(ascending=False)
    focus = swing.index[0]
    prof = test[(test["station_id"] == focus) & (test["day_of_week"] < 5)]
    prof_actual = prof.groupby("hour")[TARGET].mean()
    grid = pd.DataFrame({"station_id": focus, "hour": range(24),
                         "day_of_week": 2,
                         "capacity": test.loc[test.station_id == focus, "capacity"].median()})
    grid_pred = np.clip(best_pipe.predict(grid[FEATURES]), 0, None)
    fname = test.loc[test.station_id == focus, "name"].iloc[0]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(prof_actual.index, prof_actual.values, "-o", color=SLATE,
            label="Actual (June avg)", ms=4)
    ax.plot(range(24), grid_pred, "--", color=BLUE, label=f"Predicted ({best})")
    ax.set_xlabel("Hour of day"); ax.set_ylabel("Bikes available")
    ax.set_title(f"Weekday profile - {fname}")
    ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(fig_dir, "station_profile.png"), dpi=150)
    plt.close(fig)

    # 5. Grouped feature importance (sum one-hot dummies back to their feature)
    model_obj = best_pipe.named_steps["model"]
    if hasattr(model_obj, "feature_importances_"):
        names = best_pipe.named_steps["prep"].get_feature_names_out()
        imp = model_obj.feature_importances_
        groups = {}
        for n, v in zip(names, imp):
            key = ("capacity" if n.endswith("capacity")
                   else n.split("__")[1].rsplit("_", 1)[0])
            groups[key] = groups.get(key, 0.0) + float(v)
        gs = pd.Series(groups).sort_values()
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.barh(gs.index, gs.values, color=GREEN)
        ax.set_xlabel("Total importance"); ax.set_title(f"What drives availability - {best}")
        fig.tight_layout(); fig.savefig(os.path.join(fig_dir, "feature_importance.png"), dpi=150)
        plt.close(fig)

    # 6. Error by hour of day
    err = pd.DataFrame({"hour": test["hour"].to_numpy(),
                        "ae": np.abs(y_test - best_pred)})
    by_hour = err.groupby("hour")["ae"].mean()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(by_hour.index, by_hour.values, "-o", color=AMBER, ms=4)
    ax.set_xlabel("Hour of day"); ax.set_ylabel("Mean abs error (bikes)")
    ax.set_title(f"When is prediction hardest? - {best}")
    fig.tight_layout(); fig.savefig(os.path.join(fig_dir, "error_by_hour.png"), dpi=150)
    plt.close(fig)

    # ================================================== DASHBOARD DATA ===
    stations = station_table(data)
    stations.to_csv(os.path.join(dash_dir, "stations.csv"), index=False)

    # Actual "typical" availability by (station, dow, hour) over ALL data
    actual_prof = (data.groupby(["station_id", "day_of_week", "hour"], as_index=False)
                       .agg(actual_bikes=(TARGET, "mean")))
    actual_prof.to_csv(os.path.join(dash_dir, "actual_profiles.csv"), index=False)

    # Full prediction grid: every station x day-of-week x hour
    grid = (stations[["station_id", "capacity"]]
            .assign(key=1)
            .merge(pd.DataFrame({"day_of_week": np.repeat(range(7), 24),
                                 "hour": list(range(24)) * 7, "key": 1}), on="key")
            .drop(columns="key"))
    grid["pred_bikes"] = np.clip(best_pipe.predict(grid[FEATURES]), 0, None).round(2)
    grid["pred_occupancy"] = (grid["pred_bikes"] / grid["capacity"]).clip(0, 1).round(3)
    grid.to_csv(os.path.join(dash_dir, "predictions_grid.csv"), index=False)

    # ================================================== SAVE MODEL =======
    joblib.dump(best_pipe, os.path.join(mod_dir, "best_model.joblib"))
    meta = {
        "best_model": best,
        "features": FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "target": TARGET,
        "empty_threshold": EMPTY_THRESHOLD,
        "train_months": TRAIN_MONTHS,
        "test_months": TEST_MONTHS,
        "n_stations": int(data["station_id"].nunique()),
        "date_range": [str(data["date"].min().date()), str(data["date"].max().date())],
        "metrics": results,
        "empty_risk": er,
    }
    with open(os.path.join(mod_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\nSaved metrics  -> {met_dir}")
    print(f"Saved figures  -> {fig_dir}")
    print(f"Saved model    -> {mod_dir}")
    print(f"Saved dashboard-> {dash_dir}")


if __name__ == "__main__":
    main()
