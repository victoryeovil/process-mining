#!/usr/bin/env python3
import os
import joblib
import pandas as pd
from datetime import timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from dotenv import load_dotenv
from sqlalchemy import create_engine

# 0. Load env & build URI
load_dotenv()
user   = os.getenv("POSTGRES_USER")
pw     = os.getenv("POSTGRES_PASSWORD")
host   = os.getenv("DB_HOST")
port   = os.getenv("DB_PORT")
db     = os.getenv("POSTGRES_DB")
URI    = f"postgresql://{user}:{pw}@{host}:{port}/{db}"

# 1. Read raw events
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

# 2. Case-level feature engineering
# 2a) Compute start / end / duration
grouped = (
    df
    .groupby("case_id")["timestamp"]
    .agg(start="min", end="max")
    .reset_index()               # <-- ensure case_id is ONLY a column
)
# Duration in hours
grouped["duration"] = (
    (grouped["end"] - grouped["start"])
    .dt.total_seconds() / 3600
)
features = grouped[["case_id", "duration"]]

# 2b) Add count-based features
feat_counts = (
    df
    .groupby("case_id")
    .agg(
        total_events      = ("activity", "count"),
        unique_activities = ("activity", "nunique"),
        unique_resources  = ("resource", "nunique"),
    )
    .reset_index()               # <-- again, case_id as column only
)
features = features.merge(feat_counts, on="case_id")

# 3. Split & train
X = features[["total_events", "unique_activities", "unique_resources"]]
y = features["duration"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 4. Evaluate
preds = model.predict(X_test)
print("MAE (hrs):", mean_absolute_error(y_test, preds))
print("R²:", r2_score(y_test, preds))

# 5. Persist
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/case_duration_rf.joblib")
print("Model saved to models/case_duration_rf.joblib")
