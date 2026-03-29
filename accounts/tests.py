from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.currencies import AccountCurrency, convert_currency
from accounts.services import create_account_for_user, generate_account_number
from users.services import create_user_with_account

User = get_user_model()


class AccountServiceTests(TestCase):
    def test_generate_account_number_returns_10_digits(self):
        account_number = generate_account_number()
        self.assertEqual(len(account_number), 10)
        self.assertTrue(account_number.isdigit())

    def test_create_account_for_user_without_bonus_starts_at_zero(self):
        user = User.objects.create_user(
            email="plain-account@example.com",
            password="Passw0rd!234",
            full_name="Plain Account",
        )
        account = create_account_for_user(user=user, currency=AccountCurrency.USD, swift_code="BANKDEFF", with_welcome_bonus=False)
        self.assertEqual(account.balance, 0)
        self.assertEqual(account.swift_code, "BANKDEFF")
        self.assertEqual(account.reserved_balance, 0)
        self.assertEqual(account.currency, AccountCurrency.USD)

    def test_convert_currency_returns_expected_value(self):
        converted = convert_currency(Decimal("100.00"), AccountCurrency.EUR, AccountCurrency.USD)
        self.assertEqual(converted, Decimal("108.00"))


class AccountApiTests(APITestCase):
    def setUp(self):
        self.user = create_user_with_account(
            email="account-api@example.com",
            password="Passw0rd!234",
            full_name="Account Api",
        )
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {"email": self.user.email, "password": "Passw0rd!234"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

    def test_account_me_returns_account_portfolio(self):
        response = self.client.get("/api/v1/accounts/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["selected_account"]["currency"], AccountCurrency.EUR)
        self.assertEqual(len(response.data["accounts"]), 4)

    def test_account_me_can_select_currency(self):
        response = self.client.get("/api/v1/accounts/me/?currency=USD")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["selected_currency"], AccountCurrency.USD)

    def test_balance_can_select_currency(self):
        response = self.client.get("/api/v1/accounts/balance/?currency=GBP")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["currency"], AccountCurrency.GBP)

    def test_convert_endpoint_returns_conversion_result(self):
        response = self.client.get("/api/v1/accounts/convert/?amount=100.00&from_currency=EUR&to_currency=PLN")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["converted_amount"], Decimal("430.00"))

    def test_balance_requires_authentication(self):
        self.client.credentials()
        response = self.client.get("/api/v1/accounts/balance/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
