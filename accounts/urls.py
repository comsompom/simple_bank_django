from django.urls import path

from accounts.api import BalanceAPIView, MeAccountAPIView

urlpatterns = [
    path("me/", MeAccountAPIView.as_view(), name="account-me"),
    path("balance/", BalanceAPIView.as_view(), name="account-balance"),
]
