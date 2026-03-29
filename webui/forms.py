from django import forms
from django.contrib.auth import authenticate

from accounts.currencies import AccountCurrency, get_currency_choices
from accounts.models import BankAccount
from accounts.services import get_user_accounts
from transactions.services import validate_swift_code
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
    source_account_number = forms.ChoiceField(label="From account")
    destination_account_number = forms.CharField(
        max_length=10,
        min_length=10,
        label="Destination account number",
        help_text="Enter the 10-digit recipient account number.",
        widget=forms.TextInput(
            attrs={
                "placeholder": "1234567890",
                "inputmode": "numeric",
                "autocomplete": "off",
            }
        ),
    )
    amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0.01,
        label="Amount",
        help_text="Transfer fee is 2.5% of the amount or a minimum of 5 in the selected account currency.",
        widget=forms.NumberInput(attrs={"placeholder": "150.00", "step": "0.01", "min": "0.01"}),
    )
    swift_code = forms.CharField(
        max_length=11,
        required=False,
        label="SWIFT / BIC code",
        help_text="Optional for local testing. Use 8 or 11 characters if provided.",
        widget=forms.TextInput(attrs={"placeholder": "BANKDEFF", "autocomplete": "off"}),
    )
    reference = forms.CharField(
        max_length=255,
        required=False,
        label="Reference",
        help_text="Optional note visible in the transaction history.",
        widget=forms.TextInput(attrs={"placeholder": "Invoice 2026-001"}),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.selected_currency = kwargs.pop("selected_currency", None)
        self.destination_account = None
        self.source_account = None
        super().__init__(*args, **kwargs)
        if self.user and self.user.is_authenticated:
            account_choices = []
            initial_account_number = None
            for account in get_user_accounts(self.user):
                label = f"{account.currency} - {account.account_number} - Available {account.available_balance}"
                account_choices.append((account.account_number, label))
                if account.currency == self.selected_currency:
                    initial_account_number = account.account_number
            self.fields["source_account_number"].choices = account_choices
            if initial_account_number:
                self.initial.setdefault("source_account_number", initial_account_number)

    def clean_source_account_number(self):
        account_number = self.cleaned_data["source_account_number"]
        if not self.user or not self.user.is_authenticated:
            raise forms.ValidationError("Authentication is required.")
        try:
            self.source_account = self.user.accounts.get(account_number=account_number)
        except BankAccount.DoesNotExist as exc:
            raise forms.ValidationError("Selected source account was not found.") from exc
        return account_number

    def clean_destination_account_number(self):
        account_number = self.cleaned_data["destination_account_number"].strip()
        if not account_number.isdigit():
            raise forms.ValidationError("Account number must contain exactly 10 digits.")
        try:
            self.destination_account = BankAccount.objects.get(account_number=account_number)
        except BankAccount.DoesNotExist as exc:
            raise forms.ValidationError("Destination account was not found.") from exc
        return account_number

    def clean(self):
        cleaned_data = super().clean()
        source_account = getattr(self, "source_account", None)
        destination_account = getattr(self, "destination_account", None)
        if source_account and destination_account:
            if source_account.account_number == destination_account.account_number:
                self.add_error("destination_account_number", "You cannot send money to your own account.")
            if source_account.currency != destination_account.currency:
                self.add_error("destination_account_number", "Destination account must use the same currency as the selected source account.")
        return cleaned_data

    def clean_swift_code(self):
        try:
            return validate_swift_code(self.cleaned_data["swift_code"])
        except Exception as exc:
            raise forms.ValidationError(str(exc)) from exc


class QRForm(forms.Form):
    account_number = forms.ChoiceField(label="Account")
    amount = forms.DecimalField(max_digits=14, decimal_places=2)
    note = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        selected_currency = kwargs.pop("selected_currency", None)
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            choices = []
            initial_account_number = None
            for account in get_user_accounts(user):
                label = f"{account.currency} - {account.account_number}"
                choices.append((account.account_number, label))
                if account.currency == selected_currency:
                    initial_account_number = account.account_number
            self.fields["account_number"].choices = choices
            if initial_account_number:
                self.initial.setdefault("account_number", initial_account_number)


class CurrencyConverterForm(forms.Form):
    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=0.01, initial="100.00")
    from_currency = forms.ChoiceField(choices=get_currency_choices())
    to_currency = forms.ChoiceField(choices=get_currency_choices())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["from_currency"].initial = AccountCurrency.EUR
        self.fields["to_currency"].initial = AccountCurrency.USD
