# 🏥 AI Health Companion

> **Disclaimer:** This application is for informational purposes only and does **not** constitute medical advice. Always consult a qualified healthcare professional for medical decisions.

An AI-powered health companion that lets patients upload prescriptions and describe symptoms to receive structured, AI-generated health summaries — including prescribed medicines, dosage schedules, doctor's advice, and lifestyle recommendations.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Features](#3-features)
4. [Local Setup](#4-local-setup)
5. [Docker Setup](#5-docker-setup)
6. [EC2 Deployment](#6-ec2-deployment)
7. [Environment Variables](#7-environment-variables)
8. [API Documentation](#8-api-documentation)
9. [Assumptions & Trade-offs](#9-assumptions--trade-offs)
10. [Future Improvements](#10-future-improvements)

---

## 1. Project Overview

| Layer      | Technology                        |
|------------|-----------------------------------|
| Frontend   | Angular 21 served by nginx        |
| Backend    | FastAPI (Python 3.12)             |
| Database   | MySQL 8.0                         |
| AI         | Google Gemini API (free tier)     |
| Auth       | JWT (HS256, bcrypt password hash) |
| Storage    | Docker named volume (local disk)  |
| Containers | Docker + Docker Compose           |
| Deployment | AWS EC2 t2/t3.micro (Ubuntu)      |

---

## 2. Architecture

### Logical Flow

```
┌─────────────────────────────────────────────────────────────┐
│                          Internet                           │
│                             │                               │
│                    TCP :80 (HTTP)                           │
│                             │                               │
│              ┌──────────────▼──────────────┐               │
│              │   nginx  (Docker container)  │               │
│              │   • Serves Angular SPA       │               │
│              │   • Proxies /api/* → backend │               │
│              └──────────────┬──────────────┘               │
│                             │  Internal Docker network      │
│              ┌──────────────▼──────────────┐               │
│              │  FastAPI  (Docker container) │               │
│              │  • JWT Auth middleware       │               │
│              │  • Prescription upload       │               │
│              │  • Gemini AI integration     │               │
│              │  • REST API :8000            │               │
│              └──────┬───────────────┬───────┘               │
│                     │               │                       │
│         ┌───────────▼───┐   ┌───────▼────────────┐         │
│         │  MySQL 8.0    │   │  Docker Volume      │         │
│         │  (container)  │   │  prescription_      │         │
│         │  :3306        │   │  uploads            │         │
│         │  (internal    │   │  /app/uploads/      │         │
│         │   only)       │   │  prescriptions/     │         │
│         └───────────────┘   └────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### Container Network

```
ai-health-network  (Docker bridge)
  ├── ai-health-frontend   → exposes host :80
  ├── ai-health-backend    → internal :8000  (not exposed in prod)
  └── ai-health-mysql      → internal :3306  (not exposed in prod)
```

### Volumes

| Volume Name            | Mount Point (container)   | Purpose                        |
|------------------------|---------------------------|--------------------------------|
| `mysql_data`           | `/var/lib/mysql`          | Persistent MySQL data files    |
| `prescription_uploads` | `/app/uploads`            | Uploaded prescription images   |

---

## 3. Features

### ✅ Completed

| Phase | Feature                                                                 |
|-------|-------------------------------------------------------------------------|
| 1     | User signup & login with bcrypt-hashed passwords                        |
| 1     | JWT access token issuance & validation                                  |
| 1     | JWT middleware protecting all non-auth endpoints                        |
| 2     | Authenticated prescription upload (JPG / PNG / PDF)                    |
| 2     | Free-text symptom notes associated with each submission                 |
| 2     | Submissions persisted and linked to user accounts                       |
| 3     | Gemini AI analysis of prescription + symptoms                           |
| 3     | Structured response: medicines, dosage, doctor advice, lifestyle tips   |
| 3     | AI output persisted to DB (no re-calls on page load)                   |
| 3     | User-visible medical disclaimer                                         |
| 4     | Angular 21 SPA with auth, upload, and analysis views                   |
| 5     | Multi-stage Dockerfiles for backend and frontend                        |
| 5     | docker-compose.yml for local development                                |
| 6     | Production docker-compose override (no exposed MySQL/backend ports)     |
| 6     | EC2 deployment runbook & deploy script                                  |
| 6     | Automated MySQL backup script with 7-day rotation                       |
| 6     | Service health-check script                                             |

### ⏭ Skipped (Good-to-Have)

| Feature                          | Reason skipped                                      |
|----------------------------------|-----------------------------------------------------|
| Per-medicine reminder schedule   | Out of scope for initial submission timeline        |
| Dose taken / skipped tracking    | Depends on reminder feature                         |
| Email / WebSocket notifications  | Requires extra infrastructure (SMTP / Redis)        |

---

## 4. Local Setup

### Prerequisites

- Python 3.12+
- Node.js 22+
- MySQL 8 running locally **or** use Docker Compose (recommended)

### Backend (without Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — set DATABASE_URL, JWT_SECRET_KEY, GEMINI_API_KEY

alembic upgrade head
uvicorn app.main:app --reload
# API available at http://localhost:8000
# Swagger UI at  http://localhost:8000/docs
```

### Frontend (without Docker)

```bash
cd frontend
npm install --legacy-peer-deps
npx ng serve
# App available at http://localhost:4200
```

---

## 5. Docker Setup

### Quick start (local development)

```bash
# 1. Clone the repo
git clone https://github.com/<YOUR_GITHUB_USERNAME>/ai-health-companion.git
cd ai-health-companion

# 2. Create root .env
cp .env.example .env
# Edit .env — fill in MYSQL_ROOT_PASSWORD, MYSQL_PASSWORD, etc.

# 3. Create backend .env
cp backend/.env.example backend/.env
# Edit backend/.env — fill in JWT_SECRET_KEY, GEMINI_API_KEY, etc.

# 4. Start all services
docker compose up -d

# 5. Tail logs
docker compose logs -f
```

| Service  | URL                              |
|----------|----------------------------------|
| Frontend | http://localhost                 |
| Backend  | http://localhost:8000            |
| API Docs | http://localhost:8000/docs       |

### Useful commands

```bash
docker compose ps                        # service status & health
docker compose logs -f backend           # backend logs
docker compose restart backend           # restart one service
docker compose down                      # stop everything (keep volumes)
docker compose down -v                   # stop & wipe all volumes
docker compose exec mysql mysql -u root -p   # MySQL shell
```

---

## 6. EC2 Deployment

### 6.1 Provision EC2 Instance

1. Log in to the [AWS Console](https://console.aws.amazon.com/).
2. Launch a new EC2 instance:
   - **AMI**: Ubuntu Server 22.04 LTS (or 24.04 LTS)
   - **Instance type**: `t2.micro` or `t3.micro` (free tier eligible)
   - **Storage**: 20 GB gp3 (default is sufficient)
   - **Key pair**: Create or select an existing key pair — download the `.pem` file.
3. Note the **Public IPv4 address** after launch.

### 6.2 Configure Security Groups

Create (or edit) the instance's Security Group with the following **inbound rules**:

| Type        | Protocol | Port  | Source         | Purpose                         |
|-------------|----------|-------|----------------|---------------------------------|
| SSH         | TCP      | 22    | Your IP only   | Administrative access           |
| HTTP        | TCP      | 80    | 0.0.0.0/0      | Angular frontend + API proxy    |
| Custom TCP  | TCP      | 8000  | **None**       | ⛔ Do NOT expose — internal only |
| Custom TCP  | TCP      | 3306  | **None**       | ⛔ Do NOT expose — internal only |

> **Security note:** Restrict SSH (port 22) to your own IP address rather than `0.0.0.0/0` to prevent brute-force attacks.

**Outbound rules:** Allow all outbound traffic (default — needed for Docker image pulls and Gemini API calls).

### 6.3 Connect to the Instance

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
```

### 6.4 Automated Deployment (recommended)

```bash
# From your LOCAL machine — copy the deploy script to EC2 first:
scp -i your-key.pem scripts/deploy.sh ubuntu@<EC2_PUBLIC_IP>:~/

# Then SSH in and run it:
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
bash ~/deploy.sh
```

The script will:
1. Update system packages
2. Install Docker Engine + Docker Compose plugin
3. Clone the repository
4. Validate your `.env` file
5. Build images and start all services

### 6.5 Manual Deployment (step-by-step)

```bash
# ── On the EC2 instance ───────────────────────────────────────────────────

# 1. Install Docker
curl -fsSL https://get.docker.com | sudo bash
sudo usermod -aG docker $USER
newgrp docker

# 2. Clone the repository
git clone https://github.com/<YOUR_GITHUB_USERNAME>/ai-health-companion.git
cd ai-health-companion

# 3. Create and configure the root .env
cp .env.production.example .env
nano .env
# Fill in:  MYSQL_ROOT_PASSWORD, MYSQL_PASSWORD, JWT_SECRET_KEY,
#           GEMINI_API_KEY, EC2_PUBLIC_IP

# 4. Create and configure the backend .env
cp backend/.env.example backend/.env
nano backend/.env
# Fill in:  JWT_SECRET_KEY (same as root), GEMINI_API_KEY, DATABASE_URL
# DATABASE_URL should be:
#   mysql+pymysql://<MYSQL_USER>:<MYSQL_PASSWORD>@mysql:3306/<MYSQL_DATABASE>

# 5. Build images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# 6. Start services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 7. Verify health
./scripts/health-check.sh
```

### 6.6 Verify Deployment

```bash
# Check all containers are running and healthy
docker compose ps

# Expected output:
# NAME                 STATUS          PORTS
# ai-health-mysql      healthy         3306/tcp        ← internal only
# ai-health-backend    healthy         8000/tcp        ← internal only
# ai-health-frontend   healthy         0.0.0.0:80->80/tcp

# Open in browser
open http://<EC2_PUBLIC_IP>
```

### 6.7 Set Up Automated Backups (optional but recommended)

```bash
chmod +x scripts/backup.sh

# Test a manual backup
./scripts/backup.sh

# Add daily cron job at 02:00 UTC
(crontab -l 2>/dev/null; echo "0 2 * * * /home/ubuntu/ai-health-companion/scripts/backup.sh >> /var/log/ai-health-backup.log 2>&1") | crontab -
```

Backups are stored in `./backups/` as gzip-compressed SQL dumps, and the last 7 days are retained automatically.

### 6.8 Updating the Application

```bash
cd /home/ubuntu/ai-health-companion

# Pull latest code
git pull origin main

# Rebuild and restart (zero-downtime approach: build first, then swap)
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 7. Environment Variables

### Root `.env` (next to `docker-compose.yml`)

| Variable              | Required | Description                                          |
|-----------------------|----------|------------------------------------------------------|
| `MYSQL_ROOT_PASSWORD` | ✅        | MySQL root password (strong random string)          |
| `MYSQL_DATABASE`      | ✅        | Database name (e.g. `health_companion`)             |
| `MYSQL_USER`          | ✅        | Application DB user                                 |
| `MYSQL_PASSWORD`      | ✅        | Application DB user password                        |
| `MYSQL_PORT`          | ❌        | MySQL port (default: `3306`, internal use only)     |
| `BACKEND_PORT`        | ❌        | Host port for backend (default: `8000`, local only) |
| `FRONTEND_PORT`       | ❌        | Host port for frontend (default: `80`)              |
| `EC2_PUBLIC_IP`       | ✅ (prod) | EC2 public IP — used for CORS_ORIGINS               |
| `DOMAIN`              | ❌        | Custom domain name (leave blank if using bare IP)   |

### `backend/.env`

| Variable              | Required | Description                                                 |
|-----------------------|----------|-------------------------------------------------------------|
| `APP_NAME`            | ❌        | Application display name                                   |
| `APP_ENV`             | ✅        | `development` or `production`                              |
| `APP_DEBUG`           | ❌        | `true` enables Swagger UI; set `false` in production        |
| `DATABASE_URL`        | ✅        | SQLAlchemy connection string                               |
| `JWT_SECRET_KEY`      | ✅        | Secret for signing JWTs — generate with `openssl rand -hex 64` |
| `JWT_ALGORITHM`       | ❌        | Default: `HS256`                                           |
| `JWT_EXPIRE_MINUTES`  | ❌        | Token lifetime in minutes (default: `60`)                  |
| `GEMINI_API_KEY`      | ✅        | Google Gemini API key from [AI Studio](https://aistudio.google.com/app/apikey) |

**How to generate strong secrets:**
```bash
# JWT secret (64-byte hex)
openssl rand -hex 64

# MySQL passwords (32-byte base64)
openssl rand -base64 32
```

---

## 8. API Documentation

Interactive Swagger UI is available at `http://localhost:8000/docs` when `APP_DEBUG=true`.

### Base URL

```
http://<host>/api
```

### Authentication

| Method | Endpoint              | Auth | Description              |
|--------|-----------------------|------|--------------------------|
| POST   | `/api/auth/signup`    | ❌    | Register a new user      |
| POST   | `/api/auth/login`     | ❌    | Login and receive JWT    |
| GET    | `/api/auth/me`        | ✅    | Get current user profile |

### Prescriptions

| Method | Endpoint                         | Auth | Description                        |
|--------|----------------------------------|------|------------------------------------|
| POST   | `/api/prescriptions/`            | ✅    | Upload prescription + symptoms     |
| GET    | `/api/prescriptions/`            | ✅    | List all prescriptions for user    |
| GET    | `/api/prescriptions/{id}`        | ✅    | Get a single prescription          |

### AI Analysis

| Method | Endpoint                            | Auth | Description                        |
|--------|-------------------------------------|------|------------------------------------|
| POST   | `/api/analysis/{prescription_id}`   | ✅    | Trigger Gemini analysis            |
| GET    | `/api/analysis/{prescription_id}`   | ✅    | Fetch stored analysis result       |

### Health

| Method | Endpoint    | Auth | Description            |
|--------|-------------|------|------------------------|
| GET    | `/health`   | ❌    | Liveness probe         |

### Request / Response Contract (example)

**POST `/api/auth/signup`**
```json
// Request
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}

// Response 201
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2026-05-31T10:00:00Z"
}

// Error 409 (duplicate email)
{
  "detail": "Email already registered."
}
```

**POST `/api/prescriptions/`** (multipart/form-data)
```
file:         <binary — JPG / PNG / PDF>
symptom_notes: "Headache and fatigue for 3 days"
```

---

## 9. Assumptions & Trade-offs

| Decision                        | Rationale                                                                                    |
|---------------------------------|----------------------------------------------------------------------------------------------|
| **Local disk storage (volume)** | Keeps the stack self-contained and free-tier compliant. S3 is the production-grade alternative but requires an IAM role and incurs costs. |
| **Single EC2 instance**         | Assignment constraint. A real production setup would separate DB and app tiers.              |
| **No HTTPS / TLS**              | Adding Let's Encrypt Certbot + nginx TLS config is a one-hour addition but requires a domain name. Left as a documented future improvement. |
| **2 uvicorn workers**           | Balanced for t2/t3.micro (1 vCPU). Increase to 4 on t3.small+.                             |
| **JWT stored in localStorage**  | Simpler for the SPA demo. HttpOnly cookie would be more secure against XSS.                 |
| **Gemini free tier**            | Sufficient for demo traffic; may hit rate limits under load.                                 |
| **No reminder system**          | Requires either a persistent WebSocket server or a cron-based email worker — both add operational complexity beyond the assignment scope. |

---

## 10. Future Improvements

1. **HTTPS / TLS** — Add Certbot (Let's Encrypt) + nginx HTTPS config for any custom domain.
2. **S3 file storage** — Replace the Docker volume with an S3 bucket + IAM instance role for durability and scalability.
3. **Medicine reminder system** — Implement a Celery + Redis worker to send scheduled email/push reminders for each medicine dose.
4. **Dose tracking** — Add `dose_logs` table to record taken/skipped doses with timestamps.
5. **Refresh tokens** — Issue short-lived access tokens + long-lived refresh tokens for better security.
6. **Rate limiting** — Add `slowapi` rate-limiting middleware to the FastAPI app.
7. **CI/CD pipeline** — GitHub Actions workflow to build, test, push images to ECR, and SSH-deploy to EC2 on every merge to `main`.
8. **Horizontal scaling** — Move to ECS Fargate + RDS Aurora when traffic justifies the cost.
9. **Audit logging** — Log all prescription accesses for HIPAA-style compliance.
10. **HttpOnly JWT cookies** — Replace localStorage JWT with HttpOnly cookies to mitigate XSS risk.

