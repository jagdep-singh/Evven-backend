# Evven API — Comprehensive Documentation

> **Version:** 0.0.1 · **Base URL:** `https://api.evven.xyz` · **Framework:** FastAPI / Python 3.12

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Authentication](#2-authentication)
3. [Endpoints Reference](#3-endpoints-reference)
   - [Auth](#31-auth)
   - [Users](#32-users)
   - [Groups](#33-groups)
   - [Group Members](#34-group-members)
   - [Group Expenses](#35-group-expenses)
   - [Balances](#36-balances)
   - [Settlements](#37-settlements)
   - [Debt Breakdown](#38-debt-breakdown)
   - [Personal Expenses](#39-personal-expenses)
4. [Data Models](#4-data-models)
5. [Core Engines](#5-core-engines)
6. [Response Envelope](#6-response-envelope)
7. [Error Responses](#7-error-responses)
8. [Known Bugs & Holes in the Flow](#8-known-bugs--holes-in-the-flow)

---

## 1. Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                        FastAPI App                         │
│                                                            │
│  routes/           services/          engines/             │
│  ├ auth            ├ auth_service     ├ split_engine       │
│  ├ users           ├ group_service    ├ balance_engine     │
│  ├ groups          ├ expense_service  ├ debt_breakdown_    │
│  ├ group_member    ├ balance_service    engine             │
│  ├ group_expenses  ├ settlement_      └ settlement_engine  │
│  ├ personal_         service            (empty stub)       │
│    expenses        ├ debt_breakdown_                       │
│  ├ balances          service                               │
│  ├ debt_breakdown  └ personal_                             │
│  └ settlements       expenses_service                      │
│    (EMPTY FILE)                                            │
│                                                            │
│  repository/        models/           schemas/             │
│  ├ user             ├ user            ├ auth               │
│  ├ group            ├ group           ├ user               │
│  ├ group_member     ├ group_member    ├ groups             │
│  ├ expense          ├ group_expense   ├ expense_split      │
│  ├ settlement       ├ expense_split   ├ settlement         │
│  ├ balance          ├ settlement      ├ personal_expenses  │
│  └ personal_expense ├ personal_       └ common             │
│                       expense                              │
│                     └ password_reset_                      │
│                       token                                │
└────────────────────────────────────────────────────────────┘
         │
         ▼
  PostgreSQL (asyncpg)   Redis (planned, not wired)
```

### Tech Stack

| Layer | Choice |
|---|---|
| Framework | FastAPI 0.136 |
| Language | Python 3.12 |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL via asyncpg |
| Auth | JWT — argon2 password hash, python-jose tokens |
| Migrations | Alembic |
| Email | Resend |
| Containerization | Docker + Docker Compose |

---

## 2. Authentication

### Token Strategy

The API uses two JWTs per session:

| Token | Lifetime | Sent via | Purpose |
|---|---|---|---|
| **Access token** | `ACCESS_TOKEN_EXPIRE_MINUTES` (env) | `Authorization: Bearer <token>` | Authenticate every request |
| **Refresh token** | `REFRESH_TOKEN_EXPIRE_DAYS` (env) | Request body | Obtain a new access token without re-logging in |

Both tokens carry a `type` claim (`"access"` or `"refresh"`). The `decode_token` function validates the type to prevent using a refresh token as an access token.

### Token Payload

```json
{
  "sub": "<user_uuid>",
  "exp": 1234567890,
  "type": "access"
}
```

### Protected Routes

All routes except the following require `Authorization: Bearer <access_token>`:

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET  /auth/forgot-password`
- `POST /auth/forgot-password`
- `GET  /auth/reset-password`
- `PUT  /auth/reset-password`
- `GET  /health`
- `GET  /`

---

## 3. Endpoints Reference

### Standard Response Envelope

Every successful response is wrapped in:

```json
{
  "message": "Human-readable status string",
  "data": { ... }
}
```

---

### 3.1 Auth

#### `POST /auth/register`

Creates a new local account and returns tokens immediately.

**Request body:**
```json
{
  "name": "Jagdeep Singh",
  "email": "jagdeep@example.com",
  "password": "securepassword"
}
```

**Response `201`:**
```json
{
  "message": "User created successfully",
  "user": {
    "id": "uuid",
    "user_code": "A1B2C3",
    "name": "Jagdeep Singh",
    "email": "jagdeep@example.com",
    "auth_provider": "LOCAL",
    "profile_picture": null,
    "created_at": "2026-05-11T22:47:02Z"
  },
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer"
  }
}
```

**Errors:**
- `400` — Email already registered

**Notes:**
- A random 6-character hex `user_code` (e.g. `"A1B2C3"`) is generated and guaranteed unique at registration time.
- Password is hashed with Argon2 before storage.

---

#### `POST /auth/login`

**Request body:**
```json
{
  "email": "jagdeep@example.com",
  "password": "securepassword"
}
```

**Response `200`:** Same shape as `/register`.

**Errors:**
- `401` — Invalid email or password

---

#### `GET /auth/me` 🔒

Returns the currently authenticated user.

**Response `200`:**
```json
{
  "id": "uuid",
  "user_code": "A1B2C3",
  "name": "Jagdeep Singh",
  "email": "jagdeep@example.com",
  "auth_provider": "LOCAL",
  "profile_picture": null,
  "created_at": "2026-05-11T22:47:02Z"
}
```

---

#### `POST /auth/refresh`

Exchanges a valid refresh token for a new access + refresh token pair.

**Request body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response `200`:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Errors:**
- `401` — Invalid or expired refresh token

---

#### `POST /auth/logout` 🔒

**Response `200`:**
```json
{ "message": "Logged out successfully" }
```

> ⚠️ **Hole:** This endpoint does nothing server-side. The refresh token is not invalidated. Any client holding the old refresh token can still obtain new access tokens until the refresh token naturally expires.

---

#### `GET /auth/forgot-password`

Renders the forgot-password HTML page (not a JSON API endpoint).

---

#### `POST /auth/forgot-password`

Sends a password-reset email.

**Request body:**
```json
{ "email": "jagdeep@example.com" }
```

**Response `200`:**
```json
{ "success": true, "message": "Reset email sent" }
```

**Errors:**
- `404` — No account found with that email
- `400` — Account uses Google Sign-In (cannot reset local password)
- `500` — Resend API failed

**Flow:**
1. Look up user by email.
2. Generate a 32-byte URL-safe random token, SHA-256 hash it.
3. Store the hash + expiry in `password-reset-table`.
4. Send email with `{BACKEND_URL}/auth/reset-password?token={raw_token}`.

> ⚠️ **Hole:** Token expires in **10 minutes** (hardcoded `timedelta(minutes=10)` in `auth_service.py`), but the email template says "10 minutes" and the reset HTML page says "30 minutes". Inconsistency in user-facing messaging.

> ⚠️ **Hole:** No rate limiting. Anyone can hammer this endpoint to trigger repeated email sends to any valid address.

---

#### `GET /auth/reset-password?token=<raw_token>`

Renders the password-reset HTML page.

---

#### `PUT /auth/reset-password`

Commits the new password.

**Request body:**
```json
{
  "token": "<raw_token_from_email>",
  "password": "newpassword123"
}
```

**Response `200`:**
```json
{ "message": "Password reset successfully" }
```

**Errors:**
- `400` — Token invalid, expired, or already used

**Flow:**
1. SHA-256 hash the incoming token.
2. Look up a matching, unexpired, unused record in `password-reset-table`.
3. Hash and store the new password on the user record.
4. Mark the token as `used = true`.

> ⚠️ **Hole:** `AuthRepository.delete_token` (cleans up used tokens) is defined but **never called**. Used tokens accumulate forever in `password-reset-table`.

---

### 3.2 Users

#### `GET /users/me` 🔒

Returns the current user's profile. Same shape as `GET /auth/me`.

---

#### `PUT /users/me` 🔒

Updates `name` and/or `profile_picture`.

**Request body (all fields optional):**
```json
{
  "name": "New Name",
  "profile_picture": "https://cdn.example.com/avatar.png"
}
```

**Response `200`:** Updated user object.

---

#### `DELETE /users/me` 🔒

Soft-deletes the account by setting `is_active = false`.

**Response `200`:**
```json
{ "message": "Account deactivated successfully" }
```

> ⚠️ **Hole:** This is a soft delete only. The user record and all associated data remain in the database. There is no hard-delete path and no way to reactivate from the API.

---

### 3.3 Groups

#### `POST /groups/` 🔒

Creates a group and automatically adds the creator as a member.

**Request body:**
```json
{ "name": "Goa Trip" }
```

**Response `201`:**
```json
{
  "message": "Group created successfully",
  "data": {
    "id": "uuid",
    "name": "Goa Trip",
    "created_by": "uuid",
    "created_at": "2026-05-11T22:47:02Z"
  }
}
```

---

#### `GET /groups/` 🔒

Lists all groups the current user belongs to.

**Response `200`:** Array of group objects.

> ⚠️ **Hole:** Returns `404` if the user has no groups instead of an empty array `[]`. This is a semantic bug — "no results" is not an error.

---

#### `GET /groups/{group_id}` 🔒

Returns a single group. Requires the caller to be a member.

**Errors:**
- `404` — Group not found
- `403` — Not a member

---

#### `PUT /groups/{group_id}` 🔒

Updates the group name. Only the group **creator** may do this.

**Request body:**
```json
{ "name": "Updated Name" }
```

**Errors:**
- `403` — Not the group creator

---

#### `DELETE /groups/{group_id}` 🔒

Deletes the group. Only the group **creator** may do this.

> ⚠️ **Hole:** No cascading deletes are configured at the application level. When a group is deleted, associated `group_members`, `group_expenses`, `expense_splits`, and `settlements` records are left orphaned unless PostgreSQL foreign key cascades are set (they are not in the migration scripts).

---

### 3.4 Group Members

#### `GET /groups/{group_id}/members` 🔒

Lists all members of a group. Requires the caller to be a member.

**Response `200`:**
```json
{
  "message": "List of members fetched successfully",
  "data": [
    {
      "id": "uuid",
      "group_id": "uuid",
      "user_id": "uuid",
      "joined_at": "2026-05-11T22:47:02Z"
    }
  ]
}
```

> ⚠️ **Hole:** The `role` field (`ADMIN` / `MEMBER`) is stored in the database but is **not returned** in `GroupMemberResponse`. Roles exist at the model level but are never used to gate any action anywhere in the codebase.

---

#### `POST /groups/{group_id}/members` 🔒

Adds a user to the group by their `user_code`.

**Request body:**
```json
{ "user_code": "A1B2C3" }
```

**Response `200`:** New member object.

**Errors:**
- `403` — Caller is not a member of the group
- `400` — User already in the group
- `404` — User with that code not found (will surface as an AttributeError if `get_user_by_user_code` returns `None` — see bugs section)

> ⚠️ **Hole:** Any group member can add other users. There is no ADMIN-only gate despite the `Role` enum existing.

---

#### `DELETE /groups/{group_id}/members/{user_id}` 🔒

Removes a member from the group.

**Errors:**
- `403` — Caller is not a member
- `404` — Target user is not a member

> ⚠️ **Hole:** `has_pending_balance` in `ExpenseRepository` is defined but **never called** here. A member with outstanding debts or credits can be removed freely, leaving dangling balance data with no linked group member.

> ⚠️ **Hole:** The group creator can be removed by any other member (as long as the remover is themselves a member). There is no protection for the creator/admin role.

---

### 3.5 Group Expenses

#### `POST /groups/{group_id}/expenses` 🔒

Creates an expense and persists splits to `expense_splits`.

**Request body:**
```json
{
  "title": "Hotel Booking",
  "amount": "5000.00",
  "split_type": "equal",
  "equal_member_ids": ["uuid1", "uuid2"]
}
```

`split_type` can be `"equal"`, `"exact"`, or `"percentage"`.

**For `equal` split:**
- `equal_member_ids` — optional list of member UUIDs to split among (defaults to all group members if omitted)

**For `exact` split:**
- `splits_input` — required map of `{ user_id: amount }`, amounts must sum exactly to `amount`

**For `percentage` split:**
- `splits_input` — required map of `{ user_id: percentage }`, percentages must sum to `100`

**Response `201`:**
```json
{
  "message": "Expense created successfully",
  "data": {
    "id": "uuid",
    "group_id": "uuid",
    "paid_by": "uuid",
    "title": "Hotel Booking",
    "amount": "5000.00",
    "split_type": "equal",
    "created_at": "2026-05-11T22:47:02Z"
  }
}
```

**Errors:**
- `403` — Not a group member
- `404` — Group not found
- `400` — Split validation failure (non-members in split, totals don't match, etc.)

---

#### `GET /groups/{group_id}/expenses` 🔒

Lists all expenses for the group.

**Response `200`:** Array of expense objects.

---

#### `GET /groups/{group_id}/expenses/{expense_id}` 🔒

> ⚠️ **Critical Bug:** This route is broken at the service layer. `expense_service.get_expense` builds its response as a Python **set literal** (`{model, list}`), which is invalid (a Pydantic model is not hashable). This will raise a `TypeError` at runtime on every call.

---

#### `PUT /groups/{group_id}/expenses/{expense_id}` 🔒

Updates an expense's `title` and/or `amount`. Only the original payer may update.

**Request body (all optional):**
```json
{
  "title": "Updated Title",
  "amount": "6000.00"
}
```

> ⚠️ **Hole:** Updating `amount` does **not** recalculate or update the associated `expense_splits`. After an amount update, the splits will reflect the old amount, causing balance calculations to be wrong.

---

#### `DELETE /groups/{group_id}/expenses/{expense_id}` 🔒

Deletes the expense. Only the payer **or** the group creator may delete.

> ⚠️ **Hole:** No cascade is configured on `GroupExpense.splits`. Deleting an expense leaves all its `ExpenseSplit` rows as orphaned records in the database.

> ⚠️ **Hole:** Deleting a group expense does not delete or update the corresponding `PersonalExpense` record that may have been synced from it (the sync engine is referenced in the README but not implemented in any route handler).

---

### 3.6 Balances

> ⚠️ **Critical Hole:** `routes/balances.py` exists and is fully implemented, but it is **never registered** in `main.py`. Both balance endpoints are completely unreachable.

To fix: add to `main.py`:
```python
from routes.balances import router as balances_router
app.include_router(balances_router)
```

#### `GET /groups/{group_id}/balances` 🔒 *(currently unreachable)*

Returns the net balance for every member of the group (only non-zero balances are returned).

A **positive** value means that member is owed money overall. A **negative** value means they owe money overall.

**Response `200`:**
```json
{
  "message": "Balances fetched successfully",
  "data": {
    "uuid-alice": "350.00",
    "uuid-bob": "-350.00"
  }
}
```

> ⚠️ **Performance Hole:** `BalanceService.get_group_balances` executes **N+1 database queries** (one full balance calculation per group member). For a group of 20 members, this is 20 separate round-trips, each fetching expenses, splits, and settlements individually.

---

#### `GET /groups/{group_id}/balances/{user_id}` 🔒 *(currently unreachable)*

Returns the calling user's pairwise balance against every other member of the group.

**Response `200`:**
```json
{
  "message": "User balance fetched successfully",
  "data": {
    "uuid-alice": "200.00",
    "uuid-carol": "-150.00"
  }
}
```

---

### 3.7 Settlements

> ⚠️ **Critical Hole:** `routes/settlements.py` is an **empty file** and is **not registered** in `main.py`. The Settlement model, repository, schema, and service are all fully implemented, but there is zero API surface to reach them. The settlement feature simply does not exist at the HTTP level.

What *should* be here, based on the README, the schema, and the service:

#### `POST /groups/{group_id}/settlements` 🔒 *(not implemented)*

Records that the current user paid someone else.

**Expected request body:**
```json
{
  "receiver_id": "uuid",
  "amount": "350.00"
}
```

#### `GET /groups/{group_id}/settlements` 🔒 *(not implemented)*

Lists all settlements for the group.

**Expected response:** `SettlementListResponse` containing `settlements[]` and `total_count`.

---

### 3.8 Debt Breakdown

#### `GET /groups/{group_id}/debt-breakdown` 🔒

Returns a multi-stage breakdown of who owes whom.

> ⚠️ **Critical Bug:** `DebtBreakdownService.get_group_debt_breakdown` calls `self.expense_repository.get_group_expense_with_splits(group_id)`, but **this method does not exist** on `ExpenseRepository`. The repository has `list_by_group` (which does not eagerly load splits) and `get_splits` (takes an expense ID, not a group ID). Every call to this endpoint will raise an `AttributeError` and return a 500.

**Expected response `200` (once fixed):**
```json
{
  "message": "User debt breakdown fetched successfully",
  "data": {
    "breakdown": {
      "debtor_uuid": {
        "creditor_uuid": [
          { "expense_id": "uuid", "title": "Hotel", "amount": "1000.00" }
        ]
      }
    },
    "aggregated": {
      "debtor_uuid": { "creditor_uuid": "1000.00" }
    },
    "simplified": {
      "debtor_uuid": { "creditor_uuid": "800.00" }
    },
    "settled": {
      "debtor_uuid": { "creditor_uuid": "800.00" }
    }
  }
}
```

The four stages mean:
- **breakdown** — Per-expense debt entries (who owes whom for each specific expense)
- **aggregated** — Raw totals summed across all expenses
- **simplified** — Reverse debts cancelled against each other (if Alice owes Bob ₹500 and Bob owes Alice ₹200, simplified shows Alice owes Bob ₹300)
- **settled** — Minimum cash-flow settlement (chain simplification across multiple parties)

---

### 3.9 Personal Expenses

#### `POST /expenses/` 🔒

Creates a standalone personal expense.

**Request body:**
```json
{
  "title": "Groceries",
  "amount": "450.00",
  "category": "Food",
  "date": "2026-05-11T00:00:00Z",
  "notes": "Weekly shopping"
}
```

**Response `201`:** Created expense object.

---

#### `GET /expenses/` 🔒

Lists all personal expenses for the current user, ordered by `created_at` descending.

---

#### `GET /expenses/{expense_id}` 🔒

Returns a single personal expense.

---

#### `PUT /expenses/{expense_id}` 🔒

Updates any fields on the personal expense.

---

#### `DELETE /expenses/{expense_id}` 🔒

Deletes the personal expense.

---

#### `GET /expenses/personal-data` 🔒

> ⚠️ **Critical Bug:** This route is **unreachable**. In `routes/personal_expenses.py`, it is registered at path `/personal-data` but is declared *after* `GET /{expense_id}`. FastAPI matches routes in registration order, so any request to `/expenses/personal-data` will match `/{expense_id}` first, with `expense_id = "personal-data"` — then fail with a UUID validation error or a 404.

**Fix:** Move the `personal-data` route registration *before* `/{expense_id}`.

**Expected response `200` (once fix is applied):**
```json
{
  "message": "Personal expense analytics generated successfully",
  "data": {
    "total_spent": "4500.00",
    "expense_count": 12,
    "spending_by_category": {
      "Food": "1200.00",
      "Travel": "2500.00",
      "Uncategorized": "800.00"
    }
  }
}
```

---

## 4. Data Models

### `users`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_code` | VARCHAR | Unique 6-char hex, indexed |
| `name` | VARCHAR | |
| `email` | VARCHAR | Unique |
| `password_hash` | VARCHAR | Argon2, nullable (Google accounts have no password) |
| `google_id` | VARCHAR | Unique, nullable |
| `auth_provider` | ENUM | `LOCAL` or `GOOGLE` |
| `profile_picture` | VARCHAR | URL, nullable |
| `is_active` | BOOLEAN | Soft-delete flag |
| `created_at` | TIMESTAMP(tz) | |
| `updated_at` | TIMESTAMP(tz) | |

### `groups`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | VARCHAR | |
| `created_by` | UUID FK → users | |
| `created_at` | DATETIME | |

### `group_members`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `group_id` | UUID FK → groups | |
| `user_id` | UUID FK → users | |
| `role` | ENUM | `ADMIN` or `MEMBER` (unused in logic) |
| `joined_at` | DATETIME | |

### `group_expenses`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `group_id` | UUID FK → groups | |
| `title` | VARCHAR | |
| `amount` | NUMERIC(10,2) | |
| `paid_by` | UUID FK → users | |
| `split_type` | ENUM | `EQUAL`, `EXACT`, `PERCENTAGE` |
| `created_at` | DATETIME | |

### `expense_splits`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `expense_id` | UUID FK → group_expenses | |
| `user_id` | UUID FK → users | |
| `amount` | NUMERIC(10,2) | Each user's share |

### `settlements`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `group_id` | UUID FK → groups | |
| `payer_id` | UUID FK → users | |
| `receiver_id` | UUID FK → users | |
| `amount` | NUMERIC(10,2) | |
| `created_at` | DATETIME | |

### `personal_expenses`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `group_id` | UUID FK → groups | nullable — set when synced from a group expense |
| `group_expense_id` | UUID FK → group_expenses | nullable — tracks source |
| `title` | VARCHAR | |
| `amount` | NUMERIC(10,2) | |
| `category` | VARCHAR | nullable |
| `date` | DATETIME | nullable |
| `notes` | TEXT | nullable |
| `created_at` | DATETIME | |

### `password-reset-table`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `token_hash` | VARCHAR | SHA-256 hex of the raw token |
| `expire_at` | TIMESTAMP(tz) | 10 minutes from creation |
| `used` | BOOLEAN | Set to true after first use |

---

## 5. Core Engines

### Split Engine (`engines/split_engine.py`)

`calculate_splits(total_amount, all_members_id, split_type, splits_input, equal_member_ids)`

| `split_type` | Input | Logic |
|---|---|---|
| `equal` | optional `equal_member_ids` | `round(total / n, 2)` per member; defaults to all group members |
| `exact` | required `splits_input: {uuid: Decimal}` | Validates sum == total, returns as-is |
| `percentage` | required `splits_input: {uuid: Decimal}` | Validates sum == 100, computes `round(total * pct / 100, 2)` |

All modes validate that split participants are current group members.

> ⚠️ **Precision Note:** `equal` uses simple `round(total / n, 2)`. For `₹100.00 / 3`, each person gets `₹33.33` and `₹0.01` is silently lost. There is no rounding remainder redistribution.

---

### Balance Engine (`engines/balance_engine.py`)

**`compute_raw_balance(expenses_paid, user_splits, user_id)`**

For a given user, iterates:
- All expenses they paid → sum what others owe them (positive)
- All splits they appear in → subtract what they owe others (negative)

Returns `{ other_user_id: net_amount }`. Positive = owed to you. Negative = you owe them.

**`apply_settlements(balances, payments_made, payments_received)`**

Adjusts the raw balance map by applying recorded settlements. Removes zero-balance entries.

**`compute_category_totals(expenses)`**

Aggregates personal expenses by category, plus a `"__total__"` key for the grand total.

---

### Debt Breakdown Engine (`engines/debt_breakdown_engine.py`)

Four pure functions, each building on the previous:

**1. `build_debt_breakdown(expenses)`**

Input: list of expense dicts with embedded splits.
Output: `{ debtor_id: { creditor_id: [{ expense_id, title, amount }] } }`

Each split where `split_user != paid_by` creates one debt entry.

**2. `aggregate_debt(breakdown)`**

Collapses the per-expense list into a single total:
`{ debtor_id: { creditor_id: Decimal } }`

**3. `simplify_debt(aggregated_debt)`**

Cancels reverse debts. If A→B is ₹500 and B→A is ₹200, output is A→B ₹300. Equal reverse debts cancel completely.

**4. `settle_debts(aggregated_debt)`**

Minimum cash-flow algorithm using two deques (debtors sorted by amount owed, creditors sorted by amount receivable). Chains debts through intermediaries (A→B→C becomes A→C directly). Rounds to 2 decimal places.

**5. `calculate_net_balance(aggregated_debt, user_id)`**

Returns a single `Decimal` net balance for one user across the whole map.

---

### Settlement Engine (`engines/settlement_engine.py`)

**Currently an empty file with a comment `# something goes here`.**

---

## 6. Response Envelope

```python
class SuccessResponse(BaseModel, Generic[T]):
    message: str
    data: Optional[T] = None
```

All successful route handlers return this shape. `data` can be a single object, a list, a dict, or `null` (for delete operations).

```python
class ErrorResponse(BaseModel):
    detail: str
```

FastAPI's default `HTTPException` uses the `detail` field.

---

## 7. Error Responses

| HTTP Code | When Used |
|---|---|
| `400` | Validation failure, duplicate registration, bad split inputs |
| `401` | Missing, invalid, or expired token; wrong password |
| `403` | Authenticated but not authorized (not a member, not the creator/payer) |
| `404` | Resource not found |
| `422` | Pydantic validation error on request body |
| `500` | Unhandled exception (see bug list for several guaranteed 500s) |

---

## 8. Known Bugs & Holes in the Flow

This section documents every identified issue at the time of writing, ordered by severity.

---

### 🔴 Critical — Will cause 500 errors or completely broken features

---

#### BUG-01 · Balances router not registered in `main.py`

**File:** `main.py`
**Impact:** `GET /groups/{group_id}/balances` and `GET /groups/{group_id}/balances/{user_id}` return 404 for every request.
**Fix:**
```python
from routes.balances import router as balances_router
app.include_router(balances_router)
```

---

#### BUG-02 · `routes/settlements.py` is empty and not registered

**File:** `routes/settlements.py`, `main.py`
**Impact:** The entire settlements feature — recording payments, listing payment history — is completely inaccessible via the API. The model, repository, service, and schemas are fully written but never reachable.
**Fix:** Implement the routes file and register it in `main.py`:
```python
from routes.settlements import router as settlements_router
app.include_router(settlements_router)
```

---

#### BUG-03 · `get_group_expense_with_splits` method does not exist

**File:** `services/debt_breakdown_service.py:31`, `repository/expense_repository.py`
**Impact:** `GET /groups/{group_id}/debt-breakdown` always raises `AttributeError` and returns HTTP 500.
**Fix:** Add the missing method to `ExpenseRepository`:
```python
async def get_group_expense_with_splits(self, group_id: UUID) -> list[GroupExpense]:
    result = await self.session.execute(
        select(GroupExpense)
        .options(selectinload(GroupExpense.splits))
        .where(GroupExpense.group_id == group_id)
    )
    return list(result.scalars().all())
```

---

#### BUG-04 · `get_expense` returns a Python set literal

**File:** `services/expense_service.py:95`
**Impact:** `GET /groups/{group_id}/expenses/{expense_id}` always raises `TypeError: unhashable type: 'ExpenseResponse'` and returns HTTP 500.
**Current code:**
```python
data={
    ExpenseResponse.model_validate(expense),     # ← set syntax, not dict
    [ExpenseSplitResponse.model_validate(s) for s in splits],
}
```
**Fix:**
```python
data={
    "expense": ExpenseResponse.model_validate(expense),
    "splits": [ExpenseSplitResponse.model_validate(s) for s in splits],
}
```

---

#### BUG-05 · `has_pending_balance` logic is inverted

**File:** `repository/expense_repository.py:65`
**Impact:** The method returns `True` when the user has **no** pending balance and `False` when they **do**. Any caller relying on this (e.g., blocking member removal when debts exist) would do the exact opposite of the intended behavior.
**Current:**
```python
return result.scalar_one_or_none() is None   # True = no rows found = no balance
```
**Fix:**
```python
return result.scalar_one_or_none() is not None
```

---

#### BUG-06 · `/expenses/personal-data` route is unreachable

**File:** `routes/personal_expenses.py`
**Impact:** `GET /expenses/personal-data` matches the `/{expense_id}` route first. FastAPI tries to coerce `"personal-data"` as a UUID, fails with 422.
**Fix:** Move the `personal-data` route registration **above** the `/{expense_id}` route in the file.

---

#### BUG-07 · `SplitType` enum value mismatch between model and database

**File:** `models/group_expenses.py`, `alembic/versions/ebfc8f473775_add_enum_types.py`
**Impact:** The Python enum has lowercase values (`"equal"`, `"exact"`, `"percentage"`), but the PostgreSQL enum type created by Alembic has uppercase values (`EQUAL`, `EXACT`, `PERCENTAGE`). Writing a `SplitType.EQUAL` (Python value: `"equal"`) to the column will fail with a PostgreSQL invalid enum value error on insert.
**Fix:** Align the Python enum values with the DB enum:
```python
class SplitType(Enum):
    EQUAL = "EQUAL"
    EXACT = "EXACT"
    PERCENTAGE = "PERCENTAGE"
```
Or recreate the DB enum with lowercase values.

---

#### BUG-08 · `AuthProvider` enum value mismatch between model and database

**File:** `models/user.py`, `alembic/versions/d6ecfd59fc59_initial_schema.py`
**Impact:** Same class of bug as BUG-07. Python values are `"local"` / `"google"` but the Alembic migration creates `"LOCAL"` / `"GOOGLE"`.

---

#### BUG-09 · `Role` enum value mismatch between model and database

**File:** `models/group_members.py`, `alembic/versions/ebfc8f473775_add_enum_types.py`
**Impact:** Same class of bug as BUG-07. Python values are `"admin"` / `"member"` but the DB enum is `"ADMIN"` / `"MEMBER"`.

---

### 🟠 High — Significant functional gaps or data integrity issues

---

#### BUG-10 · Deleting an expense orphans its splits

**File:** `models/group_expenses.py`, `repository/expense_repository.py`
**Impact:** `DELETE /groups/{group_id}/expenses/{expense_id}` deletes the `GroupExpense` row but leaves all related `ExpenseSplit` rows in the database. These orphaned rows will skew future balance calculations.
**Fix:** Add cascade to the relationship:
```python
splits = relationship("ExpenseSplit", back_populates="expense", cascade="all, delete-orphan")
```

---

#### BUG-11 · `list_groups` returns 404 for users with zero groups

**File:** `services/group_service.py:37`
**Impact:** A brand new user who hasn't joined or created any group gets a 404 error from `GET /groups/`, which breaks any frontend that relies on this to show an empty state.
**Fix:**
```python
if not groups:
    return SuccessResponse(message="No groups found", data=[])
```

---

#### BUG-12 · Updating expense amount does not recalculate splits

**File:** `services/expense_service.py`, `repository/expense_repository.py`
**Impact:** After `PUT /groups/{group_id}/expenses/{expense_id}` changes the amount, the `expense_splits` table still holds amounts computed from the original total. Balance calculations will be based on stale split data.
**Fix:** Invalidate and recompute splits on amount change, or disallow amount updates and require delete + recreate.

---

#### BUG-13 · Member removal does not check for pending balances

**File:** `services/group_service.py:remove_member`
**Impact:** A user with outstanding debts or credits can be removed from a group. Their balance data becomes unreachable via the members list, but the underlying `expense_splits` and `settlements` rows remain, creating ghost debts.
**Fix:** Call `ExpenseRepository.has_pending_balance` (after fixing BUG-05) before removing:
```python
expense_repo = ExpenseRepository(db)
if await expense_repo.has_pending_balance(group_id, user_id):
    raise HTTPException(status_code=400, detail="User has pending balance")
```

---

#### BUG-14 · Used reset tokens are never cleaned up

**File:** `services/auth_service.py`, `repository/user_repository.py`
**Impact:** `AuthRepository.delete_token` is implemented (correctly deletes all `used=True` tokens for a user) but is never called anywhere. The `password-reset-table` grows without bound.
**Fix:** Call `await repo_auth.delete_token(user.id)` at the end of `reset_password`.

---

#### BUG-15 · `logout` does not invalidate the refresh token

**File:** `routes/auth.py`, `services/auth_service.py`
**Impact:** After logout, a client retaining the refresh token can silently re-acquire new access tokens indefinitely. There is no server-side session revocation.
**Fix:** Store refresh tokens in the database (or Redis) and mark them as revoked on logout. The `POST /auth/refresh` endpoint should verify the token has not been revoked.

---

### 🟡 Medium — Missing features or notable gaps

---

#### BUG-16 · Google OAuth schema exists but no route

**File:** `schemas/user.py:GoogleAuthRequest`
**Impact:** `GoogleAuthRequest` is defined with a `token: str` field, and `AuthProvider.GOOGLE` is a valid enum value, but there is no `POST /auth/google` route. Google sign-in cannot be used.

---

#### BUG-17 · `BalanceService.aggregate_totals` is never exposed

**File:** `services/balance_service.py:aggregate_totals`
**Impact:** Category-level spending totals for the current user can be computed but there is no endpoint to retrieve them.

---

#### BUG-18 · N+1 queries in `get_group_balances`

**File:** `services/balance_service.py:get_group_balances`
**Impact:** For a group of N members, this method makes N separate calls to `get_user_balance_in_group`, each of which issues multiple DB queries. A group with 20 members could trigger 100+ round-trips.
**Fix:** Aggregate all expenses, splits, and settlements for the group in a single set of queries, then compute all balances in-memory.

---

#### BUG-19 · Sync engine described in README but not implemented

**File:** README, `services/auth_service.py` (comment at bottom)
**Impact:** Group expenses are supposed to be mirrored into `personal_expenses` for each involved user (via a `SyncService`). This service is listed in the README and the `PersonalExpense` model has `group_id` and `group_expense_id` foreign keys to support it, but the sync service file does not exist and no route triggers it.

---

#### BUG-20 · `add_member` does not handle user-not-found gracefully

**File:** `services/group_service.py:add_member`

**Impact:** If `user_repo.get_user_by_user_code(user_code)` returns `None`, the next line `user_id = user.id` raises `AttributeError: 'NoneType' object has no attribute 'id'`, returning an unhandled 500 instead of a clean 404.
**Fix:**
```python
user = await user_repo.get_user_by_user_code(user_code)
if not user:
    raise HTTPException(status_code=404, detail="User not found")
```

---

#### BUG-21 · No rate limiting on password reset

**File:** `routes/auth.py`, `services/auth_service.py`
**Impact:** The `POST /auth/forgot-password` endpoint has no throttle. An attacker can flood a target's inbox or exhaust Resend API quota.
**Fix:** Add rate limiting middleware (e.g., `slowapi`) keyed on IP and/or email.

---

#### BUG-22 · Password reset expiry inconsistency

**File:** `services/auth_service.py:168`, `templates/password-reset.html`
**Impact:** The token expires in 10 minutes (code), but the reset page tells users the link is valid for 30 minutes. Users will be confused when their link expires.
**Fix:** Align both to the same value and extract it to the config/env.

---

#### BUG-23 · `equal` split does not distribute rounding remainder

**File:** `engines/split_engine.py`
**Impact:** `₹100.00 / 3` assigns `₹33.33` to each of 3 members, silently discarding `₹0.01`. Over many expenses, cumulative rounding error can accumulate in balances.
**Fix:** Assign the remainder to the first (or last) member in the list:
```python
shares = [round(total_amount / len(target_ids), 2)] * len(target_ids)
remainder = total_amount - sum(shares)
shares[0] += remainder
return dict(zip(target_ids, shares))
```

---

### 🔵 Low — Code quality & minor issues

---

#### BUG-24 · `settlement_engine.py` is a stub

**File:** `engines/settlement_engine.py`
**Content:** `# something goes here`
The debt breakdown engine contains `settle_debts` itself, but a dedicated settlement engine for recording and reversing settlements was intended here.

---

#### BUG-25 · `SettlementUpdate` only allows amount changes

**File:** `schemas/settlement.py`
The schema comment says "to update receiver we delete the settlement and create new one", but there is no delete-settlement or update-settlement route implemented.

---

#### BUG-26 · `Group` deletion has no cascade at DB level

**File:** `alembic/versions/d6ecfd59fc59_initial_schema.py`
Foreign keys are created without `ON DELETE CASCADE`. Deleting a group at the DB level will fail due to FK constraints unless the application manually deletes dependents first (which it does not).

---

#### BUG-27 · `Role` field not returned in member responses

**File:** `schemas/groups.py:GroupMemberResponse`
The `role` field is stored but excluded from the response schema, making the role system invisible to API consumers.

---

#### BUG-28 · No `conftest.py` for integration tests

**File:** `tests/`
`test_full_flow.py` and `test_db.py` use `@pytest.mark.anyio` but there is no visible `conftest.py` configuring `anyio_mode = "auto"`. Tests may fail to run without it.
**Fix:** Create `tests/conftest.py`:
```python
import pytest

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
```

---

#### BUG-29 · `DELETE /users/me` doesn't clean up group memberships

**File:** `routes/users.py`
Deactivating an account only sets `is_active = false`. The user remains in all their groups, and their `group_memberships`, `expense_splits`, and `settlements` records are untouched.

---

## Quick Reference — What Actually Works End-to-End

| Feature | Status |
|---|---|
| Register / Login | ✅ Working |
| JWT access + refresh | ✅ Working |
| Password reset email flow | ✅ Working (minor expiry messaging bug) |
| Create / update / delete group | ✅ Working |
| Add / remove group members | ✅ Working (no pending-balance check) |
| Create group expense (all 3 split types) | ✅ Working |
| List group expenses | ✅ Working |
| Get single group expense | ❌ Runtime TypeError (BUG-04) |
| Update group expense | ⚠️ Works but splits not recalculated |
| Delete group expense | ⚠️ Works but splits not deleted |
| Group balances | ❌ Router not registered (BUG-01) |
| Debt breakdown | ❌ Missing repo method (BUG-03) |
| Settlements | ❌ Empty routes file (BUG-02) |
| Personal expenses CRUD | ✅ Working |
| Personal expense analytics | ❌ Route ordering bug (BUG-06) |
| Google OAuth | ❌ Not implemented |
| Expense sync to personal tracker | ❌ Not implemented |

# 9. Fixed Issues

The following issues documented during the backend audit have been resolved.

---

## 🟢 Critical Issues Fixed

### ✅ BUG-01 · Registered Balances Router

**Status:** Fixed

**Issue:**  
`routes/balances.py` existed but was never registered in the FastAPI application.

**Impact:**  
`GET /groups/{group_id}/balances` and `GET /groups/{group_id}/balances/{user_id}` returned HTTP 404.

**Resolution:**  
Registered the balances router in `main.py`.

**Result:**  
Balance endpoints are now accessible and functioning correctly.

---

### ✅ BUG-02 · Implemented Settlements API Routes

**Status:** Fixed

**Issue:**  
Settlement functionality existed but was not exposed through any API routes.

**Impact:**  
Users could not create or retrieve settlements.

**Resolution:**  
Implemented settlement routes and registered the router.

**Result:**  
Settlement recording and history retrieval are now available.

---

### ✅ BUG-03 · Fixed Debt Breakdown Endpoint Failure

**Status:** Fixed

**Issue:**  
Debt breakdown service depended on a repository method that did not exist.

**Impact:**  
`GET /groups/{group_id}/debt-breakdown` returned HTTP 500.

**Resolution:**  
Implemented the missing repository method and updated the debt breakdown workflow.

**Result:**  
Debt breakdown calculations and settlement recommendations work correctly.

---

### ✅ BUG-04 · Fixed Single Expense Retrieval Failure

**Status:** Fixed

**Issue:**  
Expense response payload was constructed using an invalid Python set.

**Impact:**  
Expense details endpoint raised runtime exceptions.

**Resolution:**  
Replaced the invalid response structure with a proper serialized object.

**Result:**  
Expense details endpoint now returns valid data.

---

### ✅ BUG-05 · Corrected Pending Balance Validation Logic

**Status:** Fixed

**Issue:**  
Pending balance validation returned the opposite of the intended result.

**Impact:**  
Outstanding balances were detected incorrectly.

**Resolution:**  
Corrected validation logic.

**Result:**  
Pending balances are now detected accurately.

---

### ✅ BUG-06 · Fixed Personal Analytics Route Conflict

**Status:** Fixed

**Issue:**  
The `/expenses/personal-data` route was shadowed by a dynamic UUID route.

**Impact:**  
Analytics endpoint was inaccessible.

**Resolution:**  
Reordered route registration.

**Result:**  
Personal analytics endpoint is now accessible.

---

### ✅ BUG-07 · Fixed SplitType Enum Mismatch

**Status:** Fixed

**Issue:**  
Python enum values did not match PostgreSQL enum values.

**Impact:**  
Expense creation failed with enum validation errors.

**Resolution:**  
Aligned enum definitions across application and database.

**Result:**  
Expense records can be stored successfully.

---

### ✅ BUG-08 · Fixed AuthProvider Enum Mismatch

**Status:** Fixed

**Issue:**  
Authentication provider enum values differed between application and database.

**Impact:**  
Authentication workflows could fail.

**Resolution:**  
Standardized enum values.

**Result:**  
Authentication records are stored consistently.

---

### ✅ BUG-09 · Fixed Role Enum Mismatch

**Status:** Fixed

**Issue:**  
Role enum values differed between application and database.

**Impact:**  
Group member creation could fail.

**Resolution:**  
Aligned enum definitions.

**Result:**  
Role management works correctly.

---

## 🟠 High Severity Issues Fixed

### ✅ BUG-10 · Fixed Orphaned Expense Splits

**Status:** Fixed

**Issue:**  
Deleting an expense left orphaned split records.

**Impact:**  
Balance calculations could become inaccurate.

**Resolution:**  
Implemented cascading cleanup for expense splits.

**Result:**  
Related split records are removed automatically.

---

### ✅ BUG-11 · Fixed Empty Group Listing Response

**Status:** Fixed

**Issue:**  
Users with no groups received HTTP 404.

**Impact:**  
Frontend applications could not distinguish empty states from errors.

**Resolution:**  
Returned an empty collection response.

**Result:**  
New users receive valid responses even without groups.

---

### ✅ BUG-12 · Fixed Expense Split Recalculation

**Status:** Fixed

**Issue:**  
Updating expense amounts did not update associated splits.

**Impact:**  
Split data became inconsistent with expense totals.

**Resolution:**  
Added split recalculation during expense updates.

**Result:**  
Expense totals and split totals remain synchronized.

---

### ✅ BUG-13 · Added Pending Balance Validation Before Member Removal

**Status:** Fixed

**Issue:**  
Members with outstanding balances could be removed from groups.

**Impact:**  
Ghost debts and inaccessible balances could be created.

**Resolution:**  
Added pending balance validation before removal.

**Result:**  
Members with unsettled balances cannot be removed.

---

### ✅ BUG-14 · Fixed Password Reset Token Cleanup

**Status:** Fixed

**Issue:**  
Used password reset tokens remained in the database.

**Impact:**  
Password reset records accumulated indefinitely.

**Resolution:**  
Added token cleanup after successful password reset.

**Result:**  
Used reset tokens are automatically removed.

---

## 🟡 Medium Severity Issues Fixed

### ✅ BUG-16 · Implemented Google Authentication Support

**Status:** Fixed

**Issue:**  
Google authentication schema existed without a supporting route.

**Impact:**  
Google sign-in functionality could not be used.

**Resolution:**  
Implemented Google OAuth authentication workflow and route handling.

**Result:**  
Users can authenticate using Google accounts.

---

### ✅ BUG-17 · Exposed Aggregate Spending Totals

**Status:** Fixed

**Issue:**  
Aggregate spending calculations existed but were not accessible through the API.

**Impact:**  
Clients could not retrieve category-level spending insights.

**Resolution:**  
Added endpoint support for aggregate spending totals.

**Result:**  
Spending analytics can now be retrieved through the API.

---

### ✅ BUG-20 · Fixed Invalid User Code Error Handling

**Status:** Fixed

**Issue:**  
Invalid user codes caused unhandled exceptions.

**Impact:**  
API returned HTTP 500 instead of a meaningful error.

**Resolution:**  
Added validation before accessing user information.

**Result:**  
Invalid user codes now return appropriate API responses.

---

### ✅ BUG-22 · Fixed Password Reset Expiry Inconsistency

**Status:** Fixed

**Issue:**  
Password reset token expiry time differed from the value shown to users.

**Impact:**  
Users could be confused when reset links expired unexpectedly.

**Resolution:**  
Aligned expiry validation and displayed expiry information.

**Result:**  
Password reset behavior is consistent and predictable.

---

### ✅ BUG-23 · Fixed Equal Split Rounding Error

**Status:** Fixed

**Issue:**  
Equal split calculations discarded rounding remainders.

**Impact:**  
Split totals could differ from the original expense amount.

**Resolution:**  
Distributed rounding remainders during split calculation.

**Result:**  
Split totals always match the original expense amount.

---

## 🔵 Low Severity Issues Fixed

### ✅ BUG-24 · Implemented Settlement Engine

**Status:** Fixed

**Issue:**  
`settlement_engine.py` existed only as a placeholder.

**Impact:**  
Settlement processing logic was not centralized.

**Resolution:**  
Implemented settlement engine functionality.

**Result:**  
Settlement calculations are handled through a dedicated engine.

---

### ✅ BUG-25 · Expanded Settlement Update Functionality

**Status:** Fixed

**Issue:**  
Settlement updates only supported amount changes.

**Impact:**  
Settlement management required manual recreation.

**Resolution:**  
Added support for complete settlement management workflows.

**Result:**  
Settlements can be modified more effectively.

---

### ✅ BUG-26 · Added Group Deletion Dependency Handling

**Status:** Fixed

**Issue:**  
Foreign key dependencies were not properly handled during group deletion.

**Impact:**  
Group deletion could fail due to dependent records.

**Resolution:**  
Implemented dependency cleanup and deletion handling.

**Result:**  
Groups can be deleted safely.

---

### ✅ BUG-27 · Added Role Information to Member Responses

**Status:** Fixed

**Issue:**  
Member role information was not exposed through API responses.

**Impact:**  
Clients could not determine member permissions.

**Resolution:**  
Included role information in response schemas.

**Result:**  
Applications can correctly display member roles.

---

### ✅ BUG-28 · Added Test Configuration Support

**Status:** Fixed

**Issue:**  
The project lacked shared test configuration.

**Impact:**  
Automated test execution could fail depending on environment setup.

**Resolution:**  
Added centralized pytest and async test configuration.

**Result:**  
Tests run consistently across environments.

---

### ✅ BUG-29 · Improved User Deactivation Cleanup

**Status:** Fixed

**Issue:**  
User deactivation only disabled the account without cleaning related records.

**Impact:**  
Inactive users remained associated with groups and financial data.

**Resolution:**  
Implemented cleanup and consistency handling during account deactivation.

**Result:**  
User deactivation now correctly manages associated records and memberships.    