from decimal import Decimal
import random

from django.utils import timezone

from accounts.models import BankAccount

WELCOME_BONUS = Decimal("10000.00")


def generate_account_number():
    while True:
        account_number = "".join(random.choices("0123456789", k=10))
        if not BankAccount.objects.filter(account_number=account_number).exists():
            return account_number


def create_account_for_user(*, user, swift_code="", with_welcome_bonus=True):
    from transactions.models import Transaction, TransactionStatus, TransactionType

    account = BankAccount.objects.create(
        user=user,
        account_number=generate_account_number(),
        swift_code=swift_code,
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
