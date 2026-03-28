from django.urls import path

from transactions.api import FeeEstimateAPIView, TransferCreateAPIView

urlpatterns = [
    path("", TransferCreateAPIView.as_view(), name="transfers-create"),
    path("fees/estimate/", FeeEstimateAPIView.as_view(), name="transfers-fee-estimate"),
]
