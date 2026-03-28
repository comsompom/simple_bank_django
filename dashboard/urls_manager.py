from django.urls import path

from dashboard.api import (
    ManagerApproveTransferAPIView,
    ManagerBlockAccountAPIView,
    ManagerBlockTransferAPIView,
    ManagerCreateAccountAPIView,
    ManagerPendingTransferListAPIView,
    ManagerUserListAPIView,
    ManagerUserTransactionsAPIView,
)

urlpatterns = [
    path("users/", ManagerUserListAPIView.as_view(), name="manager-users"),
    path("users/<int:user_id>/transactions/", ManagerUserTransactionsAPIView.as_view(), name="manager-user-transactions"),
    path("accounts/create/", ManagerCreateAccountAPIView.as_view(), name="manager-create-account"),
    path("accounts/<int:account_id>/block/", ManagerBlockAccountAPIView.as_view(), name="manager-block-account"),
    path("transfers/pending/", ManagerPendingTransferListAPIView.as_view(), name="manager-pending-transfers"),
    path("transfers/<int:transfer_id>/approve/", ManagerApproveTransferAPIView.as_view(), name="manager-approve-transfer"),
    path("transfers/<int:transfer_id>/block/", ManagerBlockTransferAPIView.as_view(), name="manager-block-transfer"),
]
