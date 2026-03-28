from rest_framework import status
from rest_framework.test import APITestCase

from transactions.models import Transfer
from users.models import UserRole
from users.services import create_user_with_account


class RoleApiTests(APITestCase):
    def setUp(self):
        self.user = create_user_with_account(
            email="user@example.com",
            password="Passw0rd!234",
            full_name="User One",
        )
        self.manager = create_user_with_account(
            email="manager@example.com",
            password="Passw0rd!234",
            full_name="Manager One",
            role=UserRole.MANAGER,
        )
        self.director = create_user_with_account(
            email="director@example.com",
            password="Passw0rd!234",
            full_name="Director One",
            role=UserRole.DIRECTOR,
        )

    def auth(self, email):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": email, "password": "Passw0rd!234"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_manager_can_block_account(self):
        self.auth("manager@example.com")
        response = self.client.post(f"/api/v1/manager/accounts/{self.user.bank_account.id}/block/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.bank_account.refresh_from_db()
        self.assertEqual(self.user.bank_account.status, "blocked")

    def test_director_can_view_overview(self):
        self.auth("director@example.com")
        response = self.client.get("/api/v1/director/reports/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["users_count"], 1)
        self.assertIn("transactions_count", response.data)
