#!/usr/bin/env python3
import sys
import os
import joblib
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# ----------------------------------------------------------------------
# 0) Locate your canonical CSV
# ----------------------------------------------------------------------
# script lives at backend/scripts/train_reopen_classifier.py
# so parent = backend/, then data/event_logs/synthetic_events.csv
SCRIPT_DIR = Path(__file__).resolve().parents[1]
CSV_PATH   = SCRIPT_DIR / "data" / "event_logs" / "synthetic_events.csv"

def main():
    # 1) Allow optional override via first arg, else use CSV_PATH
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = CSV_PATH

    if not csv_path.exists():
        print(f"ERROR: CSV not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    # 2) Read event log
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])

    # 3) Feature engineering at case level
    feat = df.groupby("case_id").agg(
        total_events     = ("activity", "count"),
        unique_acts      = ("activity", "nunique"),
        unique_resources = ("resource", "nunique"),
    ).reset_index()

    # 4) Derive binary label if reopen_count is in your events table,
    #    otherwise default to 0 (no reopen)
    if "reopen_count" in df.columns:
        reopen_counts = (
            df.groupby("case_id")["reopen_count"]
              .first()
              .reset_index()
        )
        feat = feat.merge(reopen_counts, on="case_id")
        feat["will_reopen"] = (feat["reopen_count"] > 0).astype(int)
    else:
        feat["will_reopen"] = 0

    X = feat[["total_events", "unique_acts", "unique_resources"]]
    y = feat["will_reopen"]

    # 5) Train/test split and fit
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # 6) Evaluate
    preds = model.predict(X_test)
    print(classification_report(y_test, preds))

    # 7) Persist model artifact under backend/models
    out_dir = SCRIPT_DIR / "backend" / "models"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "reopen_risk_rf.joblib"
    joblib.dump(model, dest)
    print(f"✅ Saved reopen-risk model to {dest}")

if __name__ == "__main__":
    main()
