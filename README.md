# SimpleBank Django

SimpleBank is a Django banking system with a REST API and a modern web UI. It supports user registration, JWT authentication, automatic account creation with a EUR 10,000 welcome bonus, transaction history, transfers with fees, QR-based receive requests, manager tools, director reporting, and automated tests.

## Features

- User registration with automatic bank account creation
- JWT login for API access
- Session-based login for the web UI
- Current balance endpoint
- Transaction history with date filtering
- Transfers with fee calculation: 2.5% or minimum EUR 5
- Atomic balance updates with audit-friendly transaction records
- User QR code generation for receiving money
- Manager account blocking and user transaction visibility
- Director reporting for users, transactions, and bank earnings
- SQLite by default with PostgreSQL-ready configuration

## Quickstart

1. Create and activate a virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`.
4. Run migrations:
   `python manage.py migrate`
5. Optionally create demo manager and director accounts:
   `python manage.py seed_demo_roles`
6. Start the server:
   `python manage.py runserver`

## Default URLs

- Web UI: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`
- API auth register: `POST /api/v1/auth/register/`
- API auth login: `POST /api/v1/auth/login/`
- API profile: `GET /api/v1/auth/me/`
- API account balance: `GET /api/v1/accounts/balance/`
- API transactions: `GET /api/v1/transactions/?from=YYYY-MM-DD&to=YYYY-MM-DD`
- API transfer: `POST /api/v1/transfers/`
- API fee estimate: `GET /api/v1/transfers/fees/estimate/?amount=100.00`
- API QR: `POST /api/v1/qr/generate/`
- Manager block account: `POST /api/v1/manager/accounts/<id>/block/`
- Director overview: `GET /api/v1/director/reports/overview/`

## Example API payloads

### Register

```json
{
  "email": "alice@example.com",
  "full_name": "Alice Example",
  "password": "Passw0rd!234"
}
```

### Login

```json
{
  "email": "alice@example.com",
  "password": "Passw0rd!234"
}
```

### Transfer

```json
{
  "destination_account_number": "1234567890",
  "amount": "150.00",
  "swift_code": "BANKDEFF",
  "reference": "Invoice #52"
}
```

## Roles

- `user`: can view balance, transfer money, generate QR requests, and review personal transaction reports.
- `manager`: can inspect user transaction history, create user accounts through the API, and block accounts.
- `director`: can view aggregate KPIs about users, transactions, and bank fee earnings.

## PostgreSQL switch

Set the following environment variables in `.env`:

- `DB_ENGINE=postgresql`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

## Tests

Run the backend tests with:

`pytest`

## Performance tests

A load-test scaffold is included in `performance/locustfile.py`.
Run it with:

`locust -f performance/locustfile.py`

## Notes

- Money values use `Decimal`.
- Transfers are atomic and create debit, fee, and credit records.
- Manager transfer blocking is implemented for pending transfers; user-initiated transfers complete immediately in the current version.
