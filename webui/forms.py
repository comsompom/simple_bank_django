from django import forms
from django.contrib.auth import authenticate
from accounts.models import BankAccount

from users.models import User
from users.services import create_user_with_account


class RegisterForm(forms.Form):
    full_name = forms.CharField(max_length=255)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data

    def save(self):
        return create_user_with_account(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            full_name=self.cleaned_data["full_name"],
        )


class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")
        if email and password:
            self.user = authenticate(self.request, email=email, password=password)
            if self.user is None:
                raise forms.ValidationError("Invalid email or password.")
        return cleaned_data

    def get_user(self):
        return self.user


class TransferForm(forms.Form):
    destination_account_number = forms.CharField(max_length=10)
    amount = forms.DecimalField(max_digits=14, decimal_places=2)
    swift_code = forms.CharField(max_length=11, required=False)
    reference = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.destination_account = None
        super().__init__(*args, **kwargs)

    def clean_destination_account_number(self):
        account_number = self.cleaned_data["destination_account_number"].strip()
        try:
            self.destination_account = BankAccount.objects.get(account_number=account_number)
        except BankAccount.DoesNotExist as exc:
            raise forms.ValidationError("Destination account was not found.") from exc

        if self.user and self.user.is_authenticated and self.user.bank_account.account_number == account_number:
            raise forms.ValidationError("You cannot send money to your own account.")

        return account_number


class QRForm(forms.Form):
    amount = forms.DecimalField(max_digits=14, decimal_places=2)
    note = forms.CharField(max_length=255, required=False)
