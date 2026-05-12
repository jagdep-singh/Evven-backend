this is a very initial draft consider it as a v0.0.-1
and claude wrote it sooooo......🤞

also backend is up on 
[https://evenup-backend.onrender.com](https://evenup-backend.onrender.com)


added an uptime bot and the results are on this 
[Link](https://stats.uptimerobot.com/Fp6SnnG3zG)

# Evenup — Backend API

FastAPI backend for Evenup. Handles auth, expenses, group management, balance calculation, and debt settlement.

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Framework | FastAPI |
| Language | Python 3.11+ |
| ORM | SQLAlchemy (async) |
| Database | PostgreSQL |
| Auth | JWT (access + refresh tokens) |
| Migrations | Alembic |
| Task Queue | Celery + Redis (async jobs) |
| Containerization | Docker + Docker Compose |

---

## Project Structure

this is not the final structure and can or will be changed 

```
evenup-api/
├── main.py                     # FastAPI app init, router registration
├── config.py                   # Settings via pydantic-settings
├── database.py                 # Async SQLAlchemy engine + session
├── deps.py                     # Shared FastAPI dependencies (get_db, get_current_user)
├── alembic.ini                 # Alembic configuration
├── start.sh                    # Dev server startup script
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
│
├── routers/                    # Route handlers
│   ├── auth.py
│   ├── users.py
│   ├── personal_expenses.py
│   ├── groups.py
│   ├── group_members.py
│   ├── group_expenses.py
│   └── balances.py
│
├── services/                   # Business logic
│   ├── auth_service.py
│   ├── personal_expense_service.py
│   ├── group_service.py
│   ├── expense_service.py
│   ├── balance_service.py
│   ├── settlement_service.py
│   ├── sync_service.py
│   └── debt_breakdown_service.py
│
├── repositories/               # Database access layer
│   ├── user_repository.py
│   ├── personal_expense_repository.py
│   ├── group_repository.py
│   ├── group_member_repository.py
│   ├── expense_repository.py
│   ├── split_repository.py
│   └── settlement_repository.py
│
├── models/                     # SQLAlchemy ORM models
├── schemas/                    # Pydantic request/response schemas
│
├── engines/                    # Core computation engines
│   ├── split_engine.py
│   ├── balance_engine.py
│   ├── debt_breakdown_engine.py
│   ├── settlement_engine.py
│   └── sync_engine.py
│
├── alembic/                    # DB migrations
└── tests/
    └── test_db.py              # DB connection test
```

---

## API Routes

### Auth — `/auth`

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/auth/register` | Create account |
| `POST` | `/auth/login` | Login, returns access + refresh tokens |
| `POST` | `/auth/logout` | Invalidate session |
| `GET` | `/auth/me` | Get current user |
| `POST` | `/auth/refresh` | Rotate JWT tokens |

### Users — `/users`

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/users/me` | Get profile |
| `PUT` | `/users/me` | Update profile |
| `DELETE` | `/users/me` | Delete account |

### Personal Expenses — `/expenses`

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/expenses` | Create expense |
| `GET` | `/expenses` | List expenses (paginated) |
| `GET` | `/expenses/{expense_id}` | Get single expense |
| `PUT` | `/expenses/{expense_id}` | Update expense |
| `DELETE` | `/expenses/{expense_id}` | Delete expense |

### Groups — `/groups`

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/groups` | Create group |
| `GET` | `/groups` | List user's groups |
| `GET` | `/groups/{group_id}` | Get group detail |
| `PUT` | `/groups/{group_id}` | Update group |
| `DELETE` | `/groups/{group_id}` | Delete group |

### Group Members — `/groups/{group_id}/members`

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/groups/{group_id}/members` | List members |
| `POST` | `/groups/{group_id}/members` | Add member |
| `DELETE` | `/groups/{group_id}/members/{user_id}` | Remove member |

### Group Expenses — `/groups/{group_id}/expenses`

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/groups/{group_id}/expenses` | Create expense |
| `GET` | `/groups/{group_id}/expenses` | List expenses |
| `GET` | `/groups/{group_id}/expenses/{expense_id}` | Get expense |
| `PUT` | `/groups/{group_id}/expenses/{expense_id}` | Update expense |
| `DELETE` | `/groups/{group_id}/expenses/{expense_id}` | Delete expense |

### Balances & Settlements — `/groups/{group_id}/`

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/groups/{group_id}/balances` | All group balances |
| `GET` | `/groups/{group_id}/balances/{user_id}` | Single user's balance |
| `POST` | `/groups/{group_id}/settlements` | Record a payment |
| `GET` | `/groups/{group_id}/settlements` | List settlements |

---

## Service Layer

| Service | Responsibility |
|---------|---------------|
| `AuthService` | User creation, password hashing, JWT generation |
| `PersonalExpenseService` | CRUD + analytics + sync trigger |
| `GroupService` | Group CRUD, member management |
| `ExpenseService` | Expense creation, split calculation, edits |
| `BalanceService` | Aggregate net debts per user per group |
| `SettlementService` | Record payments, update balances, simplify debts |
| `SyncService` | Mirror group expenses into personal tracker |
| `DebtBreakdownService` | Trace a balance back to its source expenses |

---

## Database Schema

### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | VARCHAR | |
| email | VARCHAR | unique |
| password_hash | VARCHAR | bcrypt |
| created_at | TIMESTAMP | |

### `personal_expenses`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | → users |
| title | VARCHAR | |
| amount | DECIMAL | |
| category | VARCHAR | |
| date | DATE | |
| notes | TEXT | |
| group_id | UUID FK? | → groups (nullable) |
| group_expense_id | UUID FK? | → group_expenses (nullable) |

### `groups`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | VARCHAR | |
| created_by | UUID FK | → users |
| created_at | TIMESTAMP | |

### `group_members`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| group_id | UUID FK | → groups |
| user_id | UUID FK | → users |
| role | VARCHAR | `admin` / `member` |

### `group_expenses`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| group_id | UUID FK | → groups |
| title | VARCHAR | |
| amount | DECIMAL | |
| paid_by | UUID FK | → users |
| split_type | VARCHAR | `equal` / `exact` / `percentage` |
| created_at | TIMESTAMP | |

### `expense_splits`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| expense_id | UUID FK | → group_expenses |
| user_id | UUID FK | → users |
| amount | DECIMAL | |

### `settlements`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| group_id | UUID FK | → groups |
| payer_id | UUID FK | → users |
| receiver_id | UUID FK | → users |
| amount | DECIMAL | |
| created_at | TIMESTAMP | |

---

## Core Engines

| Engine | How it works |
|--------|-------------|
| **Split Engine** | Takes an expense + split_type, writes rows to `expense_splits` |
| **Balance Engine** | Sums splits minus settlements per user per group → net debt map |
| **Debt Breakdown Engine** | Walks back through expenses to show what drove each balance |
| **Settlement Engine** | Simplifies pairwise debts (min-cash-flow algo), records settlement |
| **Sync Engine** | On group expense create/update/delete, upserts corresponding `personal_expenses` row |

---

## Auth

- Access token: short-lived JWT (15 min), sent in `Authorization: Bearer` header
- Refresh token: long-lived JWT (7 days), stored server-side, rotated on use
- Logout invalidates the refresh token

---

## Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/evenup
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
REDIS_URL=redis://localhost:6379
```

---

## Getting Started

```bash
# Clone and set up virtual environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start services
docker compose up -d  # postgres + redis

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8000
```

Docs available at `http://localhost:8000/docs` (Swagger) and `/redoc`.

---

## Testing

```bash
pytest tests/ -v
```

Uses an in-memory SQLite DB for unit tests; integration tests spin up a real Postgres container via `pytest-docker`.
