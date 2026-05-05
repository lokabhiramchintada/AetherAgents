# AetherAgents

Distributed agentic AI platform for deploying, managing, and monitoring AI agent applications across VM pools.

---

## What's Built

| Component | Status | Notes |
|---|---|---|
| `core/` — base classes | ✅ Done | `BaseModel`, `BaseTool`, `BaseOrchestrator`, `BaseAgent` |
| `apps/email_classifier/` — sample app | ✅ Done | Full working example app |
| `dashboard/` — React UI | ✅ Done | Login, Register, Dashboard, Deploy, AppDetail pages |
| `subsystems/user_management/` — FastAPI backend | ✅ Done | Register, login, JWT sessions, API keys, RBAC |
| `gateway/`, all other subsystems | 🔲 Pending | To be built by respective teams |

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (running locally)

---

## Setup

### 1. Database (one-time)

```bash
psql postgres -c "CREATE USER aether WITH PASSWORD 'aether_pass';"
psql postgres -c "CREATE DATABASE aetherdb OWNER aether;"
```

### 2. Environment config (one-time)

```bash
cd aether
cp .env.example .env
# Edit .env — set DATABASE_URL to your local PostgreSQL username:
# DATABASE_URL=postgresql://<your_mac_username>@localhost:5432/aetherdb
```

---

## Running the Platform

### Backend — User Management

```bash
cd aether
python -m venv .venv
source .venv/bin/activate
pip install -r subsystems/user_management/requirements.txt
python -m uvicorn subsystems.user_management.service:app --reload --port 8000
```

- API: `http://localhost:8000`
- Interactive docs (Swagger): `http://localhost:8000/docs`

### Frontend — Dashboard

```bash
cd aether/dashboard
npm install
npm run dev
```

- UI: `http://localhost:5173`

---

## User Management API

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/register` | None | Create account |
| `POST` | `/login` | None | Get JWT token |
| `GET` | `/me` | JWT or API key | Get current user profile |
| `POST` | `/api-keys` | JWT | Create API key |
| `GET` | `/api-keys` | JWT | List API keys |
| `DELETE` | `/api-keys/{id}` | JWT | Revoke API key |
| `GET` | `/health` | None | Health check |

**Auth options:**
- `Authorization: Bearer <jwt>` — for dashboard/browser sessions
- `X-API-Key: sk-ae-...` — for programmatic/CLI access

---

## Project Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for full system design, Kafka topics, VM pool schema, and subsystem responsibilities.
