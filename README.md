# SimpleBank Django

SimpleBank is a Django banking system with a REST API and a modern web UI. It supports JWT authentication, automatic multi-currency account creation, a EUR 10,000 welcome bonus on the EUR account, transaction history, QR-based receive requests, a built-in currency converter, director reporting, and a manager-controlled transfer approval workflow.

## Features

- User registration with automatic bank account creation
- JWT login for API access
- Session-based login for the web UI
- Automatic creation of four accounts per user: `EUR`, `USD`, `GBP`, `PLN`
- Current, reserved, and available balance visibility
- Multi-currency wallet view with country flags
- Dashboard currency converter for `EUR`, `USD`, `GBP`, and `PLN`
- Transaction history with date filtering
- Transfer requests with fee calculation: 2.5% of the amount or minimum 5 in the selected source-account currency
- Same-currency transfer support across the user's selected account
- Pending transfer review flow with manager approval and blocking
- Idempotent transfer creation support through the `Idempotency-Key` header
- Atomic final settlement with audit-friendly transaction records
- User QR code generation for receiving money
- Signed QR payloads for tamper detection
- Manager account blocking, pending transfer review, and user transaction visibility
- Director reporting for users, transactions, and bank earnings
- SQLite by default with PostgreSQL-ready configuration
- Swagger UI, ReDoc, and raw OpenAPI schema endpoints

## Local setup

### Windows PowerShell

1. Create the virtual environment:
   `python -m venv .venv`
2. If script execution is blocked in PowerShell, allow it for the current shell only:
   `Set-ExecutionPolicy -Scope Process Bypass`
3. Activate the virtual environment:
   `.\\.venv\\Scripts\\Activate.ps1`
4. Install dependencies:
   `python -m pip install --upgrade pip`
   `python -m pip install -r requirements.txt`
5. Copy the environment example:
   `Copy-Item .env.example .env`
6. Update `.env` and set a strong `SECRET_KEY` value instead of `change-me`.
   Optionally set `ENABLE_API_DOCS=true` for local API docs if you want them exposed.
7. Run migrations:
   `python manage.py migrate`
8. Optionally create demo manager and director accounts:
   `python manage.py seed_demo_roles`
9. Start the server on a safe local port:
   `python manage.py runserver 127.0.0.1:8080`

### Windows without activation

If you do not want to activate the virtual environment, use the venv Python directly:

1. Create the virtual environment:
   `python -m venv .venv`
2. Install dependencies:
   `.\\.venv\\Scripts\\python -m pip install --upgrade pip`
   `.\\.venv\\Scripts\\python -m pip install -r requirements.txt`
3. Copy the environment example:
   `Copy-Item .env.example .env`
4. Run migrations:
   `.\\.venv\\Scripts\\python manage.py migrate`
5. Optionally create demo accounts:
   `.\\.venv\\Scripts\\python manage.py seed_demo_roles`
6. Start the server:
   `.\\.venv\\Scripts\\python manage.py runserver 127.0.0.1:8080`

### Why this matters

- The project dependencies, including `drf-spectacular`, are installed in `.venv`.
- Running `python manage.py ...` with system Python can fail with `ModuleNotFoundError`.
- On some Windows setups, port `8000` may be unavailable, so `8080` is the recommended local port here.

## Quick local check

After the server starts, open:

- Web UI: `http://127.0.0.1:8080/`
- Swagger UI: `http://127.0.0.1:8080/api/docs/swagger/`
- ReDoc: `http://127.0.0.1:8080/api/docs/redoc/`
- OpenAPI schema: `http://127.0.0.1:8080/api/schema/`

## Demo accounts

After running `python manage.py seed_demo_roles`, these local demo accounts are available:

- Manager: `manager@simplebank.local`
- Director: `director@simplebank.local`
- Password: `Passw0rd!234`

Each demo user also receives four currency accounts:

- `EUR`
- `USD`
- `GBP`
- `PLN`

## API documentation

API docs are controlled by the `ENABLE_API_DOCS` setting. By default they are enabled in local debug mode.

- OpenAPI schema: `http://127.0.0.1:8080/api/schema/`
- Swagger UI: `http://127.0.0.1:8080/api/docs/swagger/`
- ReDoc: `http://127.0.0.1:8080/api/docs/redoc/`

## Default URLs

- Web UI: `http://127.0.0.1:8080/`
- Admin: `http://127.0.0.1:8080/admin/`
- API auth register: `POST /api/v1/auth/register/`
- API auth login: `POST /api/v1/auth/login/`
- API profile: `GET /api/v1/auth/me/`
- API account portfolio: `GET /api/v1/accounts/me/?currency=USD`
- API account balance: `GET /api/v1/accounts/balance/?currency=EUR`
- API currency converter: `GET /api/v1/accounts/convert/?amount=100.00&from_currency=EUR&to_currency=PLN`
- API transactions: `GET /api/v1/transactions/?from=YYYY-MM-DD&to=YYYY-MM-DD`
- API transfer request list/create: `GET|POST /api/v1/transfers/`
- API fee estimate: `GET /api/v1/transfers/fees/estimate/?amount=100.00`
- API QR: `POST /api/v1/qr/generate/`
- Manager pending transfers: `GET /api/v1/manager/transfers/pending/`
- Manager approve transfer: `POST /api/v1/manager/transfers/<id>/approve/`
- Manager block transfer: `POST /api/v1/manager/transfers/<id>/block/`
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

### Transfer request

```json
{
  "source_account_number": "1234567890",
  "destination_account_number": "1234567890",
  "amount": "150.00",
  "swift_code": "BANKDEFF",
  "reference": "Invoice #52"
}
```

### Currency conversion

```text
GET /api/v1/accounts/convert/?amount=100.00&from_currency=EUR&to_currency=USD
```

## Transfer lifecycle

1. A user creates a transfer request.
2. The user chooses the source account currency.
3. The sender's funds are reserved immediately.
4. The transfer remains in `pending` status until manager review.
5. A manager can approve the transfer, which settles balances and marks related transactions as completed.
6. A manager can block the transfer, which releases the reserved funds and marks related transactions as blocked.

## Multi-currency accounts and converter

Each user now receives four separate accounts:

- `EUR`
- `USD`
- `GBP`
- `PLN`

Current behavior:

- The `EUR` account receives the welcome bonus.
- Users can switch between their currency accounts in the web UI.
- Managers can view all user accounts with currency-specific balances.
- Directors can see currency-level dashboard reporting.
- A built-in converter is available in user, manager, and director dashboards.

Current transfer rule:

- Transfers are currently allowed only between accounts with the same currency.
- Cross-currency transfers are intentionally blocked for now.
- The converter is provided as the first multi-currency step before full FX settlement logic is introduced.

## Idempotency

The project implements idempotency for the most retry-sensitive operations.

### Transfer creation

- `POST /api/v1/transfers/` accepts an optional `Idempotency-Key` request header.
- If the same authenticated user sends the same transfer payload again with the same key, the existing transfer request is returned instead of creating a duplicate reservation.
- If the same key is reused with a different payload, the request is rejected.

Where this is implemented:

- API header handling and validation: `transactions/api.py`
- Persisted idempotency key and uniqueness rule: `transactions/models.py`
- Deduplication logic: `transactions/services.py`

### Manager review actions

- Repeating `approve` on an already approved transfer returns the same completed transfer instead of applying settlement twice.
- Repeating `block` on an already blocked transfer returns the same blocked transfer instead of releasing funds twice.

Where this is implemented:

- approval and blocking logic: `transactions/services.py`
- manager action endpoints: `dashboard/api.py`

### Demo bootstrap

- The `seed_demo_roles` management command is idempotent. Running it multiple times does not create duplicate demo users.

Where this is implemented:

- `users/management/commands/seed_demo_roles.py`

## Transaction integrity and ACID note

The current implementation is designed for strong transactional safety, but it should not be described as full banking-grade ACID on the default SQLite setup.

What is implemented today:

- Atomicity: user creation, account creation, transfer request creation, transfer approval, and transfer blocking are wrapped in `transaction.atomic()` blocks.
- Consistency: balances, fees, transfer states, and transaction records are validated and updated together inside the same transactional workflow.
- Isolation intent: transfer workflows use `select_for_update()` to lock the involved accounts and the pending transfer during approval or blocking.
- Durability: committed changes are persisted by the underlying database engine.

Important limitation:

- The project uses SQLite by default for local development, and SQLite does not provide the same row-level locking behavior as PostgreSQL for `select_for_update()`.
- Because of that, this project is best described as transaction-safe and atomic in development, with stronger ACID-style guarantees when run on PostgreSQL.

Recommendation:

- Use SQLite for local development and demos.
- Use PostgreSQL for production or any environment where stronger concurrency and isolation guarantees are required.

## REST principles followed

The API follows the main REST principles in these ways:

- Resource-oriented URLs are grouped clearly under `/api/v1/`:
  - `/auth/`
  - `/accounts/`
  - `/transactions/`
  - `/transfers/`
  - `/manager/`
  - `/director/`
  - `/qr/`
- JWT bearer authentication keeps the API stateless.
- `GET` is used for reads, while `POST` is used for creation or explicit workflow transitions.
- Query parameters are used for filtering and read options, such as date ranges and status filters.
- Responses use standard HTTP status codes such as `200`, `201`, `400`, `401`, and `403`.
- API payloads are JSON and are described through OpenAPI / Swagger.
- The API is versioned under `/api/v1/` to support future evolution without breaking existing clients.

Notes:

- The approve and block transfer endpoints are modeled as `POST` action routes because they represent business workflow transitions rather than plain CRUD field updates.
- There is some intentional overlap between `/accounts/me/` and `/accounts/balance/`: one returns the fuller portfolio-oriented resource, while the other is a lightweight balance-focused response for a selected currency account.

## Roles

- `user`: can view balances, reserved funds, multiple currency accounts, transfer requests, QR requests, personal transaction reports, and the dashboard converter.
- `manager`: can inspect user transaction history, create user accounts through the API, review pending transfers, approve or block transfers, block accounts, and review user accounts across currencies.
- `director`: can view aggregate KPIs about users, transactions, bank fee earnings, and currency-level dashboard breakdowns.

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

`python -m pytest`

If you are not activating the virtual environment, use:

`.\\.venv\\Scripts\\python -m pytest`

## Performance tests

A load-test scaffold is included in `performance/locustfile.py`.
Run it with:

`locust -f performance/locustfile.py`

## Notes

- Money values use `Decimal`.
- Transfer fees are recognized as bank earnings only after approval.
- Pending transfers reserve sender funds before final settlement.
- The system creates one account per supported currency for each user.
- Cross-currency transfers are not yet enabled; the converter is currently read-only and informational.
- For local Windows development, prefer the project virtual environment and port `8080`.
