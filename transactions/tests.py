from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.currencies import AccountCurrency
from accounts.models import AccountStatus
from transactions.models import TransactionStatus, TransferStatus
from transactions.services import (
    IdempotencyConflictError,
    TransferError,
    TransferStateError,
    approve_pending_transfer,
    block_pending_transfer,
    calculate_transfer_fee,
    create_transfer_request,
)
from users.models import UserRole
from users.services import create_user_with_account


class TransferServiceUnitTests(TestCase):
    def setUp(self):
        self.sender = create_user_with_account(
            email="unit-sender@example.com",
            password="Passw0rd!234",
            full_name="Unit Sender",
        )
        self.receiver = create_user_with_account(
            email="unit-receiver@example.com",
            password="Passw0rd!234",
            full_name="Unit Receiver",
        )
        self.manager = create_user_with_account(
            email="unit-manager@example.com",
            password="Passw0rd!234",
            full_name="Unit Manager",
            role=UserRole.MANAGER,
        )

    def test_calculate_transfer_fee_uses_minimum(self):
        self.assertEqual(calculate_transfer_fee(Decimal("100.00")), Decimal("5.00"))

    def test_calculate_transfer_fee_uses_percentage(self):
        self.assertEqual(calculate_transfer_fee(Decimal("1000.00")), Decimal("25.00"))

    def test_calculate_transfer_fee_rejects_zero_amount(self):
        with self.assertRaises(TransferError):
            calculate_transfer_fee(Decimal("0.00"))

    def test_transfer_request_is_idempotent_for_same_key_and_payload(self):
        first = create_transfer_request(
            sender_account=self.sender.bank_account,
            receiver_account=self.receiver.bank_account,
            amount="100.00",
            initiated_by=self.sender,
            idempotency_key="same-key",
        )
        second = create_transfer_request(
            sender_account=self.sender.bank_account,
            receiver_account=self.receiver.bank_account,
            amount="100.00",
            initiated_by=self.sender,
            idempotency_key="same-key",
        )

        self.assertEqual(first.id, second.id)
        self.sender.bank_account.refresh_from_db()
        self.assertEqual(self.sender.bank_account.reserved_balance, Decimal("105.00"))

    def test_transfer_request_rejects_same_key_with_different_payload(self):
        create_transfer_request(
            sender_account=self.sender.bank_account,
            receiver_account=self.receiver.bank_account,
            amount="100.00",
            initiated_by=self.sender,
            idempotency_key="same-key",
        )

        with self.assertRaises(IdempotencyConflictError):
            create_transfer_request(
                sender_account=self.sender.bank_account,
                receiver_account=self.receiver.bank_account,
                amount="200.00",
                initiated_by=self.sender,
                idempotency_key="same-key",
            )

    def test_cross_currency_transfer_request_is_rejected(self):
        sender_usd = self.sender.get_account_for_currency(AccountCurrency.USD)
        sender_usd.balance = Decimal("1000.00")
        sender_usd.save(update_fields=["balance", "updated_at"])
        receiver_eur = self.receiver.get_account_for_currency(AccountCurrency.EUR)
        with self.assertRaises(TransferError):
            create_transfer_request(
                sender_account=sender_usd,
                receiver_account=receiver_eur,
                amount="100.00",
                initiated_by=self.sender,
            )

    def test_approve_pending_transfer_marks_related_transactions_completed(self):
        transfer = create_transfer_request(
            sender_account=self.sender.bank_account,
            receiver_account=self.receiver.bank_account,
            amount="100.00",
            initiated_by=self.sender,
        )
        approved = approve_pending_transfer(transfer=transfer, reviewed_by=self.manager)

        self.assertEqual(approved.status, TransferStatus.COMPLETED)
        self.assertEqual(approved.transactions.filter(status=TransactionStatus.COMPLETED).count(), 3)

    def test_approve_completed_transfer_is_idempotent(self):
        transfer = create_transfer_request(
            sender_account=self.sender.bank_account,
            receiver_account=self.receiver.bank_account,
            amount="100.00",
            initiated_by=self.sender,
        )
        first = approve_pending_transfer(transfer=transfer, reviewed_by=self.manager)
        second = approve_pending_transfer(transfer=transfer, reviewed_by=self.manager)
        self.assertEqual(first.id, second.id)

    def test_blocking_completed_transfer_raises_state_error(self):
        transfer = create_transfer_request(
            sender_account=self.sender.bank_account,
            receiver_account=self.receiver.bank_account,
            amount="100.00",
            initiated_by=self.sender,
        )
        approve_pending_transfer(transfer=transfer, reviewed_by=self.manager)

        with self.assertRaises(TransferStateError):
            block_pending_transfer(transfer=transfer, reviewed_by=self.manager)


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
        self.assertEqual(response.data["sender_currency"], AccountCurrency.EUR)

        self.sender.bank_account.refresh_from_db()
        self.receiver.bank_account.refresh_from_db()
        self.assertEqual(self.sender.bank_account.balance, Decimal("10000.00"))
        self.assertEqual(self.sender.bank_account.reserved_balance, Decimal("105.00"))
        self.assertEqual(self.sender.bank_account.available_balance, Decimal("9895.00"))
        self.assertEqual(self.receiver.bank_account.balance, Decimal("10000.00"))
        self.assertEqual(self.sender.bank_account.transactions.filter(status="pending").count(), 2)
        self.assertEqual(self.receiver.bank_account.transactions.filter(status="pending").count(), 1)

    def test_transfer_request_can_use_non_default_currency_account(self):
        sender_usd = self.sender.get_account_for_currency(AccountCurrency.USD)
        receiver_usd = self.receiver.get_account_for_currency(AccountCurrency.USD)
        sender_usd.balance = Decimal("500.00")
        sender_usd.save(update_fields=["balance", "updated_at"])
        response = self.client.post(
            "/api/v1/transfers/",
            {
                "source_account_number": sender_usd.account_number,
                "destination_account_number": receiver_usd.account_number,
                "amount": "100.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["sender_currency"], AccountCurrency.USD)

    def test_transfer_request_rejects_cross_currency_accounts(self):
        sender_usd = self.sender.get_account_for_currency(AccountCurrency.USD)
        sender_usd.balance = Decimal("500.00")
        sender_usd.save(update_fields=["balance", "updated_at"])
        response = self.client.post(
            "/api/v1/transfers/",
            {
                "source_account_number": sender_usd.account_number,
                "destination_account_number": self.receiver.bank_account.account_number,
                "amount": "100.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_request_is_idempotent_with_header(self):
        headers = {"HTTP_IDEMPOTENCY_KEY": "transfer-key-1"}
        first = self.client.post(
            "/api/v1/transfers/",
            {"destination_account_number": self.receiver.bank_account.account_number, "amount": "100.00"},
            format="json",
            **headers,
        )
        second = self.client.post(
            "/api/v1/transfers/",
            {"destination_account_number": self.receiver.bank_account.account_number, "amount": "100.00"},
            format="json",
            **headers,
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first.data["id"], second.data["id"])

    def test_transfer_request_conflicts_when_idempotency_key_reused_for_other_payload(self):
        headers = {"HTTP_IDEMPOTENCY_KEY": "transfer-key-2"}
        self.client.post(
            "/api/v1/transfers/",
            {"destination_account_number": self.receiver.bank_account.account_number, "amount": "100.00"},
            format="json",
            **headers,
        )
        response = self.client.post(
            "/api/v1/transfers/",
            {"destination_account_number": self.receiver.bank_account.account_number, "amount": "200.00"},
            format="json",
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
        self.assertEqual(response.data["currency"], AccountCurrency.EUR)

    def test_transaction_list_can_filter_by_currency(self):
        response = self.client.get("/api/v1/transactions/?currency=EUR")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_transaction_list_can_filter_pending_status(self):
        self.client.post(
            "/api/v1/transfers/",
            {
                "destination_account_number": self.receiver.bank_account.account_number,
                "amount": "100.00",
            },
            format="json",
        )
        response = self.client.get("/api/v1/transactions/?status=pending")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 2)

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

    def test_fee_estimate_endpoint_returns_total(self):
        response = self.client.get("/api/v1/transfers/fees/estimate/?amount=100.00")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["fee"], Decimal("5.00"))
        self.assertEqual(response.data["total_debit"], Decimal("105.00"))

    def test_transfer_rejects_self_destination(self):
        response = self.client.post(
            "/api/v1/transfers/",
            {"destination_account_number": self.sender.bank_account.account_number, "amount": "10.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_rejects_invalid_swift_length(self):
        response = self.client.post(
            "/api/v1/transfers/",
            {
                "destination_account_number": self.receiver.bank_account.account_number,
                "amount": "10.00",
                "swift_code": "BAD",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("swift_code", response.data)

    def test_blocked_sender_cannot_transfer(self):
        sender_account = self.sender.bank_account
        sender_account.status = AccountStatus.BLOCKED
        sender_account.save(update_fields=["status", "updated_at"])
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
