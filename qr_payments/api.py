from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers
from rest_framework.response import Response

from qr_payments.services import build_qr_payload, build_qr_png_base64, build_signed_qr_payload


class QRGenerateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)


@extend_schema(tags=["QR Payments"])
class QRGenerateAPIView(generics.GenericAPIView):
    serializer_class = QRGenerateSerializer
    throttle_scope = "qr_generate"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = request.user.bank_account
        payload = build_qr_payload(
            account_number=account.account_number,
            user_name=request.user.full_name,
            amount=serializer.validated_data["amount"],
            note=serializer.validated_data.get("note", ""),
        )
        signed_payload = build_signed_qr_payload(payload)
        png_base64 = build_qr_png_base64(payload)
        return Response({"payload": payload, "signed_payload": signed_payload, "png_base64": png_base64})
