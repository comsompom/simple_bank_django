from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers
from rest_framework.response import Response

from accounts.services import get_user_account
from qr_payments.services import build_qr_payload, build_qr_png_base64, build_signed_qr_payload


class QRGenerateSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=10, required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_account_number(self, value):
        cleaned = value.strip()
        if not cleaned:
            return ""
        if not self.context["request"].user.accounts.filter(account_number=cleaned).exists():
            raise serializers.ValidationError("Selected account was not found.")
        return cleaned


@extend_schema(tags=["QR Payments"])
class QRGenerateAPIView(generics.GenericAPIView):
    serializer_class = QRGenerateSerializer
    throttle_scope = "qr_generate"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = get_user_account(user=request.user, account_number=serializer.validated_data.get("account_number") or None)
        payload = build_qr_payload(
            account_number=account.account_number,
            user_name=request.user.full_name,
            amount=serializer.validated_data["amount"],
            note=serializer.validated_data.get("note", ""),
        )
        signed_payload = build_signed_qr_payload(payload)
        png_base64 = build_qr_png_base64(payload)
        return Response({"payload": payload, "signed_payload": signed_payload, "png_base64": png_base64})
