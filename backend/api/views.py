import io
from pathlib import Path

import pandas as pd
import joblib
from django.conf import settings
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from events.models import Event
from pm4py import convert
from pm4py.objects.log.util import dataframe_utils
from pm4py.algo.discovery.alpha import algorithm as alpha_miner
from pm4py.visualization.petri_net import visualizer as pn_visualizer


def get_database_uri():
    db = settings.DATABASES["default"]
    return (
        f"postgresql://{db['USER']}:{db['PASSWORD']}"
        f"@{db['HOST']}:{db['PORT']}/{db['NAME']}"
    )


class MetricsView(APIView):
    """Return cycle-time metrics and bottleneck data."""
    def get(self, request):
        uri = get_database_uri()
        query = """
          SELECT c.case_id AS case_id, e.activity, e.timestamp, e.resource
          FROM events_event e
          JOIN events_case c ON e.case_id = c.id
        """
        df = pd.read_sql(query, uri, parse_dates=["timestamp"])
        # Cycle-time
        ct = df.groupby("case_id")["timestamp"].agg(start="min", end="max")
        ct["duration"] = (ct["end"] - ct["start"]).dt.total_seconds() / 3600
        metrics = {
            "total_cases": int(ct.shape[0]),
            "total_events": int(df.shape[0]),
            "avg_cycle_time_hours": float(ct["duration"].mean()),
            "max_cycle_time_hours": float(ct["duration"].max()),
        }
        # Bottleneck
        df = df.sort_values(["case_id", "timestamp"])
        df["next_ts"] = df.groupby("case_id")["timestamp"].shift(-1)
        df["act_dur"] = (
            df["next_ts"] - df["timestamp"]
        ).dt.total_seconds() / 3600
        bn = df.dropna(subset=["act_dur"]).groupby("activity")["act_dur"].mean()
        bottleneck = [
            {"activity": act, "avg_hours": float(dur)} for act, dur in bn.items()
        ]
        return Response({"metrics": metrics, "bottleneck": bottleneck})


class ProcessMapView(APIView):
    """Return α-miner Petri net as a PNG image."""
    def get(self, request):
        uri = get_database_uri()
        query = """
          SELECT c.case_id AS case_id, 
                 e.activity    AS activity,
                 e.timestamp   AS timestamp,
                 e.resource    AS resource
          FROM events_event e
          JOIN events_case c ON e.case_id = c.id
        """
        df = pd.read_sql(query, uri, parse_dates=["timestamp"])
        # rename for PM4Py
        df = df.rename(columns={
            "case_id":       "case:concept:name",
            "activity":      "concept:name",
            "timestamp":     "time:timestamp",
            "resource":      "org:resource",
        })
        df = dataframe_utils.convert_timestamp_columns_in_df(df)
        df = df.sort_values("time:timestamp")
        log = convert.convert_to_event_log(df)
        net, im, fm = alpha_miner.apply(log)
        gviz = pn_visualizer.apply(net, im, fm)
        img_bytes = gviz.pipe(format="png")
        return HttpResponse(img_bytes, content_type="image/png")


class PredictDurationView(APIView):
    """Predict case duration given a case_id."""
    def get(self, request, case_id):
        # Load model
        base = Path(__file__).resolve().parents[1]
        model = joblib.load(base / "models" / "case_duration_rf.joblib")
        # Fetch events
        qs = Event.objects.filter(case__case_id=case_id)
        if not qs.exists():
            return Response(
                {"error": "Case not found"}, status=status.HTTP_404_NOT_FOUND
            )
        df = pd.DataFrame.from_records(qs.values(
            "activity", "timestamp", "resource"
        ))
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        feats = [
            df.shape[0],
            df["activity"].nunique(),
            df["resource"].nunique(),
        ]
        pred = model.predict([feats])[0]
        return Response({
            "case_id": case_id,
            "predicted_duration_hours": float(pred),
        })
