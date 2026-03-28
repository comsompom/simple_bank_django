from django.core import signing
from rest_framework import status
from rest_framework.test import APITestCase

from users.services import create_user_with_account


class QRApiTests(APITestCase):
    def setUp(self):
        self.user = create_user_with_account(
            email="qr@example.com",
            password="Passw0rd!234",
            full_name="QR User",
        )
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {"email": self.user.email, "password": "Passw0rd!234"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

    def test_qr_generate_returns_payload_signed_payload_and_png(self):
        response = self.client.post(
            "/api/v1/qr/generate/",
            {"amount": "25.50", "note": "Lunch"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["payload"]["account_number"], self.user.bank_account.account_number)
        self.assertEqual(response.data["payload"]["note"], "Lunch")
        self.assertTrue(response.data["png_base64"])
        restored = signing.loads(response.data["signed_payload"])
        self.assertEqual(restored, response.data["payload"])

    def test_qr_generate_requires_authentication(self):
        self.client.credentials()
        response = self.client.post("/api/v1/qr/generate/", {"amount": "25.50"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
