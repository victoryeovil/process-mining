# backend/events/management/commands/load_events.py
import pandas as pd
from django.core.management.base import BaseCommand
from events.models import Case, Event

class Command(BaseCommand):
    help = "Load events from a CSV (with columns case_id, activity, timestamp) into the DB"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to your event log CSV")

    def handle(self, *args, **options):
        df = pd.read_csv(options["csv_path"], parse_dates=["timestamp"])
        for _, row in df.iterrows():
            case_obj, _ = Case.objects.get_or_create(case_id=row["case_id"])
            Event.objects.create(
                case=case_obj,
                activity=row["activity"],
                timestamp=row["timestamp"],
            )
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(df)} events"))
