# AI Health Companion - Backend

This repository is being built phase-wise.

## Current Status
- Phase 1: Authentication module
- Step 1 completed: Project structure scaffold (FastAPI MVC layout)
- Step 2 completed: Database configuration scaffold (MySQL + SQLAlchemy session setup)

## Run (scaffold check)
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/health` to verify the app starts.

## Database (MySQL)
Copy `.env.example` to `.env` and update `DATABASE_URL` for your MySQL instance.

