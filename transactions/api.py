from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import generics, serializers
from rest_framework.response import Response

from accounts.models import BankAccount
from transactions.models import Transaction, Transfer
from transactions.services import TransferError, calculate_transfer_fee, perform_transfer


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
        ]


class TransferSerializer(serializers.ModelSerializer):
    sender_account_number = serializers.CharField(source="sender_account.account_number", read_only=True)
    receiver_account_number = serializers.CharField(source="receiver_account.account_number", read_only=True)

    class Meta:
        model = Transfer
        fields = [
            "id",
            "sender_account_number",
            "receiver_account_number",
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
            return perform_transfer(
                sender_account=sender_account,
                receiver_account=receiver_account,
                amount=validated_data["amount"],
                initiated_by=self.context["request"].user,
                swift_code=validated_data.get("swift_code", ""),
                reference=validated_data.get("reference", ""),
            )
        except TransferError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc


class TransactionListAPIView(generics.ListAPIView):
    serializer_class = TransactionSerializer

    def get_queryset(self):
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


class TransferCreateAPIView(generics.CreateAPIView):
    serializer_class = TransferCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transfer = serializer.save()
        output = TransferSerializer(transfer)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=201, headers=headers)


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
