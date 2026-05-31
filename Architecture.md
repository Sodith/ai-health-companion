# 🏗️ AI Health Companion — Architecture Document

> **Version:** 1.0 | **Date:** May 2026 | **Author:** Engineering Team

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Frontend Architecture](#2-frontend-architecture)
3. [Backend Architecture](#3-backend-architecture)
4. [AI Integration Flow](#4-ai-integration-flow)
5. [Authentication Flow](#5-authentication-flow)
6. [Deployment Architecture](#6-deployment-architecture)
7. [Database Design](#7-database-design)
8. [File Storage Design](#8-file-storage-design)
9. [Security Design](#9-security-design)
10. [Scalability Considerations](#10-scalability-considerations)

---

## 1. High-Level Architecture

### Overview

AI Health Companion follows a **three-tier architecture** composed of a presentation tier (Angular SPA), an application tier (FastAPI), and a data tier (MySQL 8). An external AI service (Google Gemini) augments the application tier for prescription analysis.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            USER'S BROWSER                               │
│                         Angular 21 SPA (TypeScript)                     │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │  HTTP/JSON  (port 80)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION TIER                               │
│                     Nginx — Static File Server                          │
│               Serves pre-built Angular bundles                          │
│              Reverse-proxies /api/* → Backend                           │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │  HTTP/JSON  (port 8000)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION TIER                               │
│                      FastAPI + Uvicorn (Python)                         │
│                                                                         │
│   ┌────────────┐   ┌────────────┐   ┌────────────────────────────────┐ │
│   │ Auth       │   │ Prescription│   │     Analysis Controller        │ │
│   │ Controller │   │ Controller  │   │  POST /analysis/{id}           │ │
│   └─────┬──────┘   └─────┬──────┘   └───────────────┬────────────────┘ │
│         │                │                           │                  │
│   ┌─────▼──────┐   ┌─────▼──────┐   ┌───────────────▼────────────────┐ │
│   │ Auth       │   │Prescription │   │  Analysis Service              │ │
│   │ Service    │   │ Service     │   │  + Gemini Service              │ │
│   └─────┬──────┘   └─────┬──────┘   └───────────────┬────────────────┘ │
│         │                │                           │                  │
│   ┌─────▼────────────────▼───────────────────────────▼────────────────┐ │
│   │              SQLAlchemy ORM + PyMySQL                              │ │
│   └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────┬───────────────────────────────────────┘
                    ┌─────────────┴──────────────┐
                    │                            │
                    ▼                            ▼
     ┌──────────────────────┐     ┌─────────────────────────┐
     │      DATA TIER        │     │     EXTERNAL AI SERVICE  │
     │     MySQL 8.0         │     │   Google Gemini API      │
     │  (Docker container)   │     │   (Multimodal LLM)       │
     └──────────────────────┘     └─────────────────────────┘
```

### Container Topology

```
Docker Bridge Network: ai-health-network
┌─────────────────────────────────────────────────┐
│                                                 │
│   ai-health-frontend   ai-health-backend        │
│   (Nginx :80)   ──────▶ (Uvicorn :8000)         │
│                              │                  │
│                         ai-health-mysql         │
│                         (MySQL :3306)           │
│                                                 │
│   Named Volumes:                                │
│   mysql_data            prescription_uploads    │
└─────────────────────────────────────────────────┘
```

---

## 2. Frontend Architecture

### Technology: Angular 21 SPA

The frontend is a standalone **Single Page Application** built with Angular 21, using Angular Material for UI consistency and Angular's built-in Router for navigation.

### Module Structure

```
src/app/
├── core/                        # Singleton services — loaded once
│   ├── guards/
│   │   └── auth.guard.ts        # Route activation guard (JWT check)
│   ├── interceptors/
│   │   └── auth.interceptor.ts  # Attaches Bearer token to all API calls
│   └── services/
│       ├── auth.service.ts      # Login / signup / token storage
│       ├── prescription.service.ts
│       └── analysis.service.ts
│
├── features/                    # Lazy-loaded feature areas
│   ├── auth/
│   │   ├── login/               # Login page component
│   │   └── signup/              # Signup page component
│   ├── dashboard/               # Post-login landing page
│   ├── prescriptions/
│   │   ├── upload/              # File upload + symptoms form
│   │   └── list/                # Paginated prescription list
│   └── analysis/
│       └── result/              # AI analysis result display
│
└── shared/                      # Reusable UI components, pipes, directives
```

### Data Flow (Frontend)

```
User Action
    │
    ▼
Component  ──calls──▶  Service  ──HTTP──▶  Backend API
    │                     │
    │                  RxJS Observable
    │                     │
    ▼ (subscribe)         │
Template Update  ◀────────┘
```

### Authentication State Management

- JWT stored in `localStorage` under a versioned key
- `AuthGuard` checks token presence and expiry before activating protected routes
- `HttpInterceptor` automatically appends `Authorization: Bearer <token>` to every outgoing request
- On 401 response → interceptor clears token and redirects to `/login`

### Build Pipeline

```
Angular CLI (esbuild)
    │
    ▼ ng build --configuration production
dist/frontend/browser/
    ├── index.html
    ├── main-[hash].js       (tree-shaken, minified)
    ├── styles-[hash].css
    └── assets/
    │
    ▼ (copied into)
Nginx Docker image
    └── /usr/share/nginx/html/
```

---

## 3. Backend Architecture

### Technology: FastAPI with Clean Architecture

The backend enforces a **strict three-layer architecture** where each layer has a single, well-defined responsibility.

```
HTTP Request
     │
     ▼
┌────────────────────────────────────────────────────────┐
│  LAYER 1: HTTP / Routing  (Controllers)                │
│  • Parse and validate HTTP inputs (Pydantic schemas)   │
│  • Call the correct service function                   │
│  • Wrap result in APIResponse envelope                 │
│  • Return correct HTTP status code                     │
│  ❌ No business logic  ❌ No DB access  ❌ No AI calls  │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│  LAYER 2: Business Logic  (Services)                   │
│  • Enforce business rules and ownership checks         │
│  • Coordinate between DB, file system, and AI          │
│  • Raise domain exceptions (caught by middleware)      │
│  ❌ No HTTP context  ❌ No APIResponse construction     │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│  LAYER 3: Data / ORM  (Models + SQLAlchemy Session)    │
│  • ORM model definitions                              │
│  • DB session management via dependency injection     │
│  • SQLAlchemy queries                                 │
└────────────────────────────────────────────────────────┘
```

### Request Lifecycle

```
Incoming HTTP Request
        │
        ▼
  CORSMiddleware          ← answers OPTIONS preflight
        │
        ▼
  JWTAuthMiddleware       ← validates Bearer token, injects user
        │
        ▼
  Controller (Router)     ← Pydantic validates body/params
        │
        ▼
  Service Layer           ← business logic, calls DB and/or Gemini
        │
        ▼
  SQLAlchemy Session      ← commits/rolls back transaction
        │
        ▼
  APIResponse Envelope    ← { success, message, status_code, data }
        │
        ▼
  HTTP Response           ← JSON to client
```

### Middleware Stack (LIFO order)

```
Added to app:
  1. JWTAuthMiddleware  (added first → runs second)
  2. CORSMiddleware     (added last  → runs first)

Execution order per request:
  CORSMiddleware → JWTAuthMiddleware → Route Handler
```

### Error Handling

All exceptions propagate to the global exception middleware which maps them to structured JSON responses:

```
Business Exception  →  400 / 401 / 403 / 404 / 409  (APIResponse with error details)
Unhandled Exception →  500  (generic error, no stack trace exposed)
```

### Configuration

```
pydantic-settings (BaseSettings)
    │
    ▼ reads from environment / .env file
Settings object (lru_cache — singleton per process)
    │
    ▼ injected via get_settings()
Every module that needs config
```

---

## 4. AI Integration Flow

### Gemini Service Architecture

The AI analysis pipeline uses Google's `google-genai` SDK to send multimodal prompts (prescription image/PDF + symptom text) to the Gemini model.

```
POST /api/v1/analysis/{prescription_id}
        │
        ▼
Analysis Controller
        │
        ▼
Analysis Service
  ├─ Check ownership (prescription.user_id == current_user.id)
  ├─ Check existing analysis status
  │     ├─ completed  → return cached result (HTTP 200)
  │     ├─ processing → return HTTP 409 Conflict
  │     └─ none/failed → proceed to Gemini
  │
  ├─ Set analysis_status = "processing"
  │
  ▼
Gemini Service
  ├─ Read prescription file bytes from disk
  ├─ Build multimodal prompt:
  │     ├─ SYSTEM: structured JSON extraction instructions
  │     ├─ USER:   prescription file (image/pdf bytes)
  │     └─ USER:   symptoms text (if provided)
  │
  ├─ Call google-genai SDK → Gemini model
  │
  └─ Parse JSON response:
        ├─ disease_detected
        ├─ medicines[]  (name, dosage, frequency, duration, notes)
        ├─ doctor_advice[]
        └─ lifestyle_changes[]
        │
        ▼
Analysis Service (continued)
  ├─ Persist AIAnalysis record
  ├─ Persist Medicine records (one per extracted medicine)
  ├─ Set analysis_status = "completed"
  └─ Return AnalysisResponse to controller
```

### Prompt Design

The Gemini prompt instructs the model to:
1. Act as a medical document parser
2. Extract structured data in a specified JSON schema
3. Return all fields even if empty (null-safe parsing)
4. Focus on prescription content, not general medical advice

### Idempotency Design

```
POST /analysis/{id} called N times:
  │
  ├─ 1st call → status=none   → calls Gemini → status=completed → HTTP 201
  ├─ 2nd call → status=completed → returns cached → HTTP 200
  ├─ 3rd call → status=completed → returns cached → HTTP 200
  └─ If failed → status=failed → retries Gemini → HTTP 201
```

---

## 5. Authentication Flow

### Registration (Signup)

```
Client                    Backend                      Database
  │                          │                              │
  │── POST /auth/signup ─────▶│                              │
  │   { email, password }    │                              │
  │                          │── validate email format      │
  │                          │── check email uniqueness ───▶│
  │                          │◀─ (none found) ──────────────│
  │                          │── bcrypt.hash(password)      │
  │                          │── create User record ────────▶│
  │                          │◀─ User saved ────────────────│
  │                          │── generate JWT               │
  │◀─ 201 { user, token } ───│                              │
```

### Login

```
Client                    Backend                      Database
  │                          │                              │
  │── POST /auth/login ──────▶│                              │
  │   { email, password }    │                              │
  │                          │── query User by email ───────▶│
  │                          │◀─ User record ───────────────│
  │                          │── bcrypt.verify(password)    │
  │                          │── generate JWT               │
  │◀─ 200 { access_token } ──│                              │
```

### Authenticated Request

```
Client                    JWTMiddleware              Controller
  │                            │                         │
  │── GET /prescriptions ──────▶│                         │
  │   Authorization: Bearer X  │                         │
  │                            │── decode JWT             │
  │                            │── verify expiry          │
  │                            │── verify signature       │
  │                            │── attach user to request │
  │                            │────────────────────────▶│
  │                            │                         │── service logic
  │◀───────────────────────────────────────────────── response
```

### JWT Token Structure

```
Header:  { "alg": "HS256", "typ": "JWT" }
Payload: { "sub": "<user_id>", "exp": <unix_timestamp>, "iat": <issued_at> }
Signature: HMAC-SHA256(base64(header) + "." + base64(payload), JWT_SECRET_KEY)
```

---

## 6. Deployment Architecture

### Current: Single EC2 Instance

```
Internet
    │
    ▼
AWS EC2 (Ubuntu 22.04 LTS)
  Public IP: x.x.x.x
  Security Group:
    ├─ Port 22   (SSH — restricted to admin IP)
    ├─ Port 80   (HTTP — 0.0.0.0/0)
    └─ Port 8000 (API — 0.0.0.0/0)
    │
    ▼
Docker Compose Stack
  ├─ ai-health-frontend  (Nginx :80)
  ├─ ai-health-backend   (Uvicorn :8000)
  └─ ai-health-mysql     (MySQL :3306, internal only)
```

### Deployment Pipeline (Current — Manual)

```
Developer Machine
    │
    │ git push origin main
    ▼
GitHub Repository
    │
    │ SSH
    ▼
EC2 Instance
    │
    │ git pull origin main
    ▼
Docker Compose
    │
    │ docker compose -f docker-compose.prod.yml up -d --build
    ▼
Running Containers
    │
    │ docker compose exec backend alembic upgrade head
    ▼
Database Migrations Applied
```

### Target: Production-Grade Architecture (Future)

```
Internet
    │
    ▼
Route 53 (DNS)
    │
    ▼
ACM (SSL Certificate)
    │
    ▼
Application Load Balancer (HTTPS :443)
    │
    ├─────────────────────────┐
    ▼                         ▼
ECS Service (Frontend)    ECS Service (Backend)
  2+ tasks                2+ tasks
    │                         │
    │                    RDS MySQL (Multi-AZ)
    │
S3 (Static Assets)       ElastiCache Redis (Cache)
                          S3 (Prescription Files)
```

---

## 7. Database Design

### Entity Relationship

```
users (1) ──────────────── (N) prescriptions
                                    │
                                   (1)
                                    │
                               ai_analysis
                                    │
                                   (N)
                                    │
                                medicines
```

### Table Definitions

**`users`**
```sql
CREATE TABLE users (
    id           VARCHAR(36)  PRIMARY KEY,           -- UUID
    email        VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active    TINYINT(1)  NOT NULL DEFAULT 1,
    created_at   DATETIME(6) NOT NULL DEFAULT NOW(),
    updated_at   DATETIME(6) NOT NULL DEFAULT NOW() ON UPDATE NOW()
);
```

**`prescriptions`**
```sql
CREATE TABLE prescriptions (
    id                 BIGINT       PRIMARY KEY AUTO_INCREMENT,
    user_id            VARCHAR(36)  NOT NULL,
    original_file_name VARCHAR(255) NOT NULL,
    stored_file_name   VARCHAR(255) UNIQUE NOT NULL,  -- UUID-based
    file_path          VARCHAR(500) NOT NULL,
    file_type          VARCHAR(10)  NOT NULL,          -- pdf|jpg|jpeg|png
    file_size          BIGINT       NOT NULL,          -- bytes
    symptoms           TEXT,
    upload_status      VARCHAR(20)  NOT NULL DEFAULT 'uploaded',
    created_at         DATETIME(6)  NOT NULL DEFAULT NOW(),
    updated_at         DATETIME(6)  NOT NULL DEFAULT NOW() ON UPDATE NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**`ai_analysis`**
```sql
CREATE TABLE ai_analysis (
    id                BIGINT  PRIMARY KEY AUTO_INCREMENT,
    prescription_id   BIGINT  NOT NULL,
    disease_detected  TEXT,
    doctor_advice     TEXT,               -- JSON-serialised array
    lifestyle_changes TEXT,               -- JSON-serialised array
    raw_response      LONGTEXT,           -- Full Gemini output (audit only)
    analysis_status   VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at        DATETIME(6) NOT NULL DEFAULT NOW(),
    updated_at        DATETIME(6) NOT NULL DEFAULT NOW() ON UPDATE NOW(),
    UNIQUE KEY uq_ai_analysis_prescription_id (prescription_id),
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id) ON DELETE CASCADE
);
```

**`medicines`**
```sql
CREATE TABLE medicines (
    id            BIGINT       PRIMARY KEY AUTO_INCREMENT,
    analysis_id   BIGINT       NOT NULL,
    medicine_name VARCHAR(255) NOT NULL,
    dosage        VARCHAR(100),
    frequency     VARCHAR(100),
    duration      VARCHAR(100),
    notes         TEXT,
    created_at    DATETIME(6)  NOT NULL DEFAULT NOW(),
    updated_at    DATETIME(6)  NOT NULL DEFAULT NOW() ON UPDATE NOW(),
    FOREIGN KEY (analysis_id) REFERENCES ai_analysis(id) ON DELETE CASCADE
);
```

### Migration Strategy

Managed by **Alembic** with timestamped, auto-generated migration files:

```
alembic/versions/
  20260530_1617_f29befa3f21a_create_users_table.py
  20260530_1651_e1958b089da1_create_prescriptions_table.py
  20260530_1810_3a7c912d8f45_create_ai_analysis_and_medicines_tables.py
```

---

## 8. File Storage Design

### Current Design: Local Docker Volume

```
Upload Request
    │
    ▼
prescription_service.upload_prescription()
    │
    ├─ Validate file type (PDF/JPG/PNG)
    ├─ Validate file size (≤ 10 MB)
    ├─ Generate UUID filename: <uuid4>.<ext>
    ├─ Determine storage path: uploads/prescriptions/YYYY/MM/DD/
    └─ Write bytes to Docker named volume: prescription_uploads
    
Stored path structure:
uploads/
└── prescriptions/
    └── 2026/
        └── 05/
            └── 31/
                ├── a1b2c3d4-...pdf
                └── e5f6g7h8-...jpg
```

**Security properties:**
- Original filename stored in DB only — never used for file I/O
- UUID filenames prevent path traversal and filename collisions
- Files served only after ownership verification by the backend

### Target Design: AWS S3 (Future)

```
Upload Request
    │
    ▼
prescription_service.upload_prescription()
    │
    ├─ Generate: s3://ai-health-prescriptions/{user_id}/{uuid}.{ext}
    ├─ Upload to S3 with server-side encryption (SSE-S3)
    └─ Store S3 object key in DB
    
Benefits:
  ✓ Unlimited scalable storage
  ✓ Built-in durability (11 nines)
  ✓ Works with multiple backend instances
  ✓ Pre-signed URLs for secure direct download
```

---

## 9. Security Design

### Defence in Depth

```
Layer 1: Network
  ├─ Security Group allows only ports 22, 80, 8000
  └─ MySQL port 3306 NOT exposed to internet

Layer 2: Transport
  ├─ HTTPS (target: Nginx + Let's Encrypt)
  └─ CORS whitelist — no wildcard origins

Layer 3: Authentication
  ├─ bcrypt password hashing (work factor 12)
  ├─ JWT HS256, 60-minute expiry
  └─ JWT validated by middleware on every request

Layer 4: Authorisation
  ├─ Every resource endpoint verifies ownership
  └─ No cross-user data access possible

Layer 5: Input Validation
  ├─ Pydantic v2 strict type checking on all inputs
  ├─ File type whitelist (MIME + extension)
  └─ File size enforcement (10 MB max)

Layer 6: Data
  ├─ UUID user IDs (prevent enumeration)
  ├─ UUID stored filenames (prevent path traversal)
  └─ raw_response never returned via API
```

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| Credential stuffing | bcrypt slows brute force; future: rate limiting |
| SQL injection | SQLAlchemy ORM with parameterised queries |
| XSS | Angular's built-in template escaping |
| CSRF | JWT in Authorization header (not cookies) |
| IDOR | Ownership check on every resource operation |
| Path traversal | UUID-based stored filenames |
| Token theft | Short expiry (60 min); future: refresh + rotation |
| Sensitive data exposure | password_hash excluded from repr/logs; raw_response not in API |

---

## 10. Scalability Considerations

### Current Bottlenecks

```
Single EC2 Instance
  ├─ No horizontal scaling
  ├─ Local file storage (not shared across instances)
  └─ Synchronous SQLAlchemy (blocks on I/O)

Gemini API
  ├─ Network latency (200–800ms per call)
  └─ Rate limits and quota costs
```

### Scaling Path

**Phase 1 — Vertical + Optimisation (Low effort)**
```
EC2 t3.micro → t3.medium → t3.large
Async SQLAlchemy (swap sync Session for AsyncSession)
Connection pooling (SQLAlchemy pool_size, max_overflow)
```

**Phase 2 — Horizontal Backend Scaling**
```
EC2 Auto Scaling Group
  ├─ Multiple backend instances behind ALB
  ├─ Shared state: RDS MySQL (replaces local MySQL)
  └─ Shared files: S3 (replaces local volume)
  
Redis (ElastiCache)
  ├─ Cache completed AI analysis results
  └─ Rate-limit Gemini calls per user
```

**Phase 3 — Asynchronous AI Processing**
```
POST /prescriptions/upload  → enqueue job
Celery Worker               → calls Gemini in background
Redis / SQS                 → task queue
WebSocket / polling         → notify frontend when complete
```

**Phase 4 — Containerised Orchestration**
```
AWS ECS Fargate
  ├─ Frontend tasks (auto-scaled by CPU/memory)
  ├─ Backend tasks (auto-scaled by request count)
  └─ RDS MySQL Multi-AZ (managed, failover)

Benefits: No EC2 management, auto-healing, rolling deployments
```

### Performance Targets (Future State)

| Metric | Current | Target |
|--------|---------|--------|
| API response (non-AI) | < 200ms | < 100ms |
| AI analysis latency | 2–5s (Gemini) | 2–5s (unavoidable, async) |
| Concurrent users | ~10 (single instance) | 500+ (auto-scaled) |
| Uptime | ~99% (single EC2) | 99.9% (Multi-AZ) |
| File storage | Local disk (ephemeral risk) | S3 (11 nines durability) |

---

*AI Health Companion — Architecture Document v1.0*

