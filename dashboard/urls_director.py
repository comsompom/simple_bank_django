from django.urls import path

from dashboard.api import DirectorOverviewAPIView

urlpatterns = [
    path("reports/overview/", DirectorOverviewAPIView.as_view(), name="director-overview"),
]
