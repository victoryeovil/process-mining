import os
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd
import altair as alt
import requests
from dotenv import load_dotenv

# Load .env
load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Process-Mining Dashboard", layout="wide")
st.title("🔍 Process-Mining Prototype via API")

# 1. Fetch metrics & bottleneck from API
@st.cache_data(ttl=300)
def fetch_metrics():
    resp = requests.get(f"{API_URL}/api/metrics/")
    resp.raise_for_status()
    data = resp.json()
    return data["metrics"], pd.DataFrame(data["bottleneck"])

metrics, bottleneck_df = fetch_metrics()

# Display top‐line metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Cases", metrics["total_cases"])
c2.metric("Events", metrics["total_events"])
c3.metric("Avg Cycle Time (hrs)", f"{metrics['avg_cycle_time_hours']:.1f}")
c4.metric("Max Cycle Time (hrs)", f"{metrics['max_cycle_time_hours']:.1f}")

# Bottleneck chart
st.subheader("⏳ Top Bottlenecks (Avg Hours)")
# bottleneck_df has columns ["activity","avg_hours"]
chart1 = alt.Chart(bottleneck_df.head(10)).mark_bar().encode(
    x=alt.X("activity:N", sort=None, title="Activity"),
    y=alt.Y("avg_hours:Q", title="Avg Hours"),
    tooltip=["activity","avg_hours"]
)
st.altair_chart(chart1, use_container_width=True)

# 2. Show throughput over time if we derive from metrics endpoint
# (optional: if you extend metrics API to include a throughput series)

# 3. Fetch & display the process map PNG
st.subheader("🔎 Process Map (α-Miner)")
if st.button("Load Process Map"):
    with st.spinner("Fetching from API…"):
        resp = requests.get(f"{API_URL}/api/process-map/")
        resp.raise_for_status()
        st.image(resp.content, caption="α-Miner Petri Net", use_column_width=True)

# 4. ML prediction
st.subheader("🤖 Predict Case Duration")
case_id = st.text_input("Enter Case ID (e.g. CASE_0001)")
if st.button("Predict"):
    if not case_id:
        st.error("Please enter a Case ID.")
    else:
        resp = requests.get(f"{API_URL}/api/predict-duration/{case_id}/")
        if resp.status_code == 200:
            result = resp.json()
            st.success(f"Predicted duration: {result['predicted_duration_hours']:.1f} hrs")
        else:
            # show API-returned error message
            msg = resp.json().get("error", resp.text)
            st.error(f"Error: {msg}")
