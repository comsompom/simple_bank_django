import base64
import json
from io import BytesIO

import qrcode
from django.core import signing


def build_qr_payload(*, account_number, user_name, amount, note=""):
    return {
        "account_number": account_number,
        "user_name": user_name,
        "amount": str(amount),
        "note": note,
    }


def build_signed_qr_payload(payload):
    return signing.dumps(payload)


def build_qr_png_base64(payload):
    encoded_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    qr = qrcode.make(encoded_payload)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
