from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AccountStatus, BankAccount
from dashboard.services import get_director_overview_data
from transactions.api import TransactionSerializer, TransferSerializer
from transactions.models import Transaction, Transfer, TransferStatus
from transactions.services import TransferError, TransferStateError, approve_pending_transfer, block_pending_transfer
from users.api import ManagedUserCreateSerializer, UserSerializer
from users.permissions import IsDirector, IsManager
from users.models import User


class ManagerBlockAccountResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    account_number = serializers.CharField()


class DirectorOverviewSerializer(serializers.Serializer):
    users_count = serializers.IntegerField()
    transactions_count = serializers.IntegerField()
    bank_earnings = serializers.DecimalField(max_digits=14, decimal_places=2)
    blocked_accounts = serializers.IntegerField()
    pending_transfers = serializers.IntegerField()


@extend_schema(tags=["Manager"])
class ManagerUserListAPIView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsManager]

    def get_queryset(self):
        return User.objects.filter(role="user").prefetch_related("accounts").order_by("email")


@extend_schema(tags=["Manager"])
class ManagerUserTransactionsAPIView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsManager]
    queryset = Transaction.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Transaction.objects.none()
        return Transaction.objects.filter(account__user_id=self.kwargs["user_id"]).select_related("account", "related_account")


@extend_schema(tags=["Manager"], request=ManagedUserCreateSerializer, responses={201: UserSerializer})
class ManagerCreateAccountAPIView(generics.CreateAPIView):
    serializer_class = ManagedUserCreateSerializer
    permission_classes = [IsManager]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Manager"], responses={200: ManagerBlockAccountResponseSerializer})
class ManagerBlockAccountAPIView(APIView):
    permission_classes = [IsManager]
    serializer_class = ManagerBlockAccountResponseSerializer

    def post(self, request, account_id):
        account = get_object_or_404(BankAccount, pk=account_id)
        if account.status != AccountStatus.BLOCKED:
            account.status = AccountStatus.BLOCKED
            account.save(update_fields=["status", "updated_at"])
        return Response({"detail": "Account blocked successfully.", "account_number": account.account_number})


@extend_schema(tags=["Manager"])
class ManagerPendingTransferListAPIView(generics.ListAPIView):
    serializer_class = TransferSerializer
    permission_classes = [IsManager]

    def get_queryset(self):
        return Transfer.objects.filter(status=TransferStatus.PENDING).select_related(
            "sender_account", "receiver_account", "initiated_by", "reviewed_by"
        )


@extend_schema(tags=["Manager"], responses={200: TransferSerializer})
class ManagerApproveTransferAPIView(APIView):
    permission_classes = [IsManager]
    serializer_class = TransferSerializer

    def post(self, request, transfer_id):
        transfer = get_object_or_404(Transfer, pk=transfer_id)
        try:
            transfer = approve_pending_transfer(transfer=transfer, reviewed_by=request.user)
        except (TransferError, TransferStateError) as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(TransferSerializer(transfer).data)


@extend_schema(tags=["Manager"], responses={200: TransferSerializer})
class ManagerBlockTransferAPIView(APIView):
    permission_classes = [IsManager]
    serializer_class = TransferSerializer

    def post(self, request, transfer_id):
        transfer = get_object_or_404(Transfer, pk=transfer_id)
        try:
            transfer = block_pending_transfer(transfer=transfer, reviewed_by=request.user)
        except (TransferError, TransferStateError) as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(TransferSerializer(transfer).data)


@extend_schema(tags=["Director"], responses={200: DirectorOverviewSerializer})
class DirectorOverviewAPIView(APIView):
    permission_classes = [IsDirector]
    serializer_class = DirectorOverviewSerializer

    def get(self, request):
        return Response(get_director_overview_data())
