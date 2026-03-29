from decimal import Decimal, ROUND_HALF_UP
from django.db import models


class AccountCurrency(models.TextChoices):
    EUR = "EUR", "Euro"
    USD = "USD", "US Dollar"
    GBP = "GBP", "British Pound"
    PLN = "PLN", "Polish Zloty"


TWOPLACES = Decimal("0.01")
BASE_RATES = {
    AccountCurrency.EUR: Decimal("1.00"),
    AccountCurrency.USD: Decimal("1.08"),
    AccountCurrency.GBP: Decimal("0.86"),
    AccountCurrency.PLN: Decimal("4.30"),
}

CURRENCY_METADATA = {
    AccountCurrency.EUR: {
        "name": "Euro",
        "symbol": "EUR",
        "flag_file": "webui/flags/eur.svg",
        "country": "European Union",
    },
    AccountCurrency.USD: {
        "name": "US Dollar",
        "symbol": "USD",
        "flag_file": "webui/flags/usd.svg",
        "country": "United States",
    },
    AccountCurrency.GBP: {
        "name": "British Pound",
        "symbol": "GBP",
        "flag_file": "webui/flags/gbp.svg",
        "country": "United Kingdom",
    },
    AccountCurrency.PLN: {
        "name": "Polish Zloty",
        "symbol": "PLN",
        "flag_file": "webui/flags/pln.svg",
        "country": "Poland",
    },
}

SUPPORTED_ACCOUNT_CURRENCIES = [
    AccountCurrency.EUR,
    AccountCurrency.USD,
    AccountCurrency.GBP,
    AccountCurrency.PLN,
]


def get_currency_metadata(currency):
    return CURRENCY_METADATA[currency]


def get_currency_choices():
    return [(currency.value, f"{currency.value} - {currency.label}") for currency in SUPPORTED_ACCOUNT_CURRENCIES]


def convert_currency(amount, from_currency, to_currency):
    amount = Decimal(amount).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if from_currency == to_currency:
        return amount
    eur_amount = amount / BASE_RATES[AccountCurrency(from_currency)]
    converted = eur_amount * BASE_RATES[AccountCurrency(to_currency)]
    return converted.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
