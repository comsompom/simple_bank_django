from django.contrib.auth.password_validation import validate_password
from rest_framework import generics, permissions, serializers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.models import BankAccount
from users.models import User, UserRole
from users.services import create_user_with_account


class AccountSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ["account_number", "balance", "currency", "status", "swift_code"]


class UserSerializer(serializers.ModelSerializer):
    account = AccountSummarySerializer(source="bank_account", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "account"]


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return create_user_with_account(role=UserRole.USER, **validated_data)


class ManagedUserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True, min_length=8)
    swift_code = serializers.CharField(max_length=11, required=False, allow_blank=True)

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return create_user_with_account(role=UserRole.USER, **validated_data)


class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return_response = UserSerializer(user, context=self.get_serializer_context())
        headers = self.get_success_headers(return_response.data)
        from rest_framework.response import Response

        return Response(return_response.data, status=201, headers=headers)


class MeAPIView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


__all__ = [
    "ManagedUserCreateSerializer",
    "MeAPIView",
    "RegisterAPIView",
    "TokenObtainPairView",
    "TokenRefreshView",
    "UserSerializer",
]
