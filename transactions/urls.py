from django.urls import path

from transactions.api import TransactionListAPIView

urlpatterns = [
    path("", TransactionListAPIView.as_view(), name="transactions-list"),
]
