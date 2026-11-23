# AI Business Assistant

A full-stack portfolio project demonstrating an AI-powered business assistant. Users can chat with an LLM agent that queries a synthetic business database (customers, orders, sales) and manages email drafts, with role-based access control.

Built with **FastAPI** (async, SQLAlchemy, Alembic), **Angular** (standalone components), and **PostgreSQL**. The agent uses tool-calling for accurate, data-grounded responses.

## Features

- Role-based authentication (manager, sales_rep, viewer)
- Natural language queries about customers, sales, and drafts
- Deterministic tool results rendered as markdown tables
- Email draft creation, approval, and sending workflow
- Responsive dark-themed UI
- Health endpoint for free-tier hosting keep-alive

## Tech Stack

**Backend**
- FastAPI + Uvicorn
- SQLAlchemy 2.0 (async) + Alembic
- Pydantic
- Argon2 password hashing
- LLM integration (Groq / OpenRouter) with tool calling

**Frontend**
- Angular 18+ (standalone components, signals)
- Responsive CSS (no external UI library)

**Infrastructure**
- PostgreSQL
- Docker Compose for local DB
- Designed for Render (or similar) free tier

## Project Structure

```
backend/          FastAPI app, agent, models, services
frontend/         Angular SPA
docker-compose.yml  Local PostgreSQL
```

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker (for Postgres)

### 1. Database

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
cp ../.env.example .env
# Edit .env with your LLM keys and JWT secret
uv sync
uv run alembic upgrade head
uv run python -m app.seed          # Load synthetic demo data
uv run uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

Open http://localhost:4200

**Demo accounts**
- Manager: `manager@demo.local` / `manager123`
- Viewer: `viewer@demo.local` / `viewer123`

## Deployment Notes (Render free tier)

The backend exposes a simple health check:

```
GET /health
→ {"status": "ok"}
```

**Keep-alive cron job**

Free instances spin down after inactivity. To keep the service warm:

1. Deploy the backend to Render (or similar).
2. On [cron-job.org](https://cron-job.org) create a job that hits:

   `https://your-backend.onrender.com/health`

   every **10–14 minutes**.

This prevents cold starts so the demo stays responsive.

Update `frontend/src/environments/environment.prod.ts` with your real backend URL before building the frontend for production.

## Agent Behavior

The assistant is constrained to answer from tool results. It never invents numbers. Supported tools include customer search, sales summaries, inactive high-value customer detection, and email draft management.

## License

Portfolio project — feel free to explore the code.
