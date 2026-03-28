from django.urls import path

from transactions.api import FeeEstimateAPIView, TransferListCreateAPIView

urlpatterns = [
    path("", TransferListCreateAPIView.as_view(), name="transfers-list-create"),
    path("fees/estimate/", FeeEstimateAPIView.as_view(), name="transfers-fee-estimate"),
]
