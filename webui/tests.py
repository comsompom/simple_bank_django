from django.test import TestCase
from django.urls import reverse

from transactions.models import TransferStatus
from transactions.services import create_transfer_request
from users.services import create_user_with_account
from users.models import UserRole


class TransferPageTests(TestCase):
    def setUp(self):
        self.user = create_user_with_account(
            email="webuser@example.com",
            password="Passw0rd!234",
            full_name="Web User",
        )
        self.client.force_login(self.user)

    def test_invalid_destination_account_shows_form_error(self):
        response = self.client.post(
            reverse("transfer"),
            {
                "destination_account_number": "9999999999",
                "amount": "50.00",
                "swift_code": "",
                "reference": "Test",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Destination account was not found.")

    def test_own_account_is_rejected(self):
        response = self.client.post(
            reverse("transfer"),
            {
                "destination_account_number": self.user.bank_account.account_number,
                "amount": "50.00",
                "swift_code": "",
                "reference": "Test",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You cannot send money to your own account.")

    def test_transfer_page_shows_account_guidance(self):
        response = self.client.get(reverse("transfer"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.bank_account.account_number)
        self.assertContains(response, "Destination account number must contain exactly 10 digits.")


class DirectorDashboardTests(TestCase):
    def setUp(self):
        self.director = create_user_with_account(
            email="director-ui@example.com",
            password="Passw0rd!234",
            full_name="Director UI",
            role=UserRole.DIRECTOR,
        )
        self.client.force_login(self.director)

    def test_director_dashboard_includes_chart_triggers_and_panels(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Click to open detailed chart")
        self.assertContains(response, "Detailed charts")
        self.assertContains(response, "User role distribution")
        self.assertContains(response, 'data-chart-trigger', html=False)
        self.assertContains(response, 'data-chart-panel', html=False)


class ManagerDashboardActionTests(TestCase):
    def setUp(self):
        self.user = create_user_with_account(
            email="managed-user@example.com",
            password="Passw0rd!234",
            full_name="Managed User",
        )
        self.receiver = create_user_with_account(
            email="managed-receiver@example.com",
            password="Passw0rd!234",
            full_name="Managed Receiver",
        )
        self.manager = create_user_with_account(
            email="manager-ui@example.com",
            password="Passw0rd!234",
            full_name="Manager UI",
            role=UserRole.MANAGER,
        )
        self.transfer = create_transfer_request(
            sender_account=self.user.bank_account,
            receiver_account=self.receiver.bank_account,
            amount="100.00",
            initiated_by=self.user,
        )
        self.client.force_login(self.manager)

    def test_manager_dashboard_approve_action_uses_web_route(self):
        response = self.client.post(reverse("webui-manager-approve-transfer", args=[self.transfer.id]))

        self.assertEqual(response.status_code, 302)
        self.transfer.refresh_from_db()
        self.assertEqual(self.transfer.status, TransferStatus.COMPLETED)

    def test_manager_dashboard_block_action_uses_web_route(self):
        transfer = create_transfer_request(
            sender_account=self.user.bank_account,
            receiver_account=self.receiver.bank_account,
            amount="50.00",
            initiated_by=self.user,
        )

        response = self.client.post(reverse("webui-manager-block-transfer", args=[transfer.id]))

        self.assertEqual(response.status_code, 302)
        transfer.refresh_from_db()
        self.assertEqual(transfer.status, TransferStatus.BLOCKED)
