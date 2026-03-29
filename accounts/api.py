from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, response, serializers

from accounts.currencies import AccountCurrency, convert_currency, get_currency_choices, get_currency_metadata
from accounts.models import BankAccount
from accounts.services import get_user_account, get_user_accounts


class AccountSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    available_balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    currency_name = serializers.CharField(read_only=True)
    currency_symbol = serializers.CharField(read_only=True)
    flag_file = serializers.CharField(read_only=True)

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
            "currency_name",
            "currency_symbol",
            "flag_file",
            "status",
            "swift_code",
            "created_at",
        ]


class AccountPortfolioSerializer(serializers.Serializer):
    default_currency = serializers.CharField()
    selected_currency = serializers.CharField()
    selected_account = AccountSerializer()
    accounts = AccountSerializer(many=True)


class CurrencyConversionSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    from_currency = serializers.ChoiceField(choices=AccountCurrency.choices)
    to_currency = serializers.ChoiceField(choices=AccountCurrency.choices)


@extend_schema(
    tags=["Accounts"],
    parameters=[
        OpenApiParameter(name="currency", type=str, location=OpenApiParameter.QUERY, description="Selected account currency."),
    ],
)
class MeAccountAPIView(generics.GenericAPIView):
    serializer_class = AccountPortfolioSerializer

    def get(self, request, *args, **kwargs):
        selected_account = get_user_account(user=request.user, currency=request.query_params.get("currency"))
        portfolio = {
            "default_currency": request.user.default_currency,
            "selected_currency": selected_account.currency,
            "selected_account": selected_account,
            "accounts": list(get_user_accounts(request.user)),
        }
        return response.Response(self.get_serializer(portfolio).data)


@extend_schema(
    tags=["Accounts"],
    parameters=[
        OpenApiParameter(name="currency", type=str, location=OpenApiParameter.QUERY, description="Selected account currency."),
    ],
)
class BalanceAPIView(generics.GenericAPIView):
    serializer_class = AccountSerializer

    def get(self, request, *args, **kwargs):
        account = get_user_account(user=request.user, currency=request.query_params.get("currency"))
        return response.Response(
            {
                "account_number": account.account_number,
                "balance": account.balance,
                "reserved_balance": account.reserved_balance,
                "available_balance": account.available_balance,
                "currency": account.currency,
                "currency_name": account.currency_name,
                "currency_symbol": account.currency_symbol,
                "flag_file": account.flag_file,
                "status": account.status,
            }
        )


@extend_schema(tags=["Accounts"])
class CurrencyConvertAPIView(generics.GenericAPIView):
    serializer_class = CurrencyConversionSerializer

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        from_currency = serializer.validated_data["from_currency"]
        to_currency = serializer.validated_data["to_currency"]
        converted = convert_currency(amount, from_currency, to_currency)
        return response.Response(
            {
                "amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "converted_amount": converted,
                "from_metadata": get_currency_metadata(from_currency),
                "to_metadata": get_currency_metadata(to_currency),
            }
        )
