from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class TransactionType(models.TextChoices):
    CREDIT = "credit", "Credit"
    DEBIT = "debit", "Debit"
    FEE = "fee", "Fee"
    WELCOME_BONUS = "welcome_bonus", "Welcome bonus"


class TransactionStatus(models.TextChoices):
    COMPLETED = "completed", "Completed"
    PENDING = "pending", "Pending"
    BLOCKED = "blocked", "Blocked"
    FAILED = "failed", "Failed"


class TransferStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    BLOCKED = "blocked", "Blocked"
    FAILED = "failed", "Failed"


class Transfer(models.Model):
    sender_account = models.ForeignKey("accounts.BankAccount", on_delete=models.CASCADE, related_name="outgoing_transfers")
    receiver_account = models.ForeignKey("accounts.BankAccount", on_delete=models.CASCADE, related_name="incoming_transfers")
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_transfers")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    fee_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    swift_code = models.CharField(max_length=11, blank=True)
    reference = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=TransferStatus.choices, default=TransferStatus.COMPLETED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sender_account.account_number} -> {self.receiver_account.account_number} ({self.amount})"


class Transaction(models.Model):
    account = models.ForeignKey("accounts.BankAccount", on_delete=models.CASCADE, related_name="transactions")
    related_account = models.ForeignKey("accounts.BankAccount", on_delete=models.SET_NULL, null=True, blank=True, related_name="related_transactions")
    transfer = models.ForeignKey(Transfer, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    status = models.CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.COMPLETED)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    fee_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    reference = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.account.account_number} {self.type} {self.amount}"
