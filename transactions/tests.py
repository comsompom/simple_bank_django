from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import AccountStatus
from transactions.models import TransferStatus
from transactions.services import calculate_transfer_fee
from users.services import create_user_with_account


class TransferApiTests(APITestCase):
    def setUp(self):
        self.sender = create_user_with_account(
            email="sender@example.com",
            password="Passw0rd!234",
            full_name="Sender User",
        )
        self.receiver = create_user_with_account(
            email="receiver@example.com",
            password="Passw0rd!234",
            full_name="Receiver User",
        )
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "sender@example.com", "password": "Passw0rd!234"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

    def test_calculate_transfer_fee_uses_minimum(self):
        self.assertEqual(calculate_transfer_fee(Decimal("100.00")), Decimal("5.00"))

    def test_calculate_transfer_fee_uses_percentage(self):
        self.assertEqual(calculate_transfer_fee(Decimal("1000.00")), Decimal("25.00"))

    def test_transfer_request_reserves_funds_and_records_pending_transactions(self):
        response = self.client.post(
            "/api/v1/transfers/",
            {
                "destination_account_number": self.receiver.bank_account.account_number,
                "amount": "100.00",
                "reference": "Invoice 001",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], TransferStatus.PENDING)

        self.sender.bank_account.refresh_from_db()
        self.receiver.bank_account.refresh_from_db()
        self.assertEqual(self.sender.bank_account.balance, Decimal("10000.00"))
        self.assertEqual(self.sender.bank_account.reserved_balance, Decimal("105.00"))
        self.assertEqual(self.sender.bank_account.available_balance, Decimal("9895.00"))
        self.assertEqual(self.receiver.bank_account.balance, Decimal("10000.00"))
        self.assertEqual(self.sender.bank_account.transactions.filter(status="pending").count(), 2)
        self.assertEqual(self.receiver.bank_account.transactions.filter(status="pending").count(), 1)

    def test_balance_endpoint_returns_reserved_and_available_balances(self):
        self.client.post(
            "/api/v1/transfers/",
            {
                "destination_account_number": self.receiver.bank_account.account_number,
                "amount": "100.00",
            },
            format="json",
        )
        response = self.client.get("/api/v1/accounts/balance/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["balance"], Decimal("10000.00"))
        self.assertEqual(response.data["reserved_balance"], Decimal("105.00"))
        self.assertEqual(response.data["available_balance"], Decimal("9895.00"))

    def test_transaction_list_supports_date_filters(self):
        response = self.client.get("/api/v1/transactions/?from=2000-01-01&to=2999-01-01")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_transfer_list_returns_user_related_transfer_requests(self):
        self.client.post(
            "/api/v1/transfers/",
            {
                "destination_account_number": self.receiver.bank_account.account_number,
                "amount": "100.00",
            },
            format="json",
        )
        response = self.client.get("/api/v1/transfers/?status=pending")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_blocked_sender_cannot_transfer(self):
        self.sender.bank_account.status = AccountStatus.BLOCKED
        self.sender.bank_account.save(update_fields=["status", "updated_at"])
        response = self.client.post(
            "/api/v1/transfers/",
            {"destination_account_number": self.receiver.bank_account.account_number, "amount": "100.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_fails_with_insufficient_funds_without_changing_balances(self):
        response = self.client.post(
            "/api/v1/transfers/",
            {"destination_account_number": self.receiver.bank_account.account_number, "amount": "1000000.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.sender.bank_account.refresh_from_db()
        self.receiver.bank_account.refresh_from_db()
        self.assertEqual(self.sender.bank_account.balance, Decimal("10000.00"))
        self.assertEqual(self.sender.bank_account.reserved_balance, Decimal("0.00"))
        self.assertEqual(self.receiver.bank_account.balance, Decimal("10000.00"))
