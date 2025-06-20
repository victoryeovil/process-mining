import pandas as pd
from events.models import Event
from pm4py import convert
from pm4py.objects.log.util import dataframe_utils

def get_event_log():
    # Fetch all events into a DataFrame
    qs = (
        Event.objects
        .select_related("case")
        .values("case__case_id", "activity", "timestamp", "resource")
    )
    df = pd.DataFrame.from_records(qs)
    df = df.rename(columns={
        "case__case_id": "case:concept:name",
        "activity":      "concept:name",
        "timestamp":     "time:timestamp",
        "resource":      "org:resource",
    })

    # Ensure datetime type & chronological order
    df = dataframe_utils.convert_timestamp_columns_in_df(df)
    df = df.sort_values("time:timestamp")

    # Convert DataFrame to PM4Py EventLog
    event_log = convert.convert_to_event_log(df)
    return event_log
