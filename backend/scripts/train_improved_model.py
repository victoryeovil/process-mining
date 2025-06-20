#!/usr/bin/env python3
import os
import joblib
import pandas as pd
import optuna
from datetime import timedelta
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score
from dotenv import load_dotenv
from sqlalchemy import create_engine

# 0. Load environment and build URI
load_dotenv()
user, pw, host, port, db = (
    os.getenv("POSTGRES_USER"),
    os.getenv("POSTGRES_PASSWORD"),
    os.getenv("DB_HOST"),
    os.getenv("DB_PORT"),
    os.getenv("POSTGRES_DB"),
)
URI = f"postgresql://{user}:{pw}@{host}:{port}/{db}"

# 1. Read raw events into DataFrame
engine = create_engine(URI)
query = """
    SELECT 
        c.case_id    AS case_id,
        e.activity   AS activity,
        e.timestamp  AS timestamp,
        e.resource   AS resource
    FROM events_event e
    JOIN events_case c ON e.case_id = c.id
"""
df = pd.read_sql(query, engine, parse_dates=["timestamp"])

# 2. Feature engineering at case-level
# 2a) Base durations
grp = df.groupby("case_id")["timestamp"].agg(start="min", end="max").reset_index()
grp["duration"] = (grp["end"] - grp["start"]).dt.total_seconds() / 3600

# 2b) Counts
counts = df.groupby("case_id").agg(
    total_events      = ("activity", "count"),
    unique_activities = ("activity", "nunique"),
    unique_resources  = ("resource", "nunique"),
    reopen_count      = ("activity", lambda x: (x=="Reopen Issue").sum()),
    review_count      = ("activity", lambda x: (x=="Code Review").sum()),
).reset_index()

# 2c) Temporal features
#    average time between events per case
df_sorted = df.sort_values(["case_id","timestamp"])
df_sorted["next_ts"] = df_sorted.groupby("case_id")["timestamp"].shift(-1)
df_sorted["delta"] = (df_sorted["next_ts"] - df_sorted["timestamp"]).dt.total_seconds()/3600
avg_delta = df_sorted.groupby("case_id")["delta"].mean().reset_index().rename(columns={"delta":"avg_gap_hrs"})

# Merge all features
features = (
    grp[["case_id","duration"]]
    .merge(counts, on="case_id")
    .merge(avg_delta, on="case_id")
)
X = features.drop(columns=["case_id","duration"])
y = features["duration"]

# 3. Train/Test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 4. Hyperparameter tuning with Optuna
def objective(trial):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 50, 300),
        "max_depth":    trial.suggest_int("max_depth", 3, 10),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
        "subsample":    trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "random_state": 42,
    }
    model = XGBRegressor(**params)
    # 3-fold CV MAE
    mae = -cross_val_score(model, X_train, y_train,
                           cv=3,
                           scoring="neg_mean_absolute_error").mean()
    return mae

study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=25)
best_params = study.best_params
print("Best params:", best_params)

# 5. Train final model
model = XGBRegressor(**best_params)
model.fit(X_train, y_train)

# 6. Evaluate
preds = model.predict(X_test)
print("Test MAE (hrs):", mean_absolute_error(y_test, preds))
print("Test R²:", r2_score(y_test, preds))

# 7. Persist model
os.makedirs("backend/models", exist_ok=True)
joblib.dump(model, "backend/models/case_duration_xgb.joblib")
print("Model saved to backend/models/case_duration_xgb.joblib")
