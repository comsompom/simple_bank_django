from django.contrib.auth import get_user_model
from django.db.models import Count, Sum

from accounts.models import AccountStatus, BankAccount
from transactions.models import Transaction, Transfer, TransferStatus
from users.models import UserRole

User = get_user_model()


def get_director_overview_data():
    total_fee_earnings = (
        Transfer.objects.filter(status=TransferStatus.COMPLETED).aggregate(total=Sum("fee_amount"))["total"]
        or 0
    )
    return {
        "users_count": User.objects.filter(role=UserRole.USER).count(),
        "transactions_count": Transaction.objects.count(),
        "bank_earnings": total_fee_earnings,
        "blocked_accounts": BankAccount.objects.filter(status=AccountStatus.BLOCKED).count(),
        "pending_transfers": Transfer.objects.filter(status=TransferStatus.PENDING).count(),
    }


def get_director_count_map(*, model, group_field):
    return {entry[group_field]: entry["total"] for entry in model.objects.values(group_field).annotate(total=Count("id"))}
