# AI Business Assistant

A full-stack portfolio project: an AI assistant that answers questions about customers, sales, and orders by calling real tools (no invented numbers), and manages email draft workflows with role-based permissions.

**Live demo:** [https://khaledlajili.github.io/ai-business-assistant](https://khaledlajili.github.io/ai-business-assistant)

## Features

- Role-based access (manager, sales_rep, viewer)
- Natural language queries over a synthetic business database
- Deterministic tool results rendered as clean markdown tables
- Email draft creation, approval, and sending workflow
- Responsive dark UI
- Health endpoint for free-tier keep-alive

## Tech Stack

**Backend:** FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic, Argon2, LLM tool-calling (Groq / OpenRouter)  
**Frontend:** Angular 19 (standalone + signals), responsive CSS  
**Data:** PostgreSQL + Docker Compose

## Demo Accounts

- Manager: `manager@demo.local` / `manager123`
- Sales Rep: `sales@demo.local` / `sales123`
- Viewer: `viewer@demo.local` / `viewer123`

## Local Development

```bash
docker compose up -d
cd backend
cp ../.env.example .env   # add LLM keys + JWT secret
uv sync
uv run alembic upgrade head
uv run python -m app.seed
uv run uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
npm start
```
