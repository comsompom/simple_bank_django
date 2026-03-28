from django.contrib import admin

from transactions.models import Transaction, Transfer


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ("id", "sender_account", "receiver_account", "amount", "fee_amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("sender_account__account_number", "receiver_account__account_number", "reference")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "type", "amount", "status", "created_at")
    list_filter = ("type", "status")
    search_fields = ("account__account_number", "reference", "description")
