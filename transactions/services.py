from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction as db_transaction
from django.utils import timezone

from accounts.models import AccountStatus, BankAccount
from transactions.models import Transaction, TransactionStatus, TransactionType, Transfer, TransferStatus

MINIMUM_FEE = Decimal("5.00")
FEE_RATE = Decimal("0.025")
TWOPLACES = Decimal("0.01")


class TransferError(Exception):
    pass


def calculate_transfer_fee(amount):
    if amount <= 0:
        raise TransferError("Amount must be greater than zero.")
    fee = (amount * FEE_RATE).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    return max(fee, MINIMUM_FEE)


@db_transaction.atomic
def perform_transfer(*, sender_account, receiver_account, amount, initiated_by=None, swift_code="", reference=""):
    amount = Decimal(amount).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if sender_account.id == receiver_account.id:
        raise TransferError("You cannot transfer to the same account.")
    if amount <= 0:
        raise TransferError("Amount must be greater than zero.")

    ordered_ids = sorted([sender_account.id, receiver_account.id])
    locked_accounts = {
        account.id: account
        for account in BankAccount.objects.select_for_update().filter(id__in=ordered_ids)
    }
    sender = locked_accounts[sender_account.id]
    receiver = locked_accounts[receiver_account.id]

    if sender.status != AccountStatus.ACTIVE:
        raise TransferError("Sender account is blocked.")
    if receiver.status != AccountStatus.ACTIVE:
        raise TransferError("Receiver account is blocked.")

    fee = calculate_transfer_fee(amount)
    total = (amount + fee).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if sender.balance < total:
        raise TransferError("Insufficient funds to complete this transfer.")

    sender.balance -= total
    receiver.balance += amount
    sender.save(update_fields=["balance", "updated_at"])
    receiver.save(update_fields=["balance", "updated_at"])

    transfer = Transfer.objects.create(
        sender_account=sender,
        receiver_account=receiver,
        initiated_by=initiated_by,
        amount=amount,
        fee_amount=fee,
        total_amount=total,
        swift_code=swift_code,
        reference=reference,
        status=TransferStatus.COMPLETED,
        processed_at=timezone.now(),
    )

    Transaction.objects.create(
        account=sender,
        related_account=receiver,
        transfer=transfer,
        type=TransactionType.DEBIT,
        status=TransactionStatus.COMPLETED,
        amount=amount,
        fee_amount=fee,
        reference=reference,
        description="Outgoing transfer",
    )
    Transaction.objects.create(
        account=sender,
        related_account=receiver,
        transfer=transfer,
        type=TransactionType.FEE,
        status=TransactionStatus.COMPLETED,
        amount=fee,
        fee_amount=fee,
        reference=reference,
        description="Transfer fee",
    )
    Transaction.objects.create(
        account=receiver,
        related_account=sender,
        transfer=transfer,
        type=TransactionType.CREDIT,
        status=TransactionStatus.COMPLETED,
        amount=amount,
        fee_amount=Decimal("0.00"),
        reference=reference,
        description="Incoming transfer",
    )

    return transfer


@db_transaction.atomic
def block_pending_transfer(*, transfer, reviewed_by):
    locked_transfer = Transfer.objects.select_for_update().get(pk=transfer.pk)
    if locked_transfer.status != TransferStatus.PENDING:
        raise TransferError("Only pending transfers can be blocked.")
    locked_transfer.status = TransferStatus.BLOCKED
    locked_transfer.reviewed_by = reviewed_by
    locked_transfer.processed_at = timezone.now()
    locked_transfer.save(update_fields=["status", "reviewed_by", "processed_at", "updated_at"])
    return locked_transfer
