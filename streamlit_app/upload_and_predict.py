import os
import pandas as pd
import joblib
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.title("📤 Upload & Predict Reopen Risk")

# 1. Upload
uploaded = st.file_uploader(
    "Upload your event log CSV",
    type="csv",
    help="Must have columns: case_id, activity, timestamp, resource"
)
if not uploaded:
    st.info("Awaiting CSV upload.")
    st.stop()

# 2. Read & preprocess
df = pd.read_csv(uploaded, parse_dates=["timestamp"])
st.write(f"Loaded {df['case_id'].nunique()} cases and {len(df)} events.")

# 3. Feature engineering (must match training)
feat = df.groupby("case_id").agg(
    total_events      = ("activity", "count"),
    unique_acts       = ("activity", "nunique"),
    unique_resources  = ("resource", "nunique"),
).reset_index()

# 4. Load model
model_path = os.path.join(
    os.path.dirname(__file__), "../backend/models/reopen_risk_rf.joblib"
)
if not os.path.exists(model_path):
    st.error("Reopen‐risk model not found. Run train_reopen_classifier.py first.")
    st.stop()
model = joblib.load(model_path)

# 5. Predict probabilities
probs = model.predict_proba(feat[["total_events","unique_acts","unique_resources"]])[:,1]
feat["reopen_risk_prob"] = probs

# 6. Show top risk cases
top_n = st.number_input("Show top N high‐risk cases", 5, 50, 10)
result = feat.sort_values("reopen_risk_prob", ascending=False).head(top_n)
st.subheader("Top High-Risk Cases")
st.dataframe(result[["case_id","reopen_risk_prob"]].assign(
    reopen_risk_prob=lambda d: (d.reopen_risk_prob*100).round(1).astype(str) + "%"
))
