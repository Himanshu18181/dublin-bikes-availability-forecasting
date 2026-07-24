# Predicting Dublin Bikes Availability for Smarter Rebalancing

A machine-learning approach to **station-level bike availability forecasting** on the
real **dublinbikes** open data feed (Smart Dublin). Classical regression models predict
how many bikes a station will hold at a given hour and weekday; the predictions are
turned into an **operational rebalancing signal** — empty-risk / full-risk alerts an
operations team could act on — all explored through a map-based Streamlit dashboard.

> NCI M.Sc. Data Analytics — *Domain Applications* CA. Report: 6 pages, IEEE template.

## Project structure

```
Domain Appliucation Project/
├── data/raw/            <- dublin-bikes_station_status_MMYYYY.csv (not committed)
├── src/
│   ├── data_loader.py   <- 5-min snapshots -> tidy hourly modelling table
│   └── train_model.py   <- naive / Linear / RandomForest / XGBoost + empty-risk layer
├── outputs/
│   ├── figures/         <- PNGs used in the report
│   ├── metrics/         <- model_metrics.csv|json, empty_risk_report.json
│   ├── model/           <- best_model.joblib + meta.json
│   └── dashboard/       <- precomputed CSVs consumed by the app
├── app.py               <- Streamlit dashboard (runs from the CSVs, instant start)
├── requirements.txt
└── README.md
```

## 1. Get the data

Smart Dublin open data — free, no account:
https://data.smartdublin.ie/dataset/dublinbikes-api
Download the monthly **station status** CSVs (April, May, June 2026 used here) and
place them in `data/raw/` as `dublin-bikes_station_status_MMYYYY.csv`.

## 2. Install

```bash
pip install -r requirements.txt
```

## 3. Run

Sanity-check the data build:

```bash
python src/data_loader.py --data-dir data/raw
```

Train + evaluate + export everything (metrics, figures, dashboard CSVs, model):

```bash
python src/train_model.py --data-dir data/raw --out outputs
```

Launch the dashboard:

```bash
streamlit run app.py
```

## Key methodology decisions (defensible in the report)

| Decision | Why |
|---|---|
| Aggregate 5-min snapshots to **hourly means** | Rebalancing is planned at hourly resolution; averaging kills sensor noise. |
| **Temporal split** — train Apr+May, test unseen June | Random splits leak the future; this is the honest deployment scenario. |
| **Naive (station × weekday × hour mean) baseline** | Any model must beat the obvious look-up table to justify itself. |
| **Linear → RandomForest → XGBoost ladder** | Interpretable baseline vs. non-linear models; justifies the final choice. |
| MAE / RMSE / R² **in bikes** | Business-readable error: "wrong by ~5 bikes on average". |
| **Empty-risk layer** (≤ 2 bikes ⇒ alert) with P/R/F1 | Converts regression into the decision an ops team actually takes. |

## Results (held-out June 2026)

| Model | MAE | RMSE | R² |
|---|---|---|---|
| RandomForest (best) | **4.96** | **6.58** | **0.556** |
| Naive baseline | 4.96 | 6.58 | 0.555 |
| XGBoost | 5.97 | 7.40 | 0.437 |
| LinearRegression | 6.59 | 8.29 | 0.293 |

Empty-risk alerts (RandomForest): **precision 0.78**, recall 0.28, F1 0.41 — when the
dashboard flags a station, it is right ~4 times out of 5, so crews are rarely sent for
nothing. The tight race with the naive baseline is itself a finding: with calendar +
station identity features, most predictable structure in availability *is* the weekly
rhythm — discussed honestly in the report.

## The standout analysis

Beyond one error number, the project shows **when and where the system fails riders**:
the occupancy heatmap exposes the commuter tide, error-by-hour shows the model is
weakest exactly at the rush peaks, and the dashboard turns predictions into ranked
refill / collect lists per (day, hour) — the actual rebalancing decision.

## Ethics note

The feed contains **no personal data** (station counts only), but availability
predictions steer physical service: systematically under-serving peripheral stations
would compound transport inequality, and empty-risk alerts tuned for precision trade
away recall (missed outages). These trade-offs are discussed in the report's Ethical
Concerns section.
