# SimpleBank Implementation Plan

## 1. Goal

Build a banking system called `SimpleBank` with:

- A Django backend exposing a REST API.
- SQLite as the initial database.
- Database design and settings prepared so PostgreSQL can be enabled later with minimal changes.
- Authentication and automatic account creation on registration.
- Account balance, transaction history, and transfers with fees.
- A modern banking-style UI for `User`, `Manager`, and `Director` roles.
- Strong automated test coverage.
- Clear project documentation and quickstart instructions.

This plan assumes the project should deliver both:

- A standalone backend API.
- A web UI that consumes the API.

## 2. Requirements Breakdown

### Core functional requirements

1. User registration with `email + password`.
2. User login and token-based authentication.
3. Automatic account creation after registration.
4. Unique 10-digit account number generation.
5. Automatic `EUR 10,000` welcome bonus.
6. Balance endpoint for the authenticated user.
7. Transaction history endpoint with optional date filtering.
8. Money transfer endpoint between accounts.
9. Transfer fee: `2.5%` of amount, with a minimum fee of `EUR 5`.
10. Sender and receiver transactions must both be recorded.
11. Atomic balance and transaction processing.

### Extended business requirements

1. User can send money.
2. User can generate a QR code containing account number, amount, and username for receiving money.
3. User can view a nice-looking report of transactions for any date range.
4. User can send money using account number, amount, and SWIFT details.
5. Manager can:
   - View user transaction reports.
   - Create new account.
   - Block user account.
   - Block unfinished transaction.
6. Director can see reports for:
   - Number of transactions.
   - Number of users.
   - Total bank earnings from fees.

### Non-functional requirements

1. Code should be clean and well structured.
2. Use Django ORM and RESTful API design.
3. Backend must be covered with:
   - Unit tests.
   - Integration tests.
   - Performance/load tests.
4. README must explain:
   - Quickstart.
   - System overview.
   - How to run tests.

## 3. Important Clarifications To Resolve Early

The description contains a few areas that should be clarified before or during implementation. If clarification is not available, use the assumptions below.

### Assumptions

1. The backend will be built with `Django + Django REST Framework`.
2. Authentication will use token-based auth, preferably `JWT` via `djangorestframework-simplejwt`.
3. Currency will be stored as decimal values in `EUR`.
4. The UI will be server-backed but implemented separately from the API layer, likely as:
   - Django templates for fastest delivery, or
   - a separate frontend later if needed.
5. `SWIFT` support in the first version means collecting and validating a SWIFT/BIC field as transfer metadata, not connecting to external banking networks.
6. `Block unfinished transaction` means marking a transfer request as frozen before completion if the workflow later supports pending/manual-review transactions.
7. The welcome bonus is a system-generated credit transaction.

### Recommended decisions

1. Build the API first.
2. Build role-based admin/manager/director features next.
3. Build the user-facing UI after the main API is stable.
4. Implement pending transfer support only if manager blocking of unfinished transfers is required in scope `v1`; otherwise document it as phase 2.

## 4. Suggested Technical Architecture

## Backend stack

- Python
- Django
- Django REST Framework
- SQLite initially
- PostgreSQL-ready settings via environment variables
- SimpleJWT for auth tokens
- `qrcode` package for QR generation
- `pytest` + `pytest-django` or Django `TestCase`
- `locust` or `k6` for performance testing

## Suggested app structure

Create Django apps with clear responsibilities:

1. `users`
   - Custom user model
   - Role management
   - Registration and auth
2. `accounts`
   - Bank account model
   - Account creation logic
   - Blocking/activation
3. `transactions`
   - Transaction records
   - Transfer service
   - Fee calculations
   - Reports
4. `dashboard`
   - Director and manager reporting endpoints
5. `qr_payments`
   - QR payload generation
6. `core`
   - Shared utilities
   - Settings helpers
   - Common constants

## 5. Data Model Plan

### 5.1 User model

Use a custom user model from the start.

Fields:

- `id`
- `email` as unique identifier
- `password`
- `full_name`
- `role` with values such as:
  - `user`
  - `manager`
  - `director`
- `is_active`
- `created_at`
- `updated_at`

Reason:

- Avoid migration pain later.
- Support role-based access cleanly.

### 5.2 BankAccount model

Fields:

- `id`
- `user` one-to-one to user
- `account_number` unique 10-digit string
- `swift_code` optional for transfers
- `balance`
- `currency` default `EUR`
- `status`
  - `active`
  - `blocked`
- `created_at`
- `updated_at`

Rules:

- Auto-create on user registration.
- Start with `EUR 10,000` welcome bonus.
- Only active accounts can send money.

### 5.3 Transaction model

Fields:

- `id`
- `account` foreign key
- `related_account` nullable foreign key
- `type`
  - `credit`
  - `debit`
  - `fee`
  - `welcome_bonus`
- `amount`
- `fee_amount`
- `reference`
- `description`
- `status`
  - `completed`
  - `pending`
  - `blocked`
  - `failed`
- `created_at`
- `processed_at`

Rules:

- Every monetary movement must create a transaction record.
- Transfers create:
  - sender debit
  - optional fee record or fee field
  - receiver credit
- Welcome bonus creates a system credit record.

### 5.4 Optional TransferRequest model

Create this if manager review/blocking is required in version 1.

Fields:

- `id`
- `sender_account`
- `receiver_account`
- `amount`
- `fee`
- `status`
  - `pending`
  - `completed`
  - `blocked`
  - `failed`
- `requested_by`
- `approved_or_blocked_by`
- `created_at`
- `updated_at`

Reason:

- Supports unfinished transaction management.
- Keeps business flow extensible.

## 6. API Design Plan

Base path example: `/api/v1/`

### 6.1 Authentication endpoints

1. `POST /api/v1/auth/register/`
   - Input:
     - `email`
     - `password`
     - `full_name`
   - Actions:
     - Create user.
     - Create unique bank account.
     - Credit welcome bonus.
     - Return user + account summary.

2. `POST /api/v1/auth/login/`
   - Input:
     - `email`
     - `password`
   - Output:
     - access token
     - refresh token if JWT is used

3. `POST /api/v1/auth/refresh/`
   - Refresh JWT token.

4. `GET /api/v1/auth/me/`
   - Return current user profile and role.

### 6.2 Account endpoints

1. `GET /api/v1/accounts/me/`
   - Return account number, balance, status, currency.

2. `GET /api/v1/accounts/balance/`
   - Return current balance only.

3. `GET /api/v1/accounts/transactions/`
   - Query params:
     - `from`
     - `to`
     - optional `type`
     - optional `status`

4. `GET /api/v1/accounts/transactions/report/`
   - Return data optimized for UI reports.

### 6.3 Transfer endpoints

1. `POST /api/v1/transfers/`
   - Input:
     - `destination_account_number`
     - `amount`
     - optional `swift_code`
     - optional `reference`
   - Validation:
     - sender account active
     - receiver exists
     - amount > 0
     - sender has enough balance for amount + fee
     - cannot transfer to self unless explicitly allowed

2. `GET /api/v1/transfers/fees/estimate/`
   - Input:
     - `amount`
   - Output:
     - fee
     - total debit

### 6.4 QR code endpoints

1. `POST /api/v1/qr/generate/`
   - Input:
     - `amount`
     - optional `note`
   - Output:
     - QR image or QR payload
     - encoded account number
     - username/full name
     - amount

2. `GET /api/v1/qr/payload/<id>/`
   - Optional endpoint if QR payloads are persisted.

### 6.5 Manager endpoints

1. `GET /api/v1/manager/users/`
2. `GET /api/v1/manager/users/<id>/transactions/`
3. `POST /api/v1/manager/accounts/create/`
4. `POST /api/v1/manager/accounts/<id>/block/`
5. `POST /api/v1/manager/transfers/<id>/block/`

Protect all with role-based permissions.

### 6.6 Director endpoints

1. `GET /api/v1/director/reports/overview/`
   - total users
   - total transactions
   - total fee earnings

2. `GET /api/v1/director/reports/transactions/`
   - trend over period

3. `GET /api/v1/director/reports/earnings/`
   - bank revenue from fees

## 7. Security And Business Logic Rules

### Authentication and authorization

1. Only authenticated users can access protected endpoints.
2. Role-based permissions must restrict manager and director functions.
3. Use strong password validation.
4. Do not expose private account data of other users unless role permits it.

### Transfer rules

1. Use `Decimal` for all money calculations.
2. Fee formula:
   - `max(amount * 0.025, 5.00)`
3. Total debit from sender:
   - `amount + fee`
4. Receiver gets:
   - `amount`
5. Bank earnings increase by:
   - `fee`
6. All transfer operations must run inside a database transaction.
7. Use row locking where appropriate to avoid race conditions.

### Blocking rules

1. Blocked accounts cannot initiate transfers.
2. Existing history remains readable.
3. If pending transfers are implemented, managers may block them before completion.

## 8. Step-By-Step Delivery Plan

### Phase 1: Project foundation

1. Create Django project.
2. Configure virtual environment and dependency management.
3. Add Django REST Framework.
4. Add environment variable support with `.env`.
5. Configure settings for:
   - SQLite by default
   - optional PostgreSQL through env vars
6. Create a custom user model immediately.
7. Configure base apps and split project into modules.
8. Add formatting, linting, and test tools.

Deliverable:

- Project runs locally with clean structure and reusable settings.

### Phase 2: Authentication and user creation

1. Implement custom user model using email login.
2. Create registration serializer and endpoint.
3. Create login/token endpoints.
4. Add role field with default role `user`.
5. Implement user profile endpoint.
6. Add password validation and basic auth tests.

Deliverable:

- Users can register and log in.

### Phase 3: Account creation and welcome bonus

1. Create `BankAccount` model.
2. Implement unique 10-digit account number generator.
3. Create account automatically when user registers.
4. Create initial welcome bonus transaction.
5. Update account balance accordingly.
6. Add tests for:
   - uniqueness of account number
   - account auto-creation
   - initial balance = `10000.00`

Deliverable:

- New users automatically receive an account funded with the welcome bonus.

### Phase 4: Transactions and balance tracking

1. Create `Transaction` model.
2. Define transaction types and statuses.
3. Create balance retrieval endpoint.
4. Create transaction history endpoint.
5. Add date filtering on `from` and `to`.
6. Add ordering and pagination.
7. Add tests for filtering and response shape.

Deliverable:

- Users can check balance and review history.

### Phase 5: Transfer engine

1. Create fee calculation service.
2. Build transfer serializer and endpoint.
3. Validate sender account state, receiver account, and available funds.
4. Perform transfer inside a DB transaction.
5. Lock sender and receiver accounts during processing.
6. Record:
   - sender debit
   - receiver credit
   - fee effect
7. Return transfer confirmation response.
8. Add tests for:
   - normal transfer
   - minimum fee
   - percentage fee
   - insufficient funds
   - blocked sender account
   - atomic rollback on failure

Deliverable:

- Secure, auditable money transfer flow.

### Phase 6: Role-based access

1. Add permission classes for `user`, `manager`, and `director`.
2. Seed or create initial manager and director accounts.
3. Protect endpoints by role.
4. Add role-based authorization tests.

Deliverable:

- Access rules are enforced consistently.

### Phase 7: Manager features

1. Create manager user list endpoint.
2. Create manager transaction-report view for users.
3. Implement account blocking endpoint.
4. Implement manager-created account flow.
5. If included in v1, add pending transfer model and block-transfer endpoint.
6. Add tests for manager-only permissions and account blocking.

Deliverable:

- Managers can supervise accounts and review user activity.

### Phase 8: Director reporting

1. Build reporting queries for:
   - user count
   - transaction count
   - fee earnings
2. Add period-based filters where relevant.
3. Create director overview endpoints.
4. Add tests for report accuracy.

Deliverable:

- Directors can monitor business activity and earnings.

### Phase 9: QR code payment support

1. Define QR payload format.
2. Generate QR with account number, amount, and user name.
3. Decide whether QR is:
   - generated on demand only, or
   - stored and reusable
4. Add endpoint returning QR image or encoded data.
5. Add tests for payload correctness.

Deliverable:

- Users can generate payment request QR codes.

### Phase 10: Modern UI

1. Choose frontend approach:
   - Django templates for faster delivery, or
   - separate SPA if time and scope allow
2. Create design system:
   - modern banking dashboard
   - clear typography
   - card-based layout
   - rich but clean color palette
3. Implement screens for user:
   - login/register
   - dashboard with balance
   - send money
   - transaction history
   - transaction report with calendar filters
   - QR generation
4. Implement screens for manager:
   - user list
   - user reports
   - block account
   - optional pending transfer management
5. Implement screens for director:
   - KPI dashboard
   - earnings charts
   - transaction volume charts
6. Make the UI understandable and mobile-friendly.
7. Connect all UI screens to the API.

Deliverable:

- A visually polished banking web interface.

### Phase 11: Documentation

1. Write `README.md` with:
   - project purpose
   - architecture overview
   - setup instructions
   - environment variables
   - how to run server
   - how to run tests
   - API overview
2. Add sample requests and responses.
3. Document role permissions.
4. Document PostgreSQL migration path.

Deliverable:

- Project is easy to understand and run.

### Phase 12: Quality assurance

1. Add unit tests for:
   - fee calculation
   - account number generation
   - permissions
   - QR payload builder
2. Add integration tests for:
   - register flow
   - login flow
   - transfer flow
   - manager operations
   - director reports
3. Add concurrency-sensitive tests for transfers if feasible.
4. Add performance/load tests for:
   - login
   - balance fetch
   - transfer endpoint
   - report endpoints
5. Ensure test database is isolated.
6. Add CI-ready commands for automated checks.

Deliverable:

- Reliable and testable backend behavior.

## 9. Testing Strategy In Detail

### Unit tests

Focus on isolated business logic:

- fee calculation
- account number generation
- transfer validator
- permission rules
- report aggregations

### Integration tests

Focus on full API behavior:

- user registers and gets account + bonus
- user logs in and receives token
- user checks balance
- user views transactions with date filters
- user transfers money successfully
- transfer fails on low balance
- blocked account cannot transfer
- manager can block account
- director can read reports

### Performance tests

Suggested targets:

1. Concurrent logins.
2. Concurrent transfer requests.
3. Repeated report queries over large transaction sets.

Measure:

- response times
- failure rate
- DB behavior under load

## 10. Database Portability Plan

To keep migration from SQLite to PostgreSQL easy:

1. Use Django ORM everywhere.
2. Avoid raw SQL unless necessary.
3. Use `DecimalField` for money.
4. Store account number as string, not integer.
5. Keep DB configuration environment-based.
6. Test with PostgreSQL before final delivery if possible.

Example env variables:

- `DB_ENGINE`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

## 11. Proposed Milestone Order

Recommended execution sequence:

1. Foundation and settings
2. Custom user and auth
3. Account creation + welcome bonus
4. Transactions and balance APIs
5. Transfer engine with atomic logic
6. Role permissions
7. Manager features
8. Director reports
9. QR support
10. UI
11. Documentation
12. Full testing and stabilization

## 12. Definition Of Done

The project can be considered complete when:

1. A user can register, log in, and see a funded account.
2. A user can transfer money and view correct transaction history.
3. Transfer fees are calculated correctly in all cases.
4. All financial operations are atomic and auditable.
5. Manager and director permissions work correctly.
6. QR payment requests are available.
7. UI is modern, clear, and functional for all roles in scope.
8. Tests cover core backend behavior.
9. README explains setup, usage, and testing clearly.
10. The project runs on SQLite and is configurable for PostgreSQL.

## 13. Recommended First Implementation Sprint

If starting immediately, the first sprint should focus only on the minimum working backend:

1. Django project setup.
2. Custom user model.
3. Registration and login.
4. Account model.
5. Welcome bonus logic.
6. Balance endpoint.
7. Transaction history endpoint.
8. Transfer endpoint with fee and atomic processing.
9. Unit and integration tests for the above.

This creates a solid core before manager, director, UI, and QR features are added.
