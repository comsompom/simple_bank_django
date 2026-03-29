# SimpleBank Improvement Suggestions

## 1. Highest-value next steps

### 1.1 Multi-currency accounts

The model already has a `currency` field, but the transfer flow is still effectively single-currency.

Recommended next version:

- Support one account in one currency.
- Allow a user to own multiple accounts, one per currency.
- Support these currencies:
  - `EUR`
  - `USD`
  - `GBP`
  - `PLN`

Suggested rollout:

1. Add currency enum support.
2. Allow users to hold multiple accounts by currency.
3. Start with same-currency transfers only.
4. Add FX conversion only after same-currency flows are stable.

### 1.2 Currency converter

Add a shared currency conversion service and display it in:

- user dashboard
- manager dashboard
- director dashboard

Initial implementation:

- fixed rates stored in code or DB
- no external dependency required

Later upgrade:

- live rates from ECB or another FX provider
- timestamped rates
- conversion history

### 1.3 PostgreSQL-first runtime

The transactional logic is better suited to PostgreSQL than SQLite.

Recommendation:

- keep SQLite for local development
- use PostgreSQL for production and realistic testing

### 1.4 Production security hardening

Important improvements:

- require strong `SECRET_KEY`
- force `DEBUG=false` outside local development
- restrict Swagger/ReDoc in production
- enable secure cookie and HTTPS settings
- tighten JWT lifecycle policy if needed

### 1.5 Audit trail

Add an immutable audit log for:

- transfer approval
- transfer blocking
- account blocking
- manager-created accounts
- future admin-sensitive actions

## 2. Dashboard improvements

### 2.1 User dashboard

Suggested improvements:

- multi-currency wallet view
- currency switcher with flag and currency code
- embedded currency converter
- exchange history
- downloadable account statement
- richer transfer preview before submission

### 2.2 Manager dashboard

Suggested improvements:

- filter by user, currency, amount, and date
- queue grouping by currency
- suspicious activity flags
- manual FX review if cross-currency transfers are added
- exportable user transaction reports

### 2.3 Director dashboard

Suggested improvements:

- KPI breakdown by currency
- fee earnings by currency
- transaction volume by currency and date
- FX revenue reporting if conversion is introduced
- CSV / Excel export
- period-based executive reports

## 3. Multi-currency implementation approach

Recommended order:

1. Add supported currency enum:
   - `EUR`
   - `USD`
   - `GBP`
   - `PLN`
2. Add display metadata:
   - flag
   - label
   - symbol
3. Allow one user to own multiple accounts, one per currency.
4. Add dashboard account switcher by currency.
5. Add read-only converter first.
6. Enforce same-currency transfers initially.
7. Later add true FX conversion with:
   - `ExchangeRate` model
   - applied rate persistence
   - quote TTL
   - conversion fee or spread
   - source amount and target amount storage

This is safer than introducing full cross-currency transfers immediately.

## 4. Web3 ideas

### 4.1 Good first Web3 additions

- wallet connect support
- wallet ownership verification by signed message
- read-only crypto portfolio reference panel
- stablecoin activity history through a third-party provider
- statement hash anchoring for document verification

### 4.2 High-risk / large-scope Web3 ideas

- direct on-chain settlement as a core bank flow
- crypto custody
- fiat-to-crypto internal banking settlement
- smart-contract-driven banking operations

Recommended first step:

- connect wallet
- store wallet address
- verify ownership
- keep blockchain assets separate from fiat banking logic

## 5. Other important improvements

### 5.1 Notifications

Add email, SMS, or in-app notifications for:

- transfer submitted
- transfer approved
- transfer blocked
- account blocked

### 5.2 Async background jobs

Introduce Celery or RQ with Redis for:

- notifications
- exports
- scheduled reports
- heavy dashboard calculations
- future webhook delivery

### 5.3 Rate limiting and abuse protection

Continue improving rate limiting for:

- auth
- register
- transfer creation
- privileged actions

### 5.4 Two-factor authentication

Add 2FA for:

- manager accounts
- director accounts

Potential options:

- TOTP
- WebAuthn

### 5.5 Health checks and observability

Add:

- `/health/` endpoint
- DB readiness checks
- structured logs
- error monitoring like Sentry
- request tracing if needed

### 5.6 CORS policy

Needed if frontend and backend are later split across different origins.

### 5.7 Database-level protections

Add DB constraints for:

- non-negative balance
- non-negative reserved balance
- stronger business invariants where possible

### 5.8 Shared core module

Create a `core` app or module for:

- money utilities
- currency helpers
- FX helpers
- shared constants
- reusable validators

## 6. Suggested implementation order

Recommended sequence:

1. Multi-currency account model
2. Currency converter with flags
3. Same-currency transfer enforcement
4. PostgreSQL-first deployment profile
5. Security hardening and audit trail
6. Manager/director currency reporting
7. Async jobs and export pipeline
8. Optional Web3 integration

## 7. Summary recommendation

If development continues, the best next feature to implement is:

- `multi-currency accounts + converter + flags`

because it adds clear user value, fits the current dashboard-oriented product, and creates a clean path toward richer banking and reporting features later.
