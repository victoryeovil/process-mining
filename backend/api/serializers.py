from rest_framework import serializers
from events.models import Case, Event

class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = ['case_id', 'created_at', 'resolved_at', 'reopen_count', 'assignee', 'issue_type']

class EventSerializer(serializers.ModelSerializer):
    case = serializers.CharField(source='case.case_id')

    class Meta:
        model = Event
        fields = ['case', 'activity', 'timestamp', 'resource']
