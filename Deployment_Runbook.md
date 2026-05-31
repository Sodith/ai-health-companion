# 🚀 AI Health Companion — Deployment Runbook

> **Version:** 1.0 | **Date:** May 2026
> **Purpose:** Step-by-step guide to deploy AI Health Companion on AWS EC2 from scratch.
> **Target audience:** DevOps Engineer or Backend Engineer with basic Linux and Docker knowledge.
> **Estimated time:** 45–90 minutes (first deployment)

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [AWS EC2 Instance Setup](#2-aws-ec2-instance-setup)
3. [Security Group Configuration](#3-security-group-configuration)
4. [Connecting to the EC2 Instance](#4-connecting-to-the-ec2-instance)
5. [Server Provisioning — Docker Installation](#5-server-provisioning--docker-installation)
6. [Repository Clone & Configuration](#6-repository-clone--configuration)
7. [Environment Variables Configuration](#7-environment-variables-configuration)
8. [Docker Compose Deployment](#8-docker-compose-deployment)
9. [Database Migration](#9-database-migration)
10. [Verification & Health Checks](#10-verification--health-checks)
11. [Re-Deployment (Updates)](#11-re-deployment-updates)
12. [Troubleshooting Guide](#12-troubleshooting-guide)
13. [Rollback Strategy](#13-rollback-strategy)
14. [Backup Strategy](#14-backup-strategy)
15. [Maintenance Reference](#15-maintenance-reference)

---

## 1. Prerequisites

### Required Before Starting

| Requirement | Notes |
|-------------|-------|
| AWS Account | With permission to create EC2 instances and Security Groups |
| EC2 Key Pair | `.pem` file downloaded and stored securely |
| Google Gemini API Key | Obtain from [Google AI Studio](https://aistudio.google.com) |
| GitHub access | Repository must be accessible from the EC2 instance |
| SSH client | Terminal (Linux/Mac) or PuTTY / Windows Terminal (Windows) |

### Local Machine Requirements

- SSH client available in terminal
- Git installed

---

## 2. AWS EC2 Instance Setup

### Step 1 — Launch an EC2 Instance

1. Open **AWS Console** → **EC2** → **Launch Instance**

2. Configure the instance:

   | Setting | Recommended Value |
   |---------|-------------------|
   | Name | `ai-health-companion` |
   | AMI | **Ubuntu Server 22.04 LTS** (64-bit x86) |
   | Instance Type | `t3.small` (minimum) / `t3.medium` (recommended) |
   | Key Pair | Select an existing key pair or create a new one |
   | Storage | 20 GB gp3 SSD (minimum) |

3. Under **Network Settings** → create or select a Security Group (see Section 3)

4. Click **Launch Instance**

5. Note the **Public IPv4 address** assigned to your instance

### Step 2 — Allocate an Elastic IP (Recommended)

An Elastic IP ensures your public address does not change on instance restart.

1. EC2 Console → **Elastic IPs** → **Allocate Elastic IP address**
2. **Associate Elastic IP** → select your EC2 instance
3. Use this IP in all configuration going forward

---

## 3. Security Group Configuration

Create a Security Group named `ai-health-sg` with the following **Inbound Rules**:

| Type | Protocol | Port | Source | Purpose |
|------|----------|------|--------|---------|
| SSH | TCP | 22 | Your IP only (`x.x.x.x/32`) | Admin access |
| HTTP | TCP | 80 | `0.0.0.0/0` | Frontend (Angular via Nginx) |
| Custom TCP | TCP | 8000 | `0.0.0.0/0` | Backend API (FastAPI) |

**Outbound Rules:** Allow all (default).

> ⚠️ **Security note:** Port 3306 (MySQL) must **NOT** be opened to the internet. MySQL is accessed only within the Docker bridge network.
>
> ⚠️ Restrict SSH (port 22) to your own IP address. Never open SSH to `0.0.0.0/0`.

---

## 4. Connecting to the EC2 Instance

### Linux / macOS

```bash
# Set correct permissions on your key file
chmod 400 /path/to/your-key.pem

# Connect via SSH
ssh -i /path/to/your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

### Windows (PowerShell)

```powershell
ssh -i C:\path\to\your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

### Verify Connection

After login you should see a prompt like:
```
ubuntu@ip-172-31-xx-xx:~$
```

---

## 5. Server Provisioning — Docker Installation

Run the following commands on the EC2 instance. This is a **one-time setup**.

### Step 1 — Update System Packages

```bash
sudo apt-get update && sudo apt-get upgrade -y
```

### Step 2 — Install Docker Engine

```bash
# Install Docker
sudo apt-get install -y docker.io

# Start Docker service and enable on boot
sudo systemctl start docker
sudo systemctl enable docker

# Verify Docker is running
sudo docker --version
# Expected: Docker version 24.x.x
```

### Step 3 — Install Docker Compose Plugin

```bash
# Install Docker Compose (plugin style)
sudo apt-get install -y docker-compose-plugin

# Verify
docker compose version
# Expected: Docker Compose version v2.x.x
```

### Step 4 — Add ubuntu User to Docker Group

This allows running Docker commands without `sudo`.

```bash
sudo usermod -aG docker ubuntu

# Apply group membership immediately (or log out and back in)
newgrp docker

# Verify (should NOT say "permission denied")
docker ps
```

### Step 5 — Install Git and curl

```bash
sudo apt-get install -y git curl
```

---

## 6. Repository Clone & Configuration

### Step 1 — Clone the Repository

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/ai-health-companion.git
cd ai-health-companion
```

### Step 2 — Verify Project Structure

```bash
ls -la
# Expected output:
# backend/  frontend/  docker-compose.yml  docker-compose.prod.yml  README.md  ...
```

---

## 7. Environment Variables Configuration

### Step 1 — Create the `.env` File

```bash
cd ~/ai-health-companion
cp backend/.env.example backend/.env
nano backend/.env
```

### Step 2 — Set All Required Values

Edit the `.env` file with your production values:

```dotenv
# ── Application ──────────────────────────────────────────────────────────────
APP_NAME=AI Health Companion API
APP_ENV=production
APP_DEBUG=false
HOST=0.0.0.0
PORT=8000

# ── Database ─────────────────────────────────────────────────────────────────
# NOTE: In Docker Compose, DATABASE_URL is overridden to point to the mysql service.
# These values are used to initialise the MySQL Docker container.
MYSQL_ROOT_PASSWORD=<STRONG_ROOT_PASSWORD>
MYSQL_DATABASE=ai_health_db
MYSQL_USER=ai_health_user
MYSQL_PASSWORD=<STRONG_USER_PASSWORD>
MYSQL_PORT=3306
DATABASE_URL=mysql+pymysql://ai_health_user:<STRONG_USER_PASSWORD>@localhost:3306/ai_health_db

# ── JWT ───────────────────────────────────────────────────────────────────────
# Generate with: openssl rand -hex 32
JWT_SECRET_KEY=<64_CHAR_HEX_SECRET>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# ── Google Gemini ─────────────────────────────────────────────────────────────
GEMINI_API_KEY=<YOUR_GOOGLE_AI_STUDIO_KEY>

# ── CORS ─────────────────────────────────────────────────────────────────────
CORS_ORIGINS=["http://YOUR_EC2_PUBLIC_IP","http://localhost"]

# ── Ports ────────────────────────────────────────────────────────────────────
BACKEND_PORT=8000
FRONTEND_PORT=80
```

> **Tip — Generate a secure JWT secret:**
> ```bash
> openssl rand -hex 32
> ```

### Step 3 — Save and Verify

```bash
# Save: Ctrl+O, Enter, Ctrl+X (nano)

# Verify key variables are set
grep -E "GEMINI_API_KEY|JWT_SECRET_KEY|MYSQL_ROOT_PASSWORD" backend/.env
# All three lines should show non-empty values
```

---

## 8. Docker Compose Deployment

### Step 1 — Build and Start All Services

```bash
cd ~/ai-health-companion

# Build images and start in detached mode
docker compose -f docker-compose.prod.yml up -d --build
```

This command will:
1. Build the FastAPI backend image from `backend/Dockerfile`
2. Build the Angular frontend image from `frontend/Dockerfile`
3. Pull the MySQL 8.0 image from Docker Hub
4. Start all three containers in the background
5. Apply health checks and wait for MySQL to be ready before starting the backend

**Expected output:**
```
[+] Building ...
[+] Running 3/3
 ✔ Container ai-health-mysql     Healthy
 ✔ Container ai-health-backend   Started
 ✔ Container ai-health-frontend  Started
```

### Step 2 — Monitor Startup

```bash
# Watch all container logs during startup
docker compose -f docker-compose.prod.yml logs -f

# Or watch a specific service
docker compose -f docker-compose.prod.yml logs -f backend
```

Press `Ctrl+C` to stop watching logs without stopping containers.

### Step 3 — Verify All Services Are Running

```bash
docker compose -f docker-compose.prod.yml ps
```

Expected output (all should show `healthy` or `running`):
```
NAME                  STATUS          PORTS
ai-health-frontend    Up (healthy)    0.0.0.0:80->80/tcp
ai-health-backend     Up (healthy)    0.0.0.0:8000->8000/tcp
ai-health-mysql       Up (healthy)    0.0.0.0:3306->3306/tcp
```

---

## 9. Database Migration

Run Alembic migrations to create the database schema. This is required on:
- First deployment
- Any deployment that includes a new migration file

```bash
# Apply all pending migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade  -> f29befa3f21a, create_users_table
INFO  [alembic.runtime.migration] Running upgrade f29befa3f21a -> e1958b089da1, create_prescriptions_table
INFO  [alembic.runtime.migration] Running upgrade e1958b089da1 -> 3a7c912d8f45, create_ai_analysis_and_medicines_tables
```

### Verify Migration

```bash
docker compose -f docker-compose.prod.yml exec mysql \
  mysql -u ai_health_user -p<MYSQL_PASSWORD> ai_health_db -e "SHOW TABLES;"
```

Expected tables: `users`, `prescriptions`, `ai_analysis`, `medicines`, `alembic_version`

---

## 10. Verification & Health Checks

### Backend Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}

curl http://YOUR_EC2_PUBLIC_IP:8000/health
# Expected: {"status":"ok"}
```

### Frontend Health Check

```bash
curl -I http://localhost/
# Expected: HTTP/1.1 200 OK

curl -I http://YOUR_EC2_PUBLIC_IP/
# Expected: HTTP/1.1 200 OK
```

### Swagger UI

Open in your browser:
```
http://YOUR_EC2_PUBLIC_IP:8000/docs
```

You should see the interactive FastAPI Swagger documentation.

### Full E2E Smoke Test

```bash
# 1. Register a new user
curl -s -X POST http://YOUR_EC2_PUBLIC_IP:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test1234!"}' | python3 -m json.tool

# 2. Login and capture token
TOKEN=$(curl -s -X POST http://YOUR_EC2_PUBLIC_IP:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test1234!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

echo "Token: $TOKEN"

# 3. List prescriptions (authenticated)
curl -s http://YOUR_EC2_PUBLIC_IP:8000/api/v1/prescriptions \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## 11. Re-Deployment (Updates)

When you push new code to GitHub, follow this process to redeploy:

```bash
cd ~/ai-health-companion

# 1. Pull latest code
git pull origin main

# 2. Rebuild and restart changed services (zero-downtime for unchanged services)
docker compose -f docker-compose.prod.yml up -d --build

# 3. Apply any new database migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 4. Verify deployment
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

> **Note:** If only the backend changed, only the backend container is rebuilt. MySQL data is preserved in the `mysql_data` named volume.

---

## 12. Troubleshooting Guide

### Problem: Container fails to start

```bash
# Check detailed logs
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs mysql
docker compose -f docker-compose.prod.yml logs frontend
```

### Problem: MySQL connection refused / backend can't reach database

**Symptoms:** Backend logs show `Can't connect to MySQL server`

**Steps:**
```bash
# 1. Check MySQL container health
docker compose -f docker-compose.prod.yml ps mysql

# 2. If not healthy, inspect MySQL logs
docker compose -f docker-compose.prod.yml logs mysql

# 3. Ensure MYSQL_ROOT_PASSWORD in .env matches what MySQL was initialised with
# If you changed the password after first run, the volume must be wiped:
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Problem: `GEMINI_API_KEY` not set / Gemini returns 403

**Symptoms:** Analysis endpoint returns 500 or auth error

**Steps:**
```bash
# Verify API key is set in container environment
docker compose -f docker-compose.prod.yml exec backend env | grep GEMINI

# If missing, edit backend/.env and restart
nano backend/.env
docker compose -f docker-compose.prod.yml restart backend
```

### Problem: Frontend shows blank page or 404

**Symptoms:** Nginx serves blank page; Angular app doesn't load

**Steps:**
```bash
# Check frontend container logs
docker compose -f docker-compose.prod.yml logs frontend

# Verify Nginx config is valid
docker compose -f docker-compose.prod.yml exec frontend nginx -t

# Rebuild frontend
docker compose -f docker-compose.prod.yml up -d --build frontend
```

### Problem: CORS errors in browser console

**Symptoms:** `Access-Control-Allow-Origin` missing

**Steps:**
```bash
# Verify CORS_ORIGINS in backend/.env includes your EC2 public IP
grep CORS_ORIGINS backend/.env
# Should be: CORS_ORIGINS=["http://YOUR_EC2_IP","http://localhost"]

# Restart backend after fixing
docker compose -f docker-compose.prod.yml restart backend
```

### Problem: JWT `401 Unauthorized` on all requests

**Symptoms:** Every API call returns 401 even with a valid token

**Steps:**
```bash
# Verify JWT_SECRET_KEY is set and not the default placeholder
grep JWT_SECRET_KEY backend/.env

# If key was changed, all existing tokens are invalidated — users must log in again
# Restart backend
docker compose -f docker-compose.prod.yml restart backend
```

### Problem: Disk space full

**Symptoms:** Docker build fails; MySQL fails to start

```bash
# Check disk usage
df -h /

# Remove unused Docker images and stopped containers
docker system prune -f

# Remove unused volumes (WARNING: destroys database data if volumes are stopped)
# Only do this if you have a backup or intend to start fresh:
# docker system prune -f --volumes
```

### Problem: Port 80 or 8000 already in use

```bash
# Find what is using the port
sudo lsof -i :80
sudo lsof -i :8000

# Stop the conflicting process or change port in .env
```

---

## 13. Rollback Strategy

### Rollback to Previous Code Version

```bash
cd ~/ai-health-companion

# Find the previous stable commit hash
git log --oneline -10

# Hard reset to previous commit
git reset --hard <PREVIOUS_COMMIT_HASH>

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build

# If the rollback involved a database migration, downgrade:
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1
```

### Rollback a Database Migration

```bash
# Downgrade one migration step
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1

# Downgrade to a specific revision
docker compose -f docker-compose.prod.yml exec backend alembic downgrade <REVISION_ID>

# View migration history
docker compose -f docker-compose.prod.yml exec backend alembic history
```

### Emergency: Complete Reset

> ⚠️ **This destroys ALL data. Only use in a last-resort scenario.**

```bash
cd ~/ai-health-companion

# Stop everything and destroy volumes
docker compose -f docker-compose.prod.yml down -v

# Rebuild from scratch
docker compose -f docker-compose.prod.yml up -d --build

# Re-apply migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

---

## 14. Backup Strategy

### Database Backup

#### Manual Backup (On-Demand)

```bash
# Create a timestamped SQL dump
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker compose -f docker-compose.prod.yml exec mysql \
  mysqldump -u root -p${MYSQL_ROOT_PASSWORD} ai_health_db \
  > ~/backups/ai_health_db_${TIMESTAMP}.sql

echo "Backup saved: ~/backups/ai_health_db_${TIMESTAMP}.sql"
```

#### Automated Daily Backup (cron)

```bash
# Create backup directory
mkdir -p ~/backups

# Edit crontab
crontab -e

# Add this line to run backup daily at 2 AM:
0 2 * * * cd ~/ai-health-companion && docker compose -f docker-compose.prod.yml exec -T mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} ai_health_db > ~/backups/ai_health_db_$(date +\%Y\%m\%d).sql 2>&1
```

#### Restore from Backup

```bash
cat ~/backups/ai_health_db_20260531.sql | \
  docker compose -f docker-compose.prod.yml exec -T mysql \
  mysql -u root -p${MYSQL_ROOT_PASSWORD} ai_health_db
```

### Uploaded Files Backup

```bash
# Backup the prescription uploads volume
docker run --rm \
  -v ai-health-companion_prescription_uploads:/data \
  -v ~/backups:/backup \
  ubuntu tar czf /backup/prescriptions_$(date +%Y%m%d).tar.gz -C /data .
```

### Backup to S3 (Recommended for Production)

```bash
# Install AWS CLI
sudo apt-get install -y awscli

# Configure credentials
aws configure

# Sync backups to S3
aws s3 sync ~/backups s3://your-backup-bucket/ai-health-companion/
```

---

## 15. Maintenance Reference

### Common Commands Cheat Sheet

```bash
# --- Service Management ---
docker compose -f docker-compose.prod.yml ps                    # Status
docker compose -f docker-compose.prod.yml up -d --build         # Deploy
docker compose -f docker-compose.prod.yml down                  # Stop
docker compose -f docker-compose.prod.yml restart backend        # Restart one service

# --- Logs ---
docker compose -f docker-compose.prod.yml logs -f               # All services
docker compose -f docker-compose.prod.yml logs -f backend        # Backend only
docker compose -f docker-compose.prod.yml logs --tail=100 mysql  # Last 100 lines

# --- Database ---
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head    # Migrate
docker compose -f docker-compose.prod.yml exec backend alembic current         # Current version
docker compose -f docker-compose.prod.yml exec backend alembic history         # History
docker compose -f docker-compose.prod.yml exec mysql mysql -u root -p          # MySQL shell

# --- Debugging ---
docker compose -f docker-compose.prod.yml exec backend bash     # Shell in backend
docker compose -f docker-compose.prod.yml exec backend env      # View env vars
docker stats                                                      # CPU / memory usage

# --- Cleanup ---
docker system prune -f                                            # Remove unused resources
docker volume ls                                                  # List volumes
```

### Environment Variables Quick Reference

| Variable | Required | Example |
|----------|----------|---------|
| `GEMINI_API_KEY` | ✅ Yes | `AIza...` |
| `JWT_SECRET_KEY` | ✅ Yes | 64-char hex string |
| `MYSQL_ROOT_PASSWORD` | ✅ Yes | strong password |
| `MYSQL_PASSWORD` | ✅ Yes | strong password |
| `CORS_ORIGINS` | ✅ Yes | `["http://x.x.x.x"]` |
| `APP_ENV` | Optional | `production` |
| `APP_DEBUG` | Optional | `false` |
| `JWT_EXPIRE_MINUTES` | Optional | `60` |

---

*AI Health Companion — Deployment Runbook v1.0*
*Last updated: May 2026*

