#!/usr/bin/env python3
import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from dotenv import load_dotenv
from sqlalchemy import create_engine

# 0. Load env & build URI
load_dotenv()
user, pw, host, port, db = (
    os.getenv("POSTGRES_USER"),
    os.getenv("POSTGRES_PASSWORD"),
    os.getenv("DB_HOST"),
    os.getenv("DB_PORT"),
    os.getenv("POSTGRES_DB"),
)
URI = f"postgresql://{user}:{pw}@{host}:{port}/{db}"

# 1. Pull raw events + case metadata
engine = create_engine(URI)
# Assumes your Case model has a `reopen_count` field
cases = pd.read_sql("SELECT case_id, reopen_count FROM events_case", engine)
events = pd.read_sql("""
    SELECT c.case_id, e.activity, e.timestamp, e.resource
    FROM events_event e
    JOIN events_case c ON e.case_id = c.id
""", engine, parse_dates=["timestamp"])

# 2. Build features at case level
# 2a) counts & uniques
feat = events.groupby("case_id").agg(
    total_events      = ("activity", "count"),
    unique_acts       = ("activity", "nunique"),
    unique_resources  = ("resource", "nunique"),
).reset_index()

# 2b) merge with reopen labels (binary)
feat = feat.merge(cases[["case_id","reopen_count"]], on="case_id")
feat["will_reopen"] = (feat["reopen_count"] > 0).astype(int)
X = feat[["total_events","unique_acts","unique_resources"]]
y = feat["will_reopen"]

# 3. Train/test split & model
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 4. Evaluate
preds = model.predict(X_test)
print(classification_report(y_test, preds))

# 5. Persist
os.makedirs("backend/models", exist_ok=True)
joblib.dump(model, "backend/models/reopen_risk_rf.joblib")
print("Saved reopen‐risk model to backend/models/reopen_risk_rf.joblib")
