from django.contrib.auth import get_user_model
from django.db.models import Sum
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AccountStatus, BankAccount
from transactions.api import TransactionSerializer
from transactions.models import Transaction, Transfer, TransferStatus
from transactions.services import TransferError, block_pending_transfer
from users.api import ManagedUserCreateSerializer, UserSerializer
from users.permissions import IsDirector, IsManager

User = get_user_model()


class ManagerUserListAPIView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsManager]

    def get_queryset(self):
        return User.objects.filter(role="user").select_related("bank_account").order_by("email")


class ManagerUserTransactionsAPIView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsManager]

    def get_queryset(self):
        return Transaction.objects.filter(account__user_id=self.kwargs["user_id"]).select_related("account", "related_account")


class ManagerCreateAccountAPIView(generics.CreateAPIView):
    serializer_class = ManagedUserCreateSerializer
    permission_classes = [IsManager]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class ManagerBlockAccountAPIView(APIView):
    permission_classes = [IsManager]

    def post(self, request, account_id):
        account = BankAccount.objects.get(pk=account_id)
        account.status = AccountStatus.BLOCKED
        account.save(update_fields=["status", "updated_at"])
        return Response({"detail": "Account blocked successfully.", "account_number": account.account_number})


class ManagerBlockTransferAPIView(APIView):
    permission_classes = [IsManager]

    def post(self, request, transfer_id):
        transfer = Transfer.objects.get(pk=transfer_id)
        try:
            transfer = block_pending_transfer(transfer=transfer, reviewed_by=request.user)
        except TransferError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc
        return Response({"detail": "Transfer blocked successfully.", "transfer_id": transfer.id, "status": transfer.status})


class DirectorOverviewAPIView(APIView):
    permission_classes = [IsDirector]

    def get(self, request):
        total_fee_earnings = (
            Transfer.objects.filter(status=TransferStatus.COMPLETED).aggregate(total=Sum("fee_amount"))["total"]
            or 0
        )
        return Response(
            {
                "users_count": User.objects.filter(role="user").count(),
                "transactions_count": Transaction.objects.count(),
                "bank_earnings": total_fee_earnings,
                "blocked_accounts": BankAccount.objects.filter(status=AccountStatus.BLOCKED).count(),
            }
        )
