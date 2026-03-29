from django.urls import path

from accounts.api import BalanceAPIView, CurrencyConvertAPIView, MeAccountAPIView

urlpatterns = [
    path("me/", MeAccountAPIView.as_view(), name="account-me"),
    path("balance/", BalanceAPIView.as_view(), name="account-balance"),
    path("convert/", CurrencyConvertAPIView.as_view(), name="account-convert"),
]
