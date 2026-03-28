import base64
from io import BytesIO

import qrcode
from rest_framework import generics, serializers
from rest_framework.response import Response


class QRGenerateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)


class QRGenerateAPIView(generics.GenericAPIView):
    serializer_class = QRGenerateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = request.user.bank_account
        payload = {
            "account_number": account.account_number,
            "user_name": request.user.full_name,
            "amount": str(serializer.validated_data["amount"]),
            "note": serializer.validated_data.get("note", ""),
        }
        qr = qrcode.make(payload)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        png_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return Response({"payload": payload, "png_base64": png_base64})
