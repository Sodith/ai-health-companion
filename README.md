# 🏥 AI Health Companion

> **A production-ready, full-stack AI-powered healthcare application** that enables patients to upload prescriptions, describe symptoms, and receive structured AI-generated medical analysis powered by Google Gemini.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Angular](https://img.shields.io/badge/Angular-21-DD0031?logo=angular)](https://angular.io)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql)](https://www.mysql.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docs.docker.com/compose)
[![AWS EC2](https://img.shields.io/badge/AWS-EC2-FF9900?logo=amazonaws)](https://aws.amazon.com/ec2)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://www.python.org)

---

## 📋 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Features Implemented](#3-features-implemented)
4. [Tech Stack](#4-tech-stack)
5. [System Architecture](#5-system-architecture)
6. [Project Structure](#6-project-structure)
7. [Database Schema Overview](#7-database-schema-overview)
8. [Environment Variables](#8-environment-variables)
9. [Local Development Setup](#9-local-development-setup)
10. [Docker Setup](#10-docker-setup)
11. [EC2 Deployment Runbook](#11-ec2-deployment-runbook)
12. [API Documentation](#12-api-documentation)
13. [Security Considerations](#13-security-considerations)
14. [Design Decisions](#14-design-decisions)
15. [Trade-offs](#15-trade-offs)
16. [Future Enhancements](#16-future-enhancements)
17. [Disclaimer](#17-disclaimer)
18. [Screenshots](#18-screenshots)
19. [Author Information](#19-author-information)

---

## 1. Project Overview

**AI Health Companion** is a full-stack web application that bridges the gap between patients and actionable health insights. Users can:

- Securely register and authenticate
- Upload prescription documents (PDF, JPG, PNG)
- Describe their symptoms in natural language
- Trigger AI-powered analysis via Google Gemini
- View structured results: detected diseases, prescribed medicines with dosage schedules, doctor advice, and lifestyle recommendations

The system is designed for production deployment — containerised with Docker, deployed on AWS EC2, and built following clean architecture principles that separate concerns across controllers, services, models, and schemas.

---

## 2. Problem Statement

Patients often struggle to:

1. **Understand their prescriptions** — medical jargon is inaccessible to most people
2. **Track medicine schedules** — multiple prescriptions with different dosages and frequencies
3. **Connect symptoms to diagnoses** — without waiting for a follow-up consultation

Existing solutions are either locked behind expensive subscriptions, require physical presence, or do not provide AI-driven insights. **AI Health Companion** provides a free, accessible, and intelligent bridge using state-of-the-art multimodal AI.

---

## 3. Features Implemented

| # | Feature | Status |
|---|---------|--------|
| 1 | User Registration (email + password) | ✅ Complete |
| 2 | JWT Authentication (login / logout) | ✅ Complete |
| 3 | Prescription Upload (PDF / JPG / PNG, max 10 MB) | ✅ Complete |
| 4 | Symptom Submission alongside prescription | ✅ Complete |
| 5 | Google Gemini AI Analysis (multimodal) | ✅ Complete |
| 6 | Structured AI Result: diseases, medicines, advice | ✅ Complete |
| 7 | Medicine Dosage & Schedule Extraction | ✅ Complete |
| 8 | Analysis Persistence & Idempotent Caching | ✅ Complete |
| 9 | Angular 21 SPA Frontend | ✅ Complete |
| 10 | Angular Material UI Components | ✅ Complete |
| 11 | Protected Routes (Auth Guard) | ✅ Complete |
| 12 | Dockerised 3-service Stack | ✅ Complete |
| 13 | AWS EC2 Production Deployment | ✅ Complete |
| 14 | Alembic Database Migrations | ✅ Complete |
| 15 | OpenAPI / Swagger Docs at `/docs` | ✅ Complete |

---

## 4. Tech Stack

### Backend
| Layer | Technology | Version |
|-------|-----------|---------|
| Web Framework | FastAPI | ≥ 0.115 |
| ASGI Server | Uvicorn | ≥ 0.30 |
| ORM | SQLAlchemy | ≥ 2.0 |
| Migrations | Alembic | ≥ 1.13 |
| Database Driver | PyMySQL | ≥ 1.1 |
| Auth | python-jose + bcrypt | ≥ 3.3 / ≥ 4.0 |
| Validation | Pydantic v2 | ≥ 2.7 |
| AI Integration | google-genai (Gemini) | ≥ 2.7 |
| Testing | pytest + httpx | ≥ 8.0 / ≥ 0.27 |

### Frontend
| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Angular | 21 |
| UI Library | Angular Material + CDK | 21 |
| HTTP Client | Angular HttpClient | built-in |
| Routing | Angular Router | built-in |
| Language | TypeScript | 5.x |
| Build | Angular CLI / esbuild | 21 |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Database | MySQL 8.0 |
| Container Runtime | Docker + Docker Compose |
| Reverse Proxy / Static | Nginx (inside frontend container) |
| Cloud Provider | AWS EC2 (Ubuntu 22.04 LTS) |

---

## 5. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AWS EC2 Instance                            │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Docker Compose Stack                       │  │
│  │                                                              │  │
│  │  ┌─────────────────┐   ┌─────────────────┐                  │  │
│  │  │   Frontend       │   │    Backend       │                  │  │
│  │  │  Angular 21      │   │   FastAPI        │                  │  │
│  │  │  Nginx :80       │──▶│   Uvicorn :8000  │                  │  │
│  │  └─────────────────┘   └────────┬────────┘                  │  │
│  │                                  │                            │  │
│  │                         ┌────────▼────────┐                  │  │
│  │                         │    MySQL 8.0     │                  │  │
│  │                         │    Port :3306    │                  │  │
│  │                         └─────────────────┘                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │  Google Gemini API   │
                         │  (External Service)  │
                         └─────────────────────┘
```

**Request flow:**
1. Browser → Nginx (port 80) → serves Angular SPA
2. Angular SPA → HTTP API calls → FastAPI backend (port 8000)
3. FastAPI → SQLAlchemy → MySQL 8.0
4. FastAPI → google-genai SDK → Google Gemini API
5. Gemini response → parsed → persisted → returned to frontend

---

## 6. Project Structure

```
ai-health-companion/
├── backend/
│   ├── app/
│   │   ├── controllers/        # HTTP layer — routing only, no business logic
│   │   │   ├── auth_controller.py
│   │   │   ├── prescription_controller.py
│   │   │   └── analysis_controller.py
│   │   ├── services/           # Business logic layer
│   │   │   ├── auth_service.py
│   │   │   ├── prescription_service.py
│   │   │   ├── analysis_service.py
│   │   │   └── gemini_service.py
│   │   ├── models/             # SQLAlchemy ORM models
│   │   │   ├── user_model.py
│   │   │   ├── prescription_model.py
│   │   │   ├── analysis_model.py
│   │   │   └── medicine_model.py
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── database/           # DB session and base declarative
│   │   ├── dependencies/       # FastAPI dependency injectors
│   │   ├── middleware/         # JWT auth + global exception middleware
│   │   └── utils/              # Config (pydantic-settings), logger
│   ├── alembic/                # Database migration scripts
│   ├── tests/                  # pytest test suite
│   ├── uploads/prescriptions/  # Uploaded prescription files
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/app/
│   │   ├── core/               # Guards, interceptors, services
│   │   ├── features/           # Feature modules: auth, dashboard, prescriptions, analysis
│   │   └── shared/             # Shared components and pipes
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
├── docker-compose.yml          # Local development compose
├── docker-compose.prod.yml     # Production compose override
└── README.md
```

---

## 7. Database Schema Overview

```
┌──────────────────────┐
│        users         │
├──────────────────────┤
│ id (UUID, PK)        │
│ email (UNIQUE)       │
│ password_hash        │
│ is_active            │
│ created_at           │
│ updated_at           │
└──────────┬───────────┘
           │ 1:N
┌──────────▼───────────┐
│    prescriptions     │
├──────────────────────┤
│ id (BIGINT, PK)      │
│ user_id (FK→users)   │
│ original_file_name   │
│ stored_file_name     │
│ file_path            │
│ file_type            │
│ file_size            │
│ symptoms             │
│ upload_status        │
│ created_at           │
│ updated_at           │
└──────────┬───────────┘
           │ 1:1
┌──────────▼───────────┐        ┌──────────────────────┐
│     ai_analysis      │        │      medicines        │
├──────────────────────┤        ├──────────────────────┤
│ id (BIGINT, PK)      │  1:N   │ id (BIGINT, PK)      │
│ prescription_id (FK) │───────▶│ analysis_id (FK)     │
│ disease_detected     │        │ medicine_name        │
│ doctor_advice (JSON) │        │ dosage               │
│ lifestyle_changes    │        │ frequency            │
│ raw_response         │        │ duration             │
│ analysis_status      │        │ notes                │
│ created_at           │        │ created_at           │
│ updated_at           │        │ updated_at           │
└──────────────────────┘        └──────────────────────┘
```

**Key design decisions:**
- `users.id` is a UUID string (not auto-increment) to prevent ID enumeration attacks
- `ai_analysis` has a UNIQUE constraint on `prescription_id` — enforcing one-to-one at the DB level
- `doctor_advice` and `lifestyle_changes` are stored as JSON-serialised TEXT for SQLite/MySQL portability
- `raw_response` stores the complete Gemini output for audit purposes, never exposed via API

---

## 8. Environment Variables

Create `backend/.env` with the following:

```dotenv
# ── Application ──────────────────────────────────────────────────────────────
APP_NAME=AI Health Companion API
APP_ENV=production          # development | production
APP_DEBUG=false

HOST=0.0.0.0
PORT=8000

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL=mysql+pymysql://ai_health_user:strongpassword@localhost:3306/ai_health_db

# Docker Compose uses these to initialise the MySQL container
MYSQL_ROOT_PASSWORD=strongrootpassword
MYSQL_DATABASE=ai_health_db
MYSQL_USER=ai_health_user
MYSQL_PASSWORD=strongpassword
MYSQL_PORT=3306

# ── JWT ───────────────────────────────────────────────────────────────────────
JWT_SECRET_KEY=replace_with_64_char_random_string_generated_by_openssl
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# ── Google Gemini ─────────────────────────────────────────────────────────────
GEMINI_API_KEY=your_google_ai_studio_api_key_here

# ── CORS ─────────────────────────────────────────────────────────────────────
CORS_ORIGINS=["http://localhost","http://localhost:4200","http://YOUR_EC2_PUBLIC_IP"]

# ── Ports (used by docker-compose) ───────────────────────────────────────────
BACKEND_PORT=8000
FRONTEND_PORT=80
```

> ⚠️ **Never commit `.env` to source control.** Commit a `.env.example` template instead.

---

## 9. Local Development Setup

### Prerequisites

| Tool | Minimum Version |
|------|----------------|
| Python | 3.10+ |
| Node.js | 20+ |
| npm | 10+ |
| MySQL | 8.0 (or use Docker) |
| Git | any |

### Backend (FastAPI)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/ai-health-companion.git
cd ai-health-companion/backend

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL, JWT_SECRET_KEY, GEMINI_API_KEY

# 5. Run database migrations
alembic upgrade head

# 6. Start the development server
python main.py
# API:        http://localhost:8000
# Swagger UI: http://localhost:8000/docs
# ReDoc:      http://localhost:8000/redoc
```

### Frontend (Angular)

```bash
cd ai-health-companion/frontend

# 1. Install dependencies
npm install

# 2. Start dev server (proxies API calls to localhost:8000)
npm start
# App available at: http://localhost:4200
```

### Running Tests

```bash
# Backend unit and integration tests
cd backend
pytest tests/ -v

# Frontend unit tests
cd frontend
npm test
```

---

## 10. Docker Setup

### Quick Start (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/ai-health-companion.git
cd ai-health-companion

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env — set GEMINI_API_KEY and JWT_SECRET_KEY at minimum

# 3. Build and start all three services
docker compose up -d --build

# 4. Run database migrations (first run only)
docker compose exec backend alembic upgrade head

# 5. Verify all services are healthy
docker compose ps
```

**Services after startup:**

| Service | URL |
|---------|-----|
| Frontend (Angular + Nginx) | http://localhost |
| Backend (FastAPI) | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| MySQL | localhost:3306 (internal only) |

### Useful Docker Commands

```bash
# Stream logs from a service
docker compose logs -f backend
docker compose logs -f frontend

# Stop all services (preserves volumes)
docker compose down

# Stop and wipe all data
docker compose down -v

# Rebuild a single service after code changes
docker compose up -d --build backend

# Run migrations
docker compose exec backend alembic upgrade head

# Open a shell in a container
docker compose exec backend bash
```

---

## 11. EC2 Deployment Runbook

> Full step-by-step guide available in [Deployment_Runbook.md](./Deployment_Runbook.md)

### Summary

```bash
# SSH into your EC2 instance
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP

# Install Docker (one-time setup)
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker ubuntu && newgrp docker

# Clone and configure
git clone https://github.com/YOUR_USERNAME/ai-health-companion.git
cd ai-health-companion
cp backend/.env.example backend/.env
# Edit .env with production secrets

# Deploy
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Verify
curl http://localhost:8000/health
curl http://localhost/
```

---

## 12. API Documentation

### Base URL
- **Local:** `http://localhost:8000/api/v1`
- **Production:** `http://YOUR_EC2_PUBLIC_IP:8000/api/v1`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`

### Authentication Endpoints

#### `POST /api/v1/auth/signup` — Register a new user

**Request:**
```json
{ "email": "user@example.com", "password": "SecurePassword123!" }
```

**Response `201`:**
```json
{
  "success": true,
  "message": "Account created successfully.",
  "status_code": 201,
  "data": {
    "user": { "id": "550e8400-...", "email": "user@example.com", "is_active": true },
    "access_token": "eyJhbGci..."
  }
}
```

#### `POST /api/v1/auth/login` — Authenticate user

**Response `200`:**
```json
{
  "success": true,
  "message": "Login successful.",
  "status_code": 200,
  "data": { "access_token": "eyJhbGci..." }
}
```

### Prescription Endpoints
> Require `Authorization: Bearer <token>` header.

#### `POST /api/v1/prescriptions/upload`
- **Body:** `multipart/form-data`
- `prescription_file`: File (PDF/JPG/PNG, max 10 MB)
- `symptoms`: string, optional (max 2000 chars)

#### `GET /api/v1/prescriptions` — List all prescriptions for current user
#### `GET /api/v1/prescriptions/{id}` — Get single prescription

### Analysis Endpoints
> Require `Authorization: Bearer <token>` header.

#### `POST /api/v1/analysis/{prescription_id}` — Trigger or return cached AI analysis

**Response `201`:**
```json
{
  "success": true,
  "data": {
    "id": 7,
    "prescription_id": 42,
    "disease_detected": "Hypertension, Type 2 Diabetes",
    "medicines": [
      {
        "medicine_name": "Metformin",
        "dosage": "500mg",
        "frequency": "2 times daily",
        "duration": "30 days",
        "notes": "Take after meals"
      }
    ],
    "doctor_advice": ["Monitor blood pressure daily"],
    "lifestyle_changes": ["30 minutes of walking daily"],
    "analysis_status": "completed"
  }
}
```

#### `GET /api/v1/analysis/{prescription_id}` — Retrieve stored analysis

### System
#### `GET /health` → `{ "status": "ok" }`

---

## 13. Security Considerations

### Authentication & Authorisation
- Passwords hashed with **bcrypt** (work factor ≥ 12) — plaintext never stored or logged
- **JWTs** signed with HS256, expire in 60 minutes by default
- **JWT middleware** validates every request; public routes are explicitly whitelisted (`/health`, `/docs`, `/auth/*`)
- **Ownership enforcement** — prescriptions and analyses are verified to belong to the authenticated user before any operation

### Input Validation
- All request bodies validated by **Pydantic v2** with strict type coercion
- File uploads: MIME type whitelist (PDF, JPG, PNG), maximum 10 MB enforced at the service layer
- Uploaded files are stored with **UUID filenames** — original filenames are stored for display only, never used for I/O

### Infrastructure
- MySQL is on a private Docker bridge network — **never directly exposed** to the public internet
- CORS origins are explicitly enumerated — no wildcard `*` in production configuration
- HTTPS should be enforced via Nginx SSL termination or an AWS Application Load Balancer in production

### Data Handling
- `raw_response` (full Gemini output) is stored for audit but **never returned** via any API endpoint
- User UUIDs prevent sequential ID enumeration (IDOR) attacks
- Password hash is explicitly excluded from all `__repr__` methods and log output

---

## 14. Design Decisions

### Strict Layered Architecture (Controller → Service → Model)
Controllers contain zero business logic. They accept HTTP input, delegate to services, and return responses. Services are fully testable without an HTTP context.

### Pydantic v2 Settings with `@lru_cache`
`pydantic-settings` with `lru_cache` parses environment variables once per process, provides strong type validation at startup, and prevents configuration drift.

### Idempotent AI Analysis
`POST /analysis/{id}` never calls Gemini more than once for a successfully completed analysis. Cached results are returned immediately, preventing unnecessary API costs.

### UUID Primary Keys for Users
UUID string PKs (not auto-increment integers) eliminate sequential enumeration vulnerabilities common in multi-tenant applications.

### Alembic Migrations
Schema is managed through versioned Alembic scripts rather than `Base.metadata.create_all()`, providing a safe and auditable upgrade path in production.

### CORS Middleware Ordering
CORS middleware is registered last (runs first in Starlette's LIFO stack) so that OPTIONS preflight requests are handled before JWT validation, preventing spurious 401 errors on preflight.

---

## 15. Trade-offs

| Decision | Benefit | Trade-off |
|----------|---------|-----------|
| MySQL over PostgreSQL | Wide hosting support | PostgreSQL has richer JSON/full-text search |
| Stateless JWT | Horizontal scaling friendly | Token revocation requires a blocklist |
| Synchronous SQLAlchemy | Simpler codebase | Lower throughput vs. async SQLAlchemy |
| Google Gemini cloud API | No GPU needed, SOTA AI | Latency + cost dependency on external service |
| Single EC2 instance | Cost-effective | No HA; single point of failure |
| Local file storage | Zero cost | Doesn't scale horizontally; S3 needed in production |
| JSON-serialised TEXT arrays | SQLite/MySQL portable | Less queryable than native JSON columns |

---

## 16. Future Enhancements

### Near Term
- [ ] AWS S3 for prescription file storage
- [ ] Email verification on signup
- [ ] Password reset via email token
- [ ] JWT refresh token flow

### Medium Term
- [ ] Async SQLAlchemy for higher throughput
- [ ] Redis caching + rate limiting for Gemini calls
- [ ] Celery background task queue for async analysis processing
- [ ] Pagination for prescription list endpoint

### Long Term
- [ ] HTTPS with Nginx + Let's Encrypt / AWS ACM
- [ ] ECS / EKS deployment with auto-scaling
- [ ] HIPAA-adjacent audit logging
- [ ] Doctor portal for annotation and review
- [ ] Mobile client (React Native / Flutter)
- [ ] PDF report export

---

## 17. Disclaimer

> ⚠️ **This application is a technology demonstration created for educational and evaluation purposes only.**
>
> AI analysis results are generated by a general-purpose language model (Google Gemini) and **are not a substitute for professional medical advice, diagnosis, or treatment.**
>
> - Do **not** use this application to make real medical decisions
> - Always consult a qualified healthcare professional
> - The developers assume **no liability** for decisions made based on AI-generated content

---

## 18. Screenshots

> See [Screenshots.md](./Screenshots.md) for the full screenshot guide.

| Screen | File |
|--------|------|
| Login Page | `docs/screenshots/01_login.png` |
| Signup Page | `docs/screenshots/02_signup.png` |
| Dashboard | `docs/screenshots/03_dashboard.png` |
| Upload Prescription | `docs/screenshots/04_upload.png` |
| Prescription List | `docs/screenshots/05_prescription_list.png` |
| AI Analysis Result | `docs/screenshots/06_analysis_result.png` |
| Docker Containers | `docs/screenshots/07_docker_containers.png` |
| EC2 Deployment | `docs/screenshots/08_ec2_deployment.png` |
| Public URL | `docs/screenshots/09_public_url.png` |

---

## 19. Author Information

**Developer:** *[Your Full Name]*
**Role:** Full Stack / Backend Engineer
**Email:** *[your.email@example.com]*
**GitHub:** [github.com/YOUR_USERNAME](https://github.com/YOUR_USERNAME)
**LinkedIn:** [linkedin.com/in/YOUR_PROFILE](https://linkedin.com/in/YOUR_PROFILE)

### Skills Demonstrated

| Domain | Technologies |
|--------|-------------|
| Backend Engineering | FastAPI, SQLAlchemy ORM, Alembic, JWT, bcrypt, Pydantic v2 |
| AI Integration | Google Gemini multimodal API, prompt engineering, structured parsing |
| Frontend Engineering | Angular 21, Angular Material, RxJS, route guards, HTTP interceptors |
| DevOps | Docker multi-stage builds, Docker Compose, AWS EC2, Nginx |
| Engineering Practices | Clean architecture, DI, input validation, error handling, pytest |

---

*Built with ❤️ using FastAPI · Angular · Google Gemini · Docker · AWS EC2*
