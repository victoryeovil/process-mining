import os
import streamlit as st
import pandas as pd
import altair as alt
import requests
import joblib
from dotenv import load_dotenv

# Load environment vars
load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Process-Mining Prototype", layout="wide")

# --- Styled Header ---
st.markdown(
    """
    <div style="background-color:#0066CC; padding:20px; border-radius:8px; margin-bottom:20px;">
        <h1 style="color:white; text-align:center; margin:0;">
            ⚙️ Process-Mining Prototype
        </h1>
        <p style="color:white; text-align:center; margin:5px 0 0;">
            Unified Dashboard & Reopen-Risk Predictor
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Page selector ---
page = st.sidebar.radio("Navigate to", ["Dashboard", "Upload & Predict Risk"])

# --- Dashboard Page ---
def dashboard_page():
    st.header("🔍 Dashboard")

    # 1. Fetch metrics & bottleneck
    @st.cache_data(ttl=300)
    def get_metrics():
        r = requests.get(f"{API_URL}/api/metrics/")
        r.raise_for_status()
        js = r.json()
        return js["metrics"], pd.DataFrame(js["bottleneck"])
    metrics, bottleneck_df = get_metrics()

    # Top-line metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cases",                 metrics["total_cases"])
    c2.metric("Events",                metrics["total_events"])
    c3.metric("Avg Cycle Time (hrs)",  f"{metrics['avg_cycle_time_hours']:.1f}")
    c4.metric("Max Cycle Time (hrs)",  f"{metrics['max_cycle_time_hours']:.1f}")

    # Bottleneck chart
    st.subheader("⏳ Top Bottlenecks (Avg Hours)")
    chart_bot = (
        alt.Chart(bottleneck_df.head(10))
           .mark_bar()
           .encode(
               x=alt.X("activity:N", sort=None, title="Activity"),
               y=alt.Y("avg_hours:Q", title="Avg Hours"),
               tooltip=["activity","avg_hours"]
           )
    )
    st.altair_chart(chart_bot, use_container_width=True)

    # 2. Throughput & Conformance
    st.subheader("📈 Throughput & Conformance Over Time")
    @st.cache_data(ttl=300)
    def get_performance():
        r = requests.get(f"{API_URL}/api/performance/")
        r.raise_for_status()
        return r.json()
    perf = get_performance()

    # Throughput line chart
    df_th = pd.DataFrame(perf["throughput"])
    df_th["date"] = pd.to_datetime(df_th["date"])
    chart_th = (
        alt.Chart(df_th)
           .mark_line(point=True)
           .encode(
               x=alt.X("date:T", title="Date"),
               y=alt.Y("count:Q", title="Throughput"),
               tooltip=["date","count"]
           )
    )
    st.altair_chart(chart_th, use_container_width=True)

    # Conformance scores
    st.markdown("**Conformance Scores**")
    st.json(perf.get("conformance", {}))

    # 3. Activity Frequency
    st.subheader("📊 Activity Frequency Over Time")
    @st.cache_data(ttl=300)
    def get_activity_freq():
        r = requests.get(f"{API_URL}/api/activity-frequency/")
        r.raise_for_status()
        return r.json()
    freq = get_activity_freq()

    df_freq = pd.DataFrame(freq["activity_counts"])
    df_freq["date"] = pd.to_datetime(df_freq["date"])
    chart_freq = (
        alt.Chart(df_freq)
           .mark_line()
           .encode(
               x=alt.X("date:T", title="Date"),
               y=alt.Y("count:Q", title="Count"),
               color=alt.Color("activity:N", title="Activity"),
               tooltip=["activity","date","count"]
           )
    )
    st.altair_chart(chart_freq, use_container_width=True)

    # 4. Dynamic Process Model
    st.subheader("🔎 Dynamic Process Model")
    miner = st.selectbox("Choose Miner", ["alpha", "heuristic", "inductive"])
    if st.button("Load Process Map"):
        with st.spinner("Fetching model…"):
            r = requests.get(f"{API_URL}/api/process-map/?miner={miner}")
            r.raise_for_status()
            st.image(r.content, caption=f"{miner.title()} Miner Petri Net", use_column_width=True)

    # 5. ML: Predict Case Duration
    st.subheader("🤖 Predict Case Duration")
    case_id = st.text_input("Case ID (e.g. CASE_0001)")
    if st.button("Predict Duration"):
        if not case_id:
            st.error("Please enter a Case ID.")
        else:
            r = requests.get(f"{API_URL}/api/predict-duration/{case_id}/")
            if r.status_code == 200:
                out = r.json()
                st.success(f"Predicted duration: {out['predicted_duration_hours']:.1f} hrs")
            else:
                err = r.json().get("error", r.text)
                st.error(f"Error: {err}")

# --- Upload & Predict Risk Page ---
def upload_page():
    st.header("📤 Upload & Predict Reopen-Risk")
    uploaded = st.file_uploader(
        "Upload event log CSV",
        type="csv",
        help="Columns: case_id, activity, timestamp, resource"
    )
    if not uploaded:
        st.info("Awaiting CSV upload.")
        return

    df = pd.read_csv(uploaded, parse_dates=["timestamp"])
    st.write(f"Loaded {df['case_id'].nunique()} cases and {len(df)} events.")

    feat = df.groupby("case_id").agg(
        total_events     = ("activity", "count"),
        unique_acts      = ("activity", "nunique"),
        unique_resources = ("resource", "nunique"),
    ).reset_index()

    model_path = os.path.join(
        os.path.dirname(__file__),
        "../backend/models/reopen_risk_rf.joblib"
    )
    if not os.path.exists(model_path):
        st.error("Reopen-risk model not found. Run training script first.")
        return
    model = joblib.load(model_path)

    feat["reopen_risk_prob"] = model.predict_proba(
        feat[["total_events","unique_acts","unique_resources"]]
    )[:,1]

    top_n = st.number_input("Show top N high-risk cases", 5, 50, 10)
    result = (
        feat.sort_values("reopen_risk_prob", ascending=False)
            .head(top_n)
            .assign(
                reopen_risk_prob=lambda d: (d.reopen_risk_prob * 100)
                    .round(1)
                    .astype(str) + "%"
            )
    )
    st.subheader("Top High-Risk Cases")
    st.dataframe(result[["case_id","reopen_risk_prob"]])

# --- Render selected page ---
if page == "Dashboard":
    dashboard_page()
else:
    upload_page()
