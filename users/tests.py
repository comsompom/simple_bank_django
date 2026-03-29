from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.currencies import AccountCurrency
from transactions.models import Transaction, TransactionType
from users.models import User, UserRole
from users.services import create_user_with_account


class AuthFlowTests(APITestCase):
    def test_register_creates_accounts_and_welcome_bonus(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {"email": "alice@example.com", "full_name": "Alice Example", "password": "Passw0rd!234"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["account"]["balance"], "10000.00")
        self.assertEqual(response.data["account"]["currency"], AccountCurrency.EUR)
        self.assertEqual(len(response.data["accounts"]), 4)
        self.assertTrue(User.objects.filter(email="alice@example.com").exists())

    def test_register_rejects_duplicate_email(self):
        create_user_with_account(
            email="dup@example.com",
            password="Passw0rd!234",
            full_name="Dup User",
        )
        response = self.client.post(
            "/api/v1/auth/register/",
            {"email": "dup@example.com", "full_name": "Another User", "password": "Passw0rd!234"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

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

    def test_refresh_returns_new_access_token(self):
        User.objects.create_user(email="refresh@example.com", full_name="Refresh User", password="Passw0rd!234")
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "refresh@example.com", "password": "Passw0rd!234"},
            format="json",
        )
        response = self.client.post(
            "/api/v1/auth/refresh/",
            {"refresh": login_response.data["refresh"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_me_returns_authenticated_profile(self):
        user = create_user_with_account(
            email="me@example.com",
            password="Passw0rd!234",
            full_name="Me User",
        )
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "me@example.com", "password": "Passw0rd!234"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], user.email)
        self.assertEqual(len(response.data["accounts"]), 4)

    def test_me_requires_authentication(self):
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserServiceTests(TestCase):
    def test_create_user_with_account_adds_bonus_for_eur_account_only(self):
        user = create_user_with_account(
            email="service-user@example.com",
            password="Passw0rd!234",
            full_name="Service User",
        )
        self.assertEqual(user.role, UserRole.USER)
        self.assertEqual(user.accounts.count(), 4)
        self.assertEqual(user.bank_account.currency, AccountCurrency.EUR)
        self.assertEqual(user.bank_account.balance, 10000)
        self.assertFalse(user.is_staff)
        self.assertTrue(
            Transaction.objects.filter(account=user.bank_account, type=TransactionType.WELCOME_BONUS).exists()
        )
        self.assertEqual(user.get_account_for_currency(AccountCurrency.USD).balance, 0)

    def test_create_user_with_account_skips_bonus_for_manager(self):
        manager = create_user_with_account(
            email="service-manager@example.com",
            password="Passw0rd!234",
            full_name="Service Manager",
            role=UserRole.MANAGER,
        )
        self.assertEqual(manager.accounts.count(), 4)
        self.assertEqual(manager.bank_account.balance, 0)
        self.assertTrue(manager.is_staff)
        self.assertFalse(
            Transaction.objects.filter(account=manager.bank_account, type=TransactionType.WELCOME_BONUS).exists()
        )


class SeedDemoRolesCommandTests(TestCase):
    def test_seed_demo_roles_creates_manager_and_director(self):
        stdout = StringIO()
        call_command("seed_demo_roles", stdout=stdout)

        self.assertTrue(User.objects.filter(email="manager@simplebank.local", role=UserRole.MANAGER).exists())
        self.assertTrue(User.objects.filter(email="director@simplebank.local", role=UserRole.DIRECTOR).exists())
        self.assertEqual(User.objects.get(email="manager@simplebank.local").accounts.count(), 4)

    def test_seed_demo_roles_is_idempotent(self):
        call_command("seed_demo_roles")
        stdout = StringIO()
        call_command("seed_demo_roles", stdout=stdout)

        self.assertIn("already exists", stdout.getvalue())
        self.assertEqual(User.objects.filter(email="manager@simplebank.local").count(), 1)
        self.assertEqual(User.objects.filter(email="director@simplebank.local").count(), 1)
