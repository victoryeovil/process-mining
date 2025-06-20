from django.urls import path
from .views import MetricsView, ProcessMapView, PredictDurationView

urlpatterns = [
    path('metrics/',       MetricsView.as_view(),           name='api-metrics'),
    path('process-map/',   ProcessMapView.as_view(),        name='api-process-map'),
    path('predict-duration/<str:case_id>/', PredictDurationView.as_view(), name='api-predict-duration'),
]
