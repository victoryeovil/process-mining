import io
import subprocess
from pathlib import Path

import pandas as pd
import joblib
from django.conf import settings
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from graphviz.backend.execute import ExecutableNotFound

from events.models import Event
from pm4py import convert
from pm4py.objects.log.util import dataframe_utils
from pm4py.algo.discovery.alpha import algorithm as alpha_miner
from pm4py.visualization.petri_net import visualizer as pn_visualizer
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay


class MetricsView(APIView):
    """1) Cycle-time metrics & bottleneck."""
    def get(self, request):
        qs = Event.objects.select_related("case").values(
            "case__case_id", "activity", "timestamp", "resource"
        )
        df = pd.DataFrame.from_records(qs).rename(
            columns={"case__case_id": "case_id"}
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Cycle-time per case
        ct = df.groupby("case_id")["timestamp"].agg(start="min", end="max")
        ct["duration"] = (ct.end - ct.start).dt.total_seconds() / 3600
        metrics = {
            "total_cases":   int(ct.shape[0]),
            "total_events":  int(df.shape[0]),
            "avg_cycle_time_hours": float(ct.duration.mean()),
            "max_cycle_time_hours": float(ct.duration.max()),
        }

        # Bottleneck
        df = df.sort_values(["case_id", "timestamp"])
        df["next_ts"] = df.groupby("case_id")["timestamp"].shift(-1)
        df["act_dur"] = (df.next_ts - df.timestamp).dt.total_seconds() / 3600
        bn = df.dropna(subset=["act_dur"]).groupby("activity").act_dur.mean()
        bottleneck = [{"activity": a, "avg_hours": float(d)} for a, d in bn.items()]

        return Response({"metrics": metrics, "bottleneck": bottleneck})


class ProcessMapView(APIView):
    """2) α-miner Petri net PNG."""
    def get(self, request):
        qs = Event.objects.select_related("case").values(
            "case__case_id", "activity", "timestamp", "resource"
        )
        df = pd.DataFrame.from_records(qs).rename(columns={
            "case__case_id": "case:concept:name",
            "activity":      "concept:name",
            "timestamp":     "time:timestamp",
            "resource":      "org:resource",
        })
        df["time:timestamp"] = pd.to_datetime(df["time:timestamp"])
        df = dataframe_utils.convert_timestamp_columns_in_df(df).sort_values("time:timestamp")

        log = convert.convert_to_event_log(df)
        try:
            net, im, fm = alpha_miner.apply(log)
            gviz       = pn_visualizer.apply(net, im, fm)
            img_bytes  = gviz.pipe(format="png")
            return HttpResponse(img_bytes, content_type="image/png")
        except ExecutableNotFound:
            return Response(
                {"error": "Graphviz ‘dot’ executable not found."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        finally:
            try: gviz.cleanup()
            except: pass


class PredictDurationView(APIView):
    """3) Predict case duration."""
    def get(self, request, case_id):
        model_fp = Path(__file__).resolve().parents[1] / "models" / "case_duration_rf.joblib"
        model    = joblib.load(model_fp)

        qs = Event.objects.filter(case__case_id=case_id)
        if not qs.exists():
            return Response({"error": "Case not found"}, status=status.HTTP_404_NOT_FOUND)

        df = pd.DataFrame.from_records(qs.values("activity","timestamp","resource"))
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        feats = [len(df), df.activity.nunique(), df.resource.nunique()]
        pred  = model.predict([feats])[0]
        return Response({"case_id": case_id, "predicted_duration_hours": float(pred)})


class PerformanceView(APIView):
    """4) Throughput & conformance (token-replay)."""
    def get(self, request):
        # Throughput
        qs = Event.objects.select_related("case").order_by("timestamp")
        dfc = (pd.DataFrame.from_records(qs.values("case__case_id","timestamp"))
                 .rename(columns={"case__case_id":"case_id"}))
        dfc["timestamp"] = pd.to_datetime(dfc.timestamp)
        starts = dfc.groupby("case_id").timestamp.min().reset_index(name="start_ts")
        starts["date"] = starts.start_ts.dt.date
        thr = starts.date.value_counts().sort_index().reset_index(name="count")
        thr.columns = ["date","count"]
        throughput = thr.to_dict(orient="records")

        # Conformance
        qs2 = Event.objects.select_related("case").values(
            "case__case_id","activity","timestamp","resource"
        )
        df = (pd.DataFrame.from_records(qs2)
              .rename(columns={
                  "case__case_id":"case:concept:name",
                  "activity":"concept:name",
                  "timestamp":"time:timestamp",
                  "resource":"org:resource"
              }))
        df["time:timestamp"] = pd.to_datetime(df["time:timestamp"])
        df = dataframe_utils.convert_timestamp_columns_in_df(df).sort_values("time:timestamp")
        log = convert.convert_to_event_log(df)

        net, im, fm = alpha_miner.apply(log)
        replayed    = token_replay.apply(log, net, im, fm)
        total_traces = len(replayed)

        if replayed and "trace_is_fitting" in replayed[0]:
            fit_tr = sum(1 for r in replayed if r["trace_is_fitting"])
            fit_rt = fit_tr / total_traces if total_traces else 0.0
        elif replayed and "trace_fitness" in replayed[0]:
            fit_tr, fit_rt = None, sum(r["trace_fitness"] for r in replayed)/total_traces
        else:
            fit_tr, fit_rt = None, None

        return Response({
            "throughput": throughput,
            "conformance": {
                "total_traces":   total_traces,
                "fitting_traces": fit_tr,
                "fitness_rate":   fit_rt
            }
        })


class ActivityFrequencyView(APIView):
    """5) Counts per activity per day."""
    def get(self, request):
        qs = Event.objects.values("activity","timestamp")
        df = pd.DataFrame.from_records(qs)
        df["timestamp"] = pd.to_datetime(df.timestamp)
        df["date"] = df.timestamp.dt.date
        freq = df.groupby(["activity","date"]).size().reset_index(name="count")
        return Response({"activity_counts": freq.to_dict(orient="records")})


# Path to your CSV (adjust if yours lives elsewhere)
CSV_PATH = Path(settings.BASE_DIR) / "data" / "event_logs" / "synthetic_events.csv"

def load_event_df():
    """
    Read the single canonical CSV and return a DataFrame
    with the same columns your SQL used to provide.
    """
    df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])
    # If your CSV has different column names, rename here:
    # df = df.rename(columns={"csv_case_id": "case_id", ...})
    return df

# adjust this to wherever your CSV actually lives
CANONICAL_CSV = Path(__file__).resolve().parents[1] / "data" / "event_logs" / "synthetic_events.csv"

class RetrainModelView(APIView):
    """
    POST /api/retrain/
    Re-trains reopen-risk model from a single CSV (admin only).
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        # 1) check script exists
        script = Path(__file__).resolve().parents[1] / "scripts" / "train_reopen_classifier.py"
        if not script.exists():
            return Response(
                {"error": f"Training script not found at {script}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 2) ensure CSV is present
        if not CANONICAL_CSV.exists():
            return Response(
                {"error": f"Event log CSV not found at {CANONICAL_CSV}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 3) call the script
        cmd = ["python", str(script), str(CANONICAL_CSV)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
        except Exception as e:
            return Response(
                {"error": f"Failed to launch training script: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 4) handle result
        if proc.returncode != 0:
            return Response(
                {"error": proc.stderr.strip() or "Unknown error during training"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {"output": proc.stdout.strip() or "Retraining succeeded"},
            status=status.HTTP_200_OK
        )