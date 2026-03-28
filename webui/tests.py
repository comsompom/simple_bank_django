from django.test import TestCase
from django.urls import reverse

from users.services import create_user_with_account


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
