from rest_framework import generics, response

from accounts.models import BankAccount
from rest_framework import serializers


class AccountSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = BankAccount
        fields = [
            "account_number",
            "user_email",
            "full_name",
            "balance",
            "currency",
            "status",
            "swift_code",
            "created_at",
        ]


class MeAccountAPIView(generics.RetrieveAPIView):
    serializer_class = AccountSerializer

    def get_object(self):
        return self.request.user.bank_account


class BalanceAPIView(generics.GenericAPIView):
    serializer_class = AccountSerializer

    def get(self, request, *args, **kwargs):
        account = request.user.bank_account
        return response.Response(
            {
                "account_number": account.account_number,
                "balance": account.balance,
                "currency": account.currency,
                "status": account.status,
            }
        )
