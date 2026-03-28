from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User


class AuthFlowTests(APITestCase):
    def test_register_creates_account_and_welcome_bonus(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {"email": "alice@example.com", "full_name": "Alice Example", "password": "Passw0rd!234"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["account"]["balance"], "10000.00")
        self.assertEqual(len(response.data["account"]["account_number"]), 10)
        self.assertTrue(User.objects.filter(email="alice@example.com").exists())

    def test_login_returns_tokens(self):
        User.objects.create_user(email="login@example.com", full_name="Login User", password="Passw0rd!234")
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "login@example.com", "password": "Passw0rd!234"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
