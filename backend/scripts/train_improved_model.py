#!/usr/bin/env python3
import os
from pathlib import Path

import joblib
import pandas as pd
import optuna
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score
from dotenv import load_dotenv

# 0. (Optional) load .env for any other vars you might use
load_dotenv()

# 1. Load the canonical CSV
#    Adjust the relative path if your CSV lives somewhere else.
BASE = Path(__file__).resolve().parents[1]  # backend/
CSV_PATH = BASE / "data" / "event_logs" / "synthetic_events.csv"
print(f"🔍 Loading event log from {CSV_PATH}")
df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])

# 2a. Compute case‐level duration
grp = (
    df.groupby("case_id")["timestamp"]
      .agg(start="min", end="max")
      .reset_index()
)
grp["duration"] = (grp["end"] - grp["start"]).dt.total_seconds() / 3600

# 2b. Counts & label‐specific counts
counts = (
    df.groupby("case_id").agg(
        total_events      = ("activity", "count"),
        unique_activities = ("activity", "nunique"),
        unique_resources  = ("resource", "nunique"),
        reopen_count      = ("activity", lambda x: (x == "Reopen Issue").sum()),
        review_count      = ("activity", lambda x: (x == "Code Review").sum()),
    )
    .reset_index()
)

# 2c. Temporal gaps: average hours between successive events
df_sorted = df.sort_values(["case_id", "timestamp"])
df_sorted["next_ts"] = df_sorted.groupby("case_id")["timestamp"].shift(-1)
df_sorted["delta"]   = (df_sorted["next_ts"] - df_sorted["timestamp"]).dt.total_seconds() / 3600
avg_gap = (
    df_sorted.groupby("case_id")["delta"]
             .mean()
             .reset_index()
             .rename(columns={"delta": "avg_gap_hrs"})
)

# 2d. Merge all features into one DataFrame
features = (
    grp[["case_id", "duration"]]
       .merge(counts, on="case_id")
       .merge(avg_gap, on="case_id")
)
X = features.drop(columns=["case_id", "duration"])
y = features["duration"]

# 3. Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 4. Hyperparameter tuning with Optuna
def objective(trial):
    params = {
        "n_estimators":      trial.suggest_int("n_estimators", 50, 300),
        "max_depth":         trial.suggest_int("max_depth", 3, 10),
        "learning_rate":     trial.suggest_float("learning_rate", 0.01, 0.3),
        "subsample":         trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree":  trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "random_state":      42,
    }
    model = XGBRegressor(**params)
    # use 3-fold CV on the train split
    neg_mae = cross_val_score(
        model, X_train, y_train,
        cv=3, scoring="neg_mean_absolute_error"
    ).mean()
    return -neg_mae  # minimize MAE

print("🛠️  Starting Optuna tuning...")
study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=25)
best_params = study.best_params
print("✅ Best params:", best_params)

# 5. Train final model on full train set
model = XGBRegressor(**best_params)
model.fit(X_train, y_train)

# 6. Evaluate on hold-out test set
preds = model.predict(X_test)
print("📊 Test MAE (hrs):", mean_absolute_error(y_test, preds))
print("📊 Test R²:", r2_score(y_test, preds))

# 7. Persist model artifact under backend/models/
OUT_DIR = BASE / "models"
OUT_DIR.mkdir(exist_ok=True, parents=True)
out_path = OUT_DIR / "case_duration_xgb.joblib"
joblib.dump(model, out_path)
print(f"💾 Model saved to {out_path}")
