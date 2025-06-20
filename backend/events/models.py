from django.db import models

class Case(models.Model):
    case_id        = models.CharField(max_length=64, unique=True)
    created_at     = models.DateTimeField(null=True, blank=True)
    resolved_at    = models.DateTimeField(null=True, blank=True)
    reopen_count   = models.IntegerField(default=0)
    assignee       = models.CharField(max_length=128, blank=True)
    issue_type     = models.CharField(max_length=32, blank=True)


    def __str__(self):
        return self.case_id

class Event(models.Model):
    """
    A single event: links to a Case, has an activity name and timestamp.
    """
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="events")
    activity = models.CharField(max_length=128)
    timestamp = models.DateTimeField()
    resource  = models.CharField(max_length=128)   # ← add this

    class Meta:
        ordering = ["timestamp"]  # ensures chronological order

    def __str__(self):
        return f"{self.case.case_id} | {self.activity} @ {self.timestamp}"
