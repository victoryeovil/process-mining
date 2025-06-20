#!/usr/bin/env python3
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# PARAMETERS
NUM_CASES       = 500     # number of distinct cases
MIN_EVENTS      = 20      # min events per case
MAX_EVENTS      = 80      # max events per case
START_DATE      = datetime(2024, 1, 1)
END_DATE        = datetime(2025, 6, 1)
ACTIVITIES      = [
    "Create Issue", "Assign Issue", "Start Work",
    "Commit Code", "Code Review", "Resolve Issue",
    "Reopen Issue", "Close Issue"
]
RESOURCES       = [f"user_{i:03d}" for i in range(1, 51)]
OUTPUT_CSV_PATH = Path("data/event_logs/synthetic_events.csv")

def random_timestamp(start, end):
    """Return a random datetime between start and end."""
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))

def main():
    # ensure output dir exists
    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_CSV_PATH.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "activity", "timestamp", "resource"])

        for case_num in range(1, NUM_CASES + 1):
            case_id = f"CASE_{case_num:04d}"
            # pick a start time for the case
            case_start = random_timestamp(START_DATE, END_DATE - timedelta(days=30))
            n_events = random.randint(MIN_EVENTS, MAX_EVENTS)

            # generate events in chronological order
            timestamps = sorted(
                random_timestamp(case_start, case_start + timedelta(days=30))
                for _ in range(n_events)
            )

            for ts in timestamps:
                activity = random.choice(ACTIVITIES)
                resource = random.choice(RESOURCES)
                writer.writerow([case_id, activity, ts.isoformat(), resource])

    print(f"Synthetic log written to {OUTPUT_CSV_PATH}")

if __name__ == "__main__":
    main()

