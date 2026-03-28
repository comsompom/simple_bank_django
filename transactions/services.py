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


class TransferStateError(TransferError):
    pass


def calculate_transfer_fee(amount):
    if amount <= 0:
        raise TransferError("Amount must be greater than zero.")
    fee = (amount * FEE_RATE).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    return max(fee, MINIMUM_FEE)


def _get_locked_accounts(sender_account_id, receiver_account_id):
    ordered_ids = sorted([sender_account_id, receiver_account_id])
    return {
        account.id: account for account in BankAccount.objects.select_for_update().filter(id__in=ordered_ids)
    }


@db_transaction.atomic
def create_transfer_request(*, sender_account, receiver_account, amount, initiated_by=None, swift_code="", reference=""):
    amount = Decimal(amount).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if sender_account.id == receiver_account.id:
        raise TransferError("You cannot transfer to the same account.")
    if amount <= 0:
        raise TransferError("Amount must be greater than zero.")

    locked_accounts = _get_locked_accounts(sender_account.id, receiver_account.id)
    sender = locked_accounts[sender_account.id]
    receiver = locked_accounts[receiver_account.id]

    if sender.status != AccountStatus.ACTIVE:
        raise TransferError("Sender account is blocked.")
    if receiver.status != AccountStatus.ACTIVE:
        raise TransferError("Receiver account is blocked.")

    fee = calculate_transfer_fee(amount)
    total = (amount + fee).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if sender.available_balance < total:
        raise TransferError("Insufficient available funds to create this transfer request.")

    sender.reserved_balance += total
    sender.save(update_fields=["reserved_balance", "updated_at"])

    transfer = Transfer.objects.create(
        sender_account=sender,
        receiver_account=receiver,
        initiated_by=initiated_by,
        amount=amount,
        fee_amount=fee,
        total_amount=total,
        swift_code=swift_code,
        reference=reference,
        status=TransferStatus.PENDING,
    )

    Transaction.objects.create(
        account=sender,
        related_account=receiver,
        transfer=transfer,
        type=TransactionType.DEBIT,
        status=TransactionStatus.PENDING,
        amount=amount,
        fee_amount=fee,
        reference=reference,
        description="Pending outgoing transfer",
    )
    Transaction.objects.create(
        account=sender,
        related_account=receiver,
        transfer=transfer,
        type=TransactionType.FEE,
        status=TransactionStatus.PENDING,
        amount=fee,
        fee_amount=fee,
        reference=reference,
        description="Pending transfer fee",
    )
    Transaction.objects.create(
        account=receiver,
        related_account=sender,
        transfer=transfer,
        type=TransactionType.CREDIT,
        status=TransactionStatus.PENDING,
        amount=amount,
        fee_amount=Decimal("0.00"),
        reference=reference,
        description="Pending incoming transfer",
    )

    return transfer


@db_transaction.atomic
def approve_pending_transfer(*, transfer, reviewed_by):
    locked_transfer = Transfer.objects.select_for_update().select_related("sender_account", "receiver_account").get(pk=transfer.pk)
    if locked_transfer.status != TransferStatus.PENDING:
        raise TransferStateError("Only pending transfers can be approved.")

    locked_accounts = _get_locked_accounts(locked_transfer.sender_account_id, locked_transfer.receiver_account_id)
    sender = locked_accounts[locked_transfer.sender_account_id]
    receiver = locked_accounts[locked_transfer.receiver_account_id]

    if sender.status != AccountStatus.ACTIVE:
        raise TransferError("Sender account is blocked.")
    if receiver.status != AccountStatus.ACTIVE:
        raise TransferError("Receiver account is blocked.")
    if sender.reserved_balance < locked_transfer.total_amount:
        raise TransferError("Reserved funds are no longer available for this transfer.")

    sender.reserved_balance -= locked_transfer.total_amount
    sender.balance -= locked_transfer.total_amount
    receiver.balance += locked_transfer.amount
    sender.save(update_fields=["reserved_balance", "balance", "updated_at"])
    receiver.save(update_fields=["balance", "updated_at"])

    processed_at = timezone.now()
    locked_transfer.status = TransferStatus.COMPLETED
    locked_transfer.reviewed_by = reviewed_by
    locked_transfer.processed_at = processed_at
    locked_transfer.save(update_fields=["status", "reviewed_by", "processed_at", "updated_at"])

    locked_transfer.transactions.update(status=TransactionStatus.COMPLETED, processed_at=processed_at)
    return locked_transfer


@db_transaction.atomic
def block_pending_transfer(*, transfer, reviewed_by):
    locked_transfer = Transfer.objects.select_for_update().select_related("sender_account").get(pk=transfer.pk)
    if locked_transfer.status != TransferStatus.PENDING:
        raise TransferStateError("Only pending transfers can be blocked.")

    sender = BankAccount.objects.select_for_update().get(pk=locked_transfer.sender_account_id)
    if sender.reserved_balance < locked_transfer.total_amount:
        raise TransferError("Reserved funds are lower than the pending transfer total.")

    sender.reserved_balance -= locked_transfer.total_amount
    sender.save(update_fields=["reserved_balance", "updated_at"])

    processed_at = timezone.now()
    locked_transfer.status = TransferStatus.BLOCKED
    locked_transfer.reviewed_by = reviewed_by
    locked_transfer.processed_at = processed_at
    locked_transfer.save(update_fields=["status", "reviewed_by", "processed_at", "updated_at"])
    locked_transfer.transactions.update(status=TransactionStatus.BLOCKED, processed_at=processed_at)
    return locked_transfer
