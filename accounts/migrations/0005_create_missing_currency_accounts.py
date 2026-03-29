from django.db import migrations
import random


SUPPORTED_CURRENCIES = ["EUR", "USD", "GBP", "PLN"]


def generate_account_number(BankAccount):
    while True:
        account_number = "".join(random.choices("0123456789", k=10))
        if not BankAccount.objects.filter(account_number=account_number).exists():
            return account_number


def create_missing_accounts(apps, schema_editor):
    User = apps.get_model("users", "User")
    BankAccount = apps.get_model("accounts", "BankAccount")

    for user in User.objects.all():
        existing_currencies = set(BankAccount.objects.filter(user=user).values_list("currency", flat=True))
        for currency in SUPPORTED_CURRENCIES:
            if currency in existing_currencies:
                continue
            BankAccount.objects.create(
                user=user,
                account_number=generate_account_number(BankAccount),
                swift_code="",
                balance="0.00",
                reserved_balance="0.00",
                currency=currency,
                status="active",
            )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_user_default_currency"),
        ("accounts", "0004_alter_bankaccount_options_alter_bankaccount_currency_and_more"),
    ]

    operations = [
        migrations.RunPython(create_missing_accounts, migrations.RunPython.noop),
    ]
