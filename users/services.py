from django.db import transaction

from accounts.services import create_default_accounts_for_user
from users.models import UserRole


@transaction.atomic
def create_user_with_account(*, email, password, full_name, role=UserRole.USER, swift_code=""):
    from users.models import User

    user = User.objects.create_user(
        email=email,
        password=password,
        full_name=full_name,
        role=role,
        is_staff=role in {UserRole.MANAGER, UserRole.DIRECTOR},
    )
    create_default_accounts_for_user(user=user, swift_code=swift_code, with_welcome_bonus=role == UserRole.USER)
    return user
