from django.urls import path

from qr_payments.api import QRGenerateAPIView

urlpatterns = [
    path("generate/", QRGenerateAPIView.as_view(), name="qr-generate"),
]
