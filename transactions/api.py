from django.db.models import Q
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics, serializers
from rest_framework.response import Response

from accounts.models import BankAccount
from transactions.models import Transaction, Transfer
from transactions.services import TransferError, calculate_transfer_fee, create_transfer_request


class TransactionSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(source="account.account_number", read_only=True)
    related_account_number = serializers.CharField(source="related_account.account_number", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "account_number",
            "related_account_number",
            "type",
            "status",
            "amount",
            "fee_amount",
            "reference",
            "description",
            "created_at",
            "processed_at",
        ]


class TransferSerializer(serializers.ModelSerializer):
    sender_account_number = serializers.CharField(source="sender_account.account_number", read_only=True)
    receiver_account_number = serializers.CharField(source="receiver_account.account_number", read_only=True)
    initiated_by_email = serializers.EmailField(source="initiated_by.email", read_only=True)
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True)

    class Meta:
        model = Transfer
        fields = [
            "id",
            "sender_account_number",
            "receiver_account_number",
            "initiated_by_email",
            "reviewed_by_email",
            "amount",
            "fee_amount",
            "total_amount",
            "swift_code",
            "reference",
            "status",
            "created_at",
            "processed_at",
        ]


class TransferCreateSerializer(serializers.Serializer):
    destination_account_number = serializers.CharField(max_length=10)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    swift_code = serializers.CharField(max_length=11, required=False, allow_blank=True)
    reference = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_destination_account_number(self, value):
        if not BankAccount.objects.filter(account_number=value).exists():
            raise serializers.ValidationError("Destination account does not exist.")
        return value

    def create(self, validated_data):
        sender_account = self.context["request"].user.bank_account
        receiver_account = BankAccount.objects.get(account_number=validated_data["destination_account_number"])
        try:
            return create_transfer_request(
                sender_account=sender_account,
                receiver_account=receiver_account,
                amount=validated_data["amount"],
                initiated_by=self.context["request"].user,
                swift_code=validated_data.get("swift_code", ""),
                reference=validated_data.get("reference", ""),
            )
        except TransferError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc


@extend_schema_view(
    get=extend_schema(
        tags=["Transactions"],
        parameters=[
            OpenApiParameter(name="from", type=str, location=OpenApiParameter.QUERY, description="Start date YYYY-MM-DD"),
            OpenApiParameter(name="to", type=str, location=OpenApiParameter.QUERY, description="End date YYYY-MM-DD"),
            OpenApiParameter(name="type", type=str, location=OpenApiParameter.QUERY, description="Transaction type filter"),
            OpenApiParameter(name="status", type=str, location=OpenApiParameter.QUERY, description="Transaction status filter"),
        ],
    )
)
class TransactionListAPIView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Transaction.objects.none()
        queryset = Transaction.objects.filter(account=self.request.user.bank_account)
        from_date = parse_date(self.request.query_params.get("from", ""))
        to_date = parse_date(self.request.query_params.get("to", ""))
        tx_type = self.request.query_params.get("type")
        status = self.request.query_params.get("status")
        if from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)
        if tx_type:
            queryset = queryset.filter(type=tx_type)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.select_related("account", "related_account")


@extend_schema_view(
    get=extend_schema(
        tags=["Transfers"],
        parameters=[
            OpenApiParameter(name="status", type=str, location=OpenApiParameter.QUERY, description="Transfer status filter"),
        ],
    ),
    post=extend_schema(tags=["Transfers"], request=TransferCreateSerializer, responses={201: TransferSerializer}),
)
class TransferListCreateAPIView(generics.ListCreateAPIView):
    queryset = Transfer.objects.none()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TransferCreateSerializer
        return TransferSerializer

    def get_queryset(self):
        queryset = Transfer.objects.filter(
            Q(sender_account=self.request.user.bank_account) | Q(receiver_account=self.request.user.bank_account)
        ).select_related("sender_account", "receiver_account", "initiated_by", "reviewed_by")
        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transfer = serializer.save()
        output = TransferSerializer(transfer)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=201, headers=headers)


@extend_schema(tags=["Transfers"])
class FeeEstimateAPIView(generics.GenericAPIView):
    class InputSerializer(serializers.Serializer):
        amount = serializers.DecimalField(max_digits=14, decimal_places=2)

    serializer_class = InputSerializer

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        fee = calculate_transfer_fee(amount)
        return Response({"amount": amount, "fee": fee, "total_debit": amount + fee})
