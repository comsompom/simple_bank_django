from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, serializers
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.models import BankAccount
from users.models import User, UserRole
from users.services import create_user_with_account


class LoginAPIView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"


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

    def validate_email(self, value):
        normalized = value.lower()
        if User.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

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

    def validate_email(self, value):
        normalized = value.lower()
        if User.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return create_user_with_account(role=UserRole.USER, **validated_data)


@extend_schema(tags=["Authentication"])
class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_register"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return_response = UserSerializer(user, context=self.get_serializer_context())
        headers = self.get_success_headers(return_response.data)
        from rest_framework.response import Response

        return Response(return_response.data, status=201, headers=headers)


@extend_schema(tags=["Authentication"])
class MeAPIView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


__all__ = [
    "LoginAPIView",
    "ManagedUserCreateSerializer",
    "MeAPIView",
    "RegisterAPIView",
    "TokenRefreshView",
    "UserSerializer",
]
