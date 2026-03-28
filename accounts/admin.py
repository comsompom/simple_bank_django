from django.contrib import admin

from accounts.models import BankAccount


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("account_number", "user", "balance", "currency", "status", "swift_code")
    list_filter = ("status", "currency")
    search_fields = ("account_number", "user__email", "user__full_name")
