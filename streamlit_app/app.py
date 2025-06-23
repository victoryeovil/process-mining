import os
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import joblib
import streamlit as st
import altair as alt
import requests
from dotenv import load_dotenv
from requests.exceptions import HTTPError

# Load environment vars
load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Process-Mining Prototype", layout="wide")

# --- Login Screen ---
if "access_token" not in st.session_state:
    st.markdown("""
        <div style="max-width:400px; margin:100px auto; padding:20px;
                    border:1px solid #ddd; border-radius:8px;">
            <h2 style="text-align:center;">🔐 Log Into Process-Mining Prototype</h2>
        </div>
    """, unsafe_allow_html=True)
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pw")
    if st.button("Login"):
        resp = requests.post(
            f"{API_URL}/api/token/",
            json={"username": username, "password": password}
        )
        if resp.status_code == 200:
            tokens = resp.json()
            st.session_state.access_token  = tokens["access"]
            st.session_state.refresh_token = tokens["refresh"]
            st.experimental_rerun()
        else:
            st.error("Login failed. Please check your credentials.")
    st.stop()

# --- Authenticated Section ---
AUTH_HEADERS = {"Authorization": f"Bearer {st.session_state.access_token}"}

def safe_get_json(url):
    try:
        r = requests.get(url, headers=AUTH_HEADERS)
        r.raise_for_status()
        return r.json()
    except HTTPError as e:
        if e.response.status_code == 401:
            st.error("🔒 Authentication required. Please log in again.")
            for k in ("access_token", "refresh_token"):
                st.session_state.pop(k, None)
            st.experimental_rerun()
        else:
            st.error(f"Error fetching data: {e}")
            st.stop()

# --- Sidebar: Logout, Retrain, Filters, Navigation ---
with st.sidebar:
    st.header("⚙️ Menu")
    if st.button("Logout"):
        for k in ("access_token","refresh_token"):
            st.session_state.pop(k, None)
        st.experimental_rerun()
    if st.button("🚀 Retrain Model"):
        with st.spinner("Retraining..."):
            r = requests.post(f"{API_URL}/api/retrain/", headers=AUTH_HEADERS)
            if r.ok:
                st.success("Retraining complete")
            else:
                st.error(f"Retrain failed: {r.text}")
    st.markdown("---")

    # Fetch throughput once for date bounds
    perf_all = safe_get_json(f"{API_URL}/api/performance/")
    df_th_all = pd.DataFrame(perf_all["throughput"])
    df_th_all["date"] = pd.to_datetime(df_th_all["date"])
    min_date = df_th_all["date"].min().date()
    max_date = df_th_all["date"].max().date()

    st.subheader("🔎 Filters")
    date_range = st.date_input(
        "Date range",
        [min_date, max_date],
        min_value=min_date, max_value=max_date
    )

    bot = safe_get_json(f"{API_URL}/api/metrics/")["bottleneck"]
    activities = [rec["activity"] for rec in bot]
    activity_sel = st.multiselect("Activities", activities, default=activities)

    st.markdown("---")
    page = st.radio("Navigate to", ["Dashboard", "Upload & Predict Risk"])

# --- Styled Header ---
st.markdown("""
    <div style="background-color:#0066CC; padding:20px; border-radius:8px;
                margin-bottom:20px;">
        <h1 style="color:white; text-align:center; margin:0;">
            ⚙️ Process-Mining Prototype
        </h1>
    </div>
""", unsafe_allow_html=True)

# --- Dashboard Page ---
def dashboard_page():
    st.header("🔍 Dashboard")

    # 1. Metrics & Bottleneck
    data = safe_get_json(f"{API_URL}/api/metrics/")
    metrics = data["metrics"]
    bottleneck_df = pd.DataFrame(data["bottleneck"])
    bottleneck_df = bottleneck_df[bottleneck_df["activity"].isin(activity_sel)]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cases", metrics["total_cases"])
    c2.metric("Events", metrics["total_events"])
    c3.metric("Avg Cycle Time (hrs)", f"{metrics['avg_cycle_time_hours']:.1f}")
    c4.metric("Max Cycle Time (hrs)", f"{metrics['max_cycle_time_hours']:.1f}")

    # Bottleneck chart
    st.subheader("⏳ Top Bottlenecks (Avg Hours)")
    chart_bot = alt.Chart(bottleneck_df.head(10)).mark_bar().encode(
        x=alt.X("activity:N", sort=None, title="Activity"),
        y=alt.Y("avg_hours:Q", title="Avg Hours"),
        tooltip=["activity","avg_hours"]
    )
    st.altair_chart(chart_bot, use_container_width=True)
    csv_bot = bottleneck_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Bottleneck CSV", csv_bot, "bottleneck.csv", "text/csv")

    # Throughput & Conformance
    st.subheader("📈 Throughput Over Time")
    df_th = df_th_all.copy()
    mask = (
        (df_th["date"].dt.date >= date_range[0]) &
        (df_th["date"].dt.date <= date_range[1])
    )
    df_th = df_th[mask]
    chart_th = alt.Chart(df_th).mark_line(point=True).encode(
        x=alt.X("date:T", title="Date"),
        y=alt.Y("count:Q", title="Throughput"),
        tooltip=["date","count"]
    )
    st.altair_chart(chart_th, use_container_width=True)
    csv_th = df_th.to_csv(index=False).encode("utf-8")
    st.download_button("Download Throughput CSV", csv_th, "throughput.csv", "text/csv")

    st.markdown("**Conformance Scores**")
    st.json(perf_all["conformance"])

    # Activity Frequency
    st.subheader("📊 Activity Frequency Over Time")
    freq = safe_get_json(f"{API_URL}/api/activity-frequency/")
    df_freq = pd.DataFrame(freq["activity_counts"])
    df_freq["date"] = pd.to_datetime(df_freq["date"])
    mask_f = (
        (df_freq["date"].dt.date >= date_range[0]) &
        (df_freq["date"].dt.date <= date_range[1])
    )
    df_freq = df_freq[mask_f & df_freq["activity"].isin(activity_sel)]
    chart_freq = alt.Chart(df_freq).mark_line().encode(
        x=alt.X("date:T", title="Date"),
        y=alt.Y("count:Q", title="Count"),
        color=alt.Color("activity:N", title="Activity"),
        tooltip=["activity","date","count"]
    )
    st.altair_chart(chart_freq, use_container_width=True)
    csv_freq = df_freq.to_csv(index=False).encode("utf-8")
    st.download_button("Download Activity Frequency CSV", csv_freq, "activity_frequency.csv", "text/csv")

    # Dynamic Process Model
    st.subheader("🔎 Dynamic Process Model")
    miner = st.selectbox("Choose Miner", ["alpha", "heuristic", "inductive"])
    if st.button("Load Process Map"):
        img = requests.get(
            f"{API_URL}/api/process-map/?miner={miner}",
            headers=AUTH_HEADERS
        ).content
        st.image(img, caption=f"{miner.title()} Miner Petri Net", use_column_width=True)

    # Predict Case Duration
    st.subheader("🤖 Predict Case Duration")
    case_id = st.text_input("Case ID (e.g. CASE_0001)")
    if st.button("Predict Duration"):
        out = safe_get_json(f"{API_URL}/api/predict-duration/{case_id}/")
        st.success(f"Predicted duration: {out['predicted_duration_hours']:.1f} hrs")

# --- Upload & Predict Risk Page ---
def upload_page():
    st.header("📤 Upload & Predict Reopen-Risk")

    # 1. Upload
    uploaded = st.file_uploader("Upload event log CSV", type="csv")
    if not uploaded:
        st.info("Awaiting CSV upload.")
        return

    # 2. Read & preprocess
    df = pd.read_csv(uploaded, parse_dates=["timestamp"])
    st.write(f"Loaded {df['case_id'].nunique()} cases and {len(df)} events.")

    # 3. Feature engineering
    feat = df.groupby("case_id").agg(
        total_events     = ("activity", "count"),
        unique_acts      = ("activity", "nunique"),
        unique_resources = ("resource", "nunique"),
    ).reset_index()

    # 4. Locate model in either backend/models or backend/backend/models
    project_root = Path(__file__).resolve().parents[1]
    candidates = [
        project_root / "backend" / "models" / "reopen_risk_rf.joblib",
        project_root / "backend" / "backend" / "models" / "reopen_risk_rf.joblib",
    ]
    model_path = next((p for p in candidates if p.exists()), None)

    st.write("🔍 Looking for model at:")
    for p in candidates:
        st.write(" •", p)

    if model_path is None:
        st.error(
            "❌ Reopen-risk model not found in any of those locations.\n"
            "Please run `scripts/train_reopen_classifier.py` to generate it."
        )
        return

    # 5. Load model
    model = joblib.load(model_path)

    # 6. Predict probabilities — guard against single-class
    X = feat[["total_events","unique_acts","unique_resources"]]
    probas = model.predict_proba(X)
    if probas.shape[1] > 1:
        feat["reopen_risk_prob"] = probas[:, 1]
    else:
        st.warning("⚠️ Model only supports a single class; assigning 0% reopen risk.")
        feat["reopen_risk_prob"] = np.zeros(len(probas))

    # 7. Show top risk cases
    top_n = st.number_input("Show top N high-risk cases", min_value=5, max_value=50, value=10)
    result = (
        feat.sort_values("reopen_risk_prob", ascending=False)
            .head(top_n)
            .assign(
                reopen_risk=lambda df: (df.reopen_risk_prob * 100)
                                       .round(1)
                                       .astype(str) + "%"
            )
    )

    st.subheader("Top High-Risk Cases")
    st.dataframe(result[["case_id","reopen_risk"]])

# --- Render selected page ---
if page == "Dashboard":
    dashboard_page()
else:
    upload_page()
