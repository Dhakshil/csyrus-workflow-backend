# Csyrus Workflow — Backend

A Workflow Approval Management System backend built with **FastAPI + SQLAlchemy 2.0 + PostgreSQL**. Users sign in via Google OAuth 2.0, requesters submit approval requests, and designated reviewers approve or reject them with comments.

> Built for the Csyrus Technologies Engineering Internship Technical Assessment.

---

## Tech Stack

| Layer      | Technology                      |
| ---------- | ------------------------------- |
| Framework  | FastAPI 0.115                   |
| ORM        | SQLAlchemy 2.0                  |
| DB Driver  | psycopg 3 (PostgreSQL)          |
| Auth       | Google OAuth 2.0 (Authlib)      |
| Sessions   | JWT (python-jose)               |
| Validation | Pydantic v2 + pydantic-settings |
| Testing    | pytest + httpx                  |

---

## Project Structure

```
backend/
├── app/
│   ├── api/v1/          # Route handlers (thin layer)
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic
│   ├── repositories/    # DB access (one class per entity)
│   ├── core/            # Config, security, deps, exceptions
│   └── database/        # Engine, session factory, init script
├── tests/               # pytest suite (25 tests)
├── main.py              # App entry point
├── requirements.txt
└── pyproject.toml
```

Each layer has a single responsibility — see `ENGINEERING_DECISIONS.md` for the rationale.

---

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- A Google Cloud project with OAuth 2.0 credentials (see below)

### 1. Clone & create virtual environment

```bash
git clone https://github.com/YOUR_USERNAME/csyrus-workflow-backend.git
cd csyrus-workflow-backend
python -m venv venv
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
```

Required variables:

| Variable               | Description                                  |
| ---------------------- | -------------------------------------------- |
| `SECRET_KEY`           | Random string for JWT signing (≥32 chars)    |
| `DATABASE_URL`         | PostgreSQL connection string                 |
| `GOOGLE_CLIENT_ID`     | From Google Cloud Console                    |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console                    |
| `GOOGLE_REDIRECT_URI`  | `http://localhost:8000/auth/google/callback` |
| `FRONTEND_URL`         | `http://localhost:5173`                      |
| `TEST_DATABASE_URL`    | Separate test DB connection string           |

### 4. Set up PostgreSQL

```sql
CREATE USER csyrus_user WITH PASSWORD 'csyrus_dev_pass';
CREATE DATABASE csyrus_workflow OWNER csyrus_user;
CREATE DATABASE csyrus_workflow_test OWNER csyrus_user;
GRANT ALL PRIVILEGES ON DATABASE csyrus_workflow TO csyrus_user;
GRANT ALL PRIVILEGES ON DATABASE csyrus_workflow_test TO csyrus_user;
```

### 5. Create database tables

```bash
python -m app.database.init_db
```

### 6. Set up Google OAuth credentials

1. Go to https://console.cloud.google.com/
2. Create a project → configure OAuth consent screen (External)
3. Create OAuth client ID (Web application)
4. Add authorized redirect URI: `http://localhost:8000/auth/google/callback`
5. Copy the Client ID + Secret into your `.env`

---

## Running the app

```bash
uvicorn main:app --reload
```

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

---

## Running tests

```bash
pytest -v
```

25 tests cover:

- Auth: JWT validation, missing/invalid tokens, deleted user handling
- Requests: CRUD, ownership checks, status transition rules, validation
- Reviewer: list/filter/approve/reject, role enforcement, double-decision prevention

Tests use a real PostgreSQL test database (not SQLite or mocks) — see `ENGINEERING_DECISIONS.md` for rationale.

---

## API Reference

### Auth

| Method | Path                    | Description                       |
| ------ | ----------------------- | --------------------------------- |
| GET    | `/auth/google/login`    | Get Google OAuth consent URL      |
| GET    | `/auth/google/callback` | OAuth callback (Google → backend) |
| GET    | `/auth/me`              | Get current authenticated user    |

### Requests (Requester)

| Method | Path             | Description              |
| ------ | ---------------- | ------------------------ |
| POST   | `/requests`      | Create approval request  |
| GET    | `/requests`      | List my requests         |
| GET    | `/requests/{id}` | Get single request       |
| PUT    | `/requests/{id}` | Update (only if PENDING) |
| DELETE | `/requests/{id}` | Delete (only if PENDING) |

### Reviewer

| Method | Path                              | Description            |
| ------ | --------------------------------- | ---------------------- |
| GET    | `/reviewer/requests`              | List assigned requests |
| POST   | `/reviewer/requests/{id}/approve` | Approve with comments  |
| POST   | `/reviewer/requests/{id}/reject`  | Reject with comments   |

### Users

| Method | Path               | Description                       |
| ------ | ------------------ | --------------------------------- |
| GET    | `/users/reviewers` | List all reviewers (for dropdown) |

All endpoints except `/auth/google/login`, `/auth/google/callback`, and `/health` require a `Authorization: Bearer <jwt>` header.

---

## Architecture

See `docs/architecture.png` for the full system diagram.

Layered architecture:

```
HTTP Request → API Route → Service → Repository → Model → PostgreSQL
```

- **Routes** parse HTTP and call services. No business logic.
- **Services** contain business rules (ownership, status transitions, role checks).
- **Repositories** wrap SQLAlchemy queries. `flush()` only — services commit.
- **Models** are dumb data containers with relationships.
- **Schemas** (Pydantic) define the API contract, separate from ORM models.

---

## License

MIT
