from decimal import Decimal
import random

from django.utils import timezone

from accounts.currencies import AccountCurrency, SUPPORTED_ACCOUNT_CURRENCIES
from accounts.models import BankAccount

WELCOME_BONUS = Decimal("10000.00")


def generate_account_number():
    while True:
        account_number = "".join(random.choices("0123456789", k=10))
        if not BankAccount.objects.filter(account_number=account_number).exists():
            return account_number


def create_account_for_user(*, user, currency, swift_code="", with_welcome_bonus=False):
    from transactions.models import Transaction, TransactionStatus, TransactionType

    account = BankAccount.objects.create(
        user=user,
        account_number=generate_account_number(),
        swift_code=swift_code,
        currency=currency,
        balance=WELCOME_BONUS if with_welcome_bonus else Decimal("0.00"),
    )
    if with_welcome_bonus:
        Transaction.objects.create(
            account=account,
            type=TransactionType.WELCOME_BONUS,
            status=TransactionStatus.COMPLETED,
            amount=WELCOME_BONUS,
            description="Automatic welcome bonus",
            processed_at=timezone.now(),
        )
    return account


def create_default_accounts_for_user(*, user, swift_code="", with_welcome_bonus=True):
    accounts = []
    for currency in SUPPORTED_ACCOUNT_CURRENCIES:
        accounts.append(
            create_account_for_user(
                user=user,
                currency=currency,
                swift_code=swift_code,
                with_welcome_bonus=with_welcome_bonus and currency == AccountCurrency.EUR,
            )
        )
    return accounts


def get_user_accounts(user):
    return user.accounts.all().order_by("currency")


def get_user_account(*, user, currency=None, account_number=None):
    queryset = user.accounts.all()
    if account_number:
        try:
            return queryset.get(account_number=account_number)
        except BankAccount.DoesNotExist:
            return user.bank_account
    if currency:
        try:
            return queryset.get(currency=currency)
        except BankAccount.DoesNotExist:
            return user.bank_account
    return user.bank_account
