from drf_spectacular.utils import extend_schema
from rest_framework import generics, response, serializers

from accounts.models import BankAccount


class AccountSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    available_balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = BankAccount
        fields = [
            "account_number",
            "user_email",
            "full_name",
            "balance",
            "reserved_balance",
            "available_balance",
            "currency",
            "status",
            "swift_code",
            "created_at",
        ]


@extend_schema(tags=["Accounts"])
class MeAccountAPIView(generics.RetrieveAPIView):
    serializer_class = AccountSerializer

    def get_object(self):
        return self.request.user.bank_account


@extend_schema(tags=["Accounts"])
class BalanceAPIView(generics.GenericAPIView):
    serializer_class = AccountSerializer

    def get(self, request, *args, **kwargs):
        account = request.user.bank_account
        return response.Response(
            {
                "account_number": account.account_number,
                "balance": account.balance,
                "reserved_balance": account.reserved_balance,
                "available_balance": account.available_balance,
                "currency": account.currency,
                "status": account.status,
            }
        )
