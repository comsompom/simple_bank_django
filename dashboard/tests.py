from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from transactions.models import TransferStatus
from users.models import UserRole
from users.services import create_user_with_account


class RoleApiTests(APITestCase):
    def setUp(self):
        self.user = create_user_with_account(
            email="user@example.com",
            password="Passw0rd!234",
            full_name="User One",
        )
        self.receiver = create_user_with_account(
            email="receiver@example.com",
            password="Passw0rd!234",
            full_name="Receiver User",
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

    def create_pending_transfer_as_user(self):
        self.auth("user@example.com")
        response = self.client.post(
            "/api/v1/transfers/",
            {"destination_account_number": self.receiver.bank_account.account_number, "amount": "100.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        transfer_id = response.data["id"]
        self.client.credentials()
        return transfer_id

    def test_manager_can_block_account(self):
        self.auth("manager@example.com")
        response = self.client.post(f"/api/v1/manager/accounts/{self.user.bank_account.id}/block/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.bank_account.refresh_from_db()
        self.assertEqual(self.user.bank_account.status, "blocked")

    def test_manager_can_list_and_approve_pending_transfer(self):
        transfer_id = self.create_pending_transfer_as_user()
        self.auth("manager@example.com")
        list_response = self.client.get("/api/v1/manager/transfers/pending/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)

        response = self.client.post(f"/api/v1/manager/transfers/{transfer_id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], TransferStatus.COMPLETED)
        self.user.bank_account.refresh_from_db()
        self.receiver.bank_account.refresh_from_db()
        self.assertEqual(self.user.bank_account.balance, Decimal("9895.00"))
        self.assertEqual(self.user.bank_account.reserved_balance, Decimal("0.00"))
        self.assertEqual(self.receiver.bank_account.balance, Decimal("10100.00"))

    def test_manager_can_block_pending_transfer_and_release_reserved_funds(self):
        transfer_id = self.create_pending_transfer_as_user()
        self.auth("manager@example.com")
        response = self.client.post(f"/api/v1/manager/transfers/{transfer_id}/block/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], TransferStatus.BLOCKED)
        self.user.bank_account.refresh_from_db()
        self.receiver.bank_account.refresh_from_db()
        self.assertEqual(self.user.bank_account.balance, Decimal("10000.00"))
        self.assertEqual(self.user.bank_account.reserved_balance, Decimal("0.00"))
        self.assertEqual(self.receiver.bank_account.balance, Decimal("10000.00"))

    def test_director_can_view_overview(self):
        self.auth("director@example.com")
        response = self.client.get("/api/v1/director/reports/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["users_count"], 2)
        self.assertIn("transactions_count", response.data)
        self.assertIn("pending_transfers", response.data)

    def test_openapi_schema_is_available(self):
        self.client.credentials()
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
