from decimal import Decimal

from django.conf import settings
from django.db import models


class AccountStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    BLOCKED = "blocked", "Blocked"


class BankAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bank_account")
    account_number = models.CharField(max_length=10, unique=True)
    swift_code = models.CharField(max_length=11, blank=True)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    reserved_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, default="EUR")
    status = models.CharField(max_length=20, choices=AccountStatus.choices, default=AccountStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["account_number"]

    def __str__(self):
        return f"{self.account_number} ({self.user.email})"

    @property
    def is_blocked(self):
        return self.status == AccountStatus.BLOCKED

    @property
    def available_balance(self):
        return self.balance - self.reserved_balance
