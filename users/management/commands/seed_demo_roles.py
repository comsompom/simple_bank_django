from django.core.management.base import BaseCommand

from accounts.models import BankAccount
from users.models import User, UserRole
from users.services import create_user_with_account


class Command(BaseCommand):
    help = "Create demo manager and director accounts for local testing."

    def handle(self, *args, **options):
        defaults = [
            ("manager@simplebank.local", "Manager Demo", UserRole.MANAGER),
            ("director@simplebank.local", "Director Demo", UserRole.DIRECTOR),
        ]
        for email, full_name, role in defaults:
            if User.objects.filter(email=email).exists():
                self.stdout.write(self.style.WARNING(f"{email} already exists"))
                continue
            create_user_with_account(email=email, password="Passw0rd!234", full_name=full_name, role=role)
            self.stdout.write(self.style.SUCCESS(f"Created {role}: {email}"))
