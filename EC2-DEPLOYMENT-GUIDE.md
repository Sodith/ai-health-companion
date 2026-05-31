# 🚀 EC2 Free Tier Deployment Guide — AI Health Companion

## ✅ Cost: $0 (AWS Free Tier — 12 months)

AWS Free Tier gives you:
- **EC2 t2.micro** — 750 hrs/month FREE (enough for 1 always-on server)
- **EBS 30 GB** — FREE
- **Data transfer** — 15 GB outbound FREE/month

> ⚠️ Requires a new AWS account (or account under 12 months old).
> After 12 months: ~$8.50/month for t2.micro.
> **Alternative (always free):** Oracle Cloud Free Tier — Ampere A1 VM with 4 OCPUs + 24 GB RAM, always free.

---

## PART 1 — AWS Account Setup

### Step 1.1 — Create AWS Account (skip if you have one)

1. Go to → **https://aws.amazon.com/free**
2. Click **"Create a Free Account"**
3. Enter email, password, account name
4. Select **"Personal"** account type
5. Enter credit/debit card (required for verification — will NOT be charged on free tier)
6. Verify phone number
7. Choose **"Basic support — Free"**
8. Sign in to AWS Console → **https://console.aws.amazon.com**

---

## PART 2 — Launch EC2 Instance

### Step 2.1 — Open EC2 Console

1. In AWS Console, search for **"EC2"** in the top search bar
2. Click **EC2** → click **"Launch Instance"** (orange button)

### Step 2.2 — Configure the Instance

Fill in the launch wizard exactly as follows:

```
Name:              ai-health-companion

AMI (OS):          Ubuntu Server 22.04 LTS (HVM), SSD Volume Type
                   ✅ Make sure it says "Free tier eligible"

Instance type:     t2.micro
                   ✅ "Free tier eligible" label must be visible

Key pair:          → Click "Create new key pair"
                     Name:  ai-health-key
                     Type:  RSA
                     Format: .pem  (for Mac/Linux/WSL)
                             .ppk  (for PuTTY on Windows)
                   → Click "Create key pair" — file downloads automatically
                   → SAVE THIS FILE — you cannot re-download it

Network settings:  → Click "Edit"
  VPC:             default
  Subnet:          any (pick first one)
  Auto-assign IP:  ENABLE  ← important!

Firewall (Security Group): → "Create security group"
  Name: ai-health-sg

  Add these rules:
  ┌──────────┬──────────┬───────┬─────────────┬────────────────────────────┐
  │ Type     │ Protocol │ Port  │ Source      │ Purpose                    │
  ├──────────┼──────────┼───────┼─────────────┼────────────────────────────┤
  │ SSH      │ TCP      │ 22    │ My IP       │ Admin access (your IP only)│
  │ HTTP     │ TCP      │ 80    │ 0.0.0.0/0   │ App access (public)        │
  └──────────┴──────────┴───────┴─────────────┴────────────────────────────┘
  ⛔ Do NOT add rules for port 8000 or 3306

Storage:           8 GB → change to 20 GB  (still free tier)
                   Volume type: gp2

Advanced details:  leave all defaults
```

3. Click **"Launch Instance"** (orange button, bottom right)
4. Click **"View all instances"**
5. Wait ~2 minutes for **"Instance state"** to show **"running"**
6. Note the **"Public IPv4 address"** — you'll need this (e.g. `54.123.45.67`)

---

## PART 3 — Connect to EC2

### Step 3.1 — Save your key file

```powershell
# Windows — save the .pem file to:
C:\Users\YourName\.ssh\ai-health-key.pem
```

### Step 3.2 — Connect via SSH

**Windows (PowerShell / Windows Terminal):**
```powershell
# Fix key permissions (required)
icacls "C:\Users\YourName\.ssh\ai-health-key.pem" /inheritance:r /grant:r "$($env:USERNAME):(R)"

# Connect
ssh -i "C:\Users\YourName\.ssh\ai-health-key.pem" ubuntu@YOUR_EC2_PUBLIC_IP
```

**Windows (PuTTY):**
```
Host:     YOUR_EC2_PUBLIC_IP
Port:     22
Auth:     Connection → SSH → Auth → Browse → select .ppk file
Username: ubuntu
```

**Mac / Linux:**
```bash
chmod 400 ~/.ssh/ai-health-key.pem
ssh -i ~/.ssh/ai-health-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

---

## PART 4 — Install Docker on EC2

Run these commands **on the EC2 instance** (after SSH):

```bash
# 1. Update system
sudo apt-get update -y && sudo apt-get upgrade -y

# 2. Install Docker
curl -fsSL https://get.docker.com | sudo bash

# 3. Add ubuntu user to docker group (no sudo needed)
sudo usermod -aG docker ubuntu

# 4. Apply group change (log out and back in, OR run:)
newgrp docker

# 5. Verify
docker --version          # Docker version 24.x.x
docker compose version    # Docker Compose version v2.x.x
```

---

## PART 5 — Deploy the Application

### Step 5.1 — Push code to GitHub (from your LOCAL machine)

```bash
# On your LOCAL Windows machine (PowerShell):
cd G:\Assignments\ai-health-companion

# Initialize git if not already done
git init
git add .
git commit -m "Phase 6 — production ready"

# Create repo on GitHub: https://github.com/new
# Then:
git remote add origin https://github.com/YOUR_USERNAME/ai-health-companion.git
git branch -M main
git push -u origin main
```

### Step 5.2 — Clone on EC2

```bash
# On EC2:
git clone https://github.com/YOUR_USERNAME/ai-health-companion.git
cd ai-health-companion
```

### Step 5.3 — Create production .env files

```bash
# On EC2 — create root .env
nano .env
```

Paste this content (replace the two FILL_IN values):
```dotenv
MYSQL_ROOT_PASSWORD=QGIiSAWCfIIsx-s7qC0cWFnQMW6f7-Fhkjl43Ow5tEU
MYSQL_DATABASE=health_companion
MYSQL_USER=health_user
MYSQL_PASSWORD=biz1G7vOLG74ClXYiM5ssVXm2LrTXMuXiQu7Bur70Cs
MYSQL_PORT=3306
BACKEND_PORT=8000
FRONTEND_PORT=80
EC2_PUBLIC_IP=YOUR_EC2_PUBLIC_IP
DOMAIN=
```

```bash
# Create backend .env
nano backend/.env
```

Paste this (replace FILL_IN values):
```dotenv
APP_NAME="AI Health Companion API"
APP_ENV=production
APP_DEBUG=false
HOST=0.0.0.0
PORT=8000
DATABASE_URL=mysql+pymysql://health_user:biz1G7vOLG74ClXYiM5ssVXm2LrTXMuXiQu7Bur70Cs@mysql:3306/health_companion
JWT_SECRET_KEY=6650bd30e54577eb9a0013eabe9a91190cca0b7a61e558fede2c1ad7e2ff9b23817a0f0c6e0e9fe84fb9958dbeeab69241def0aee2afdd26ace012d3fdf3dc20
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
CORS_ORIGINS=["http://YOUR_EC2_PUBLIC_IP","http://localhost"]
GEMINI_API_KEY=YOUR_PERMANENT_GEMINI_API_KEY
```

### Step 5.4 — Build and start

```bash
# Build images (takes 3-5 minutes on t2.micro)
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start all services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Watch logs (optional)
docker compose logs -f
```

### Step 5.5 — Verify deployment

```bash
# Check all containers are healthy
docker compose ps

# Expected output:
# ai-health-mysql     healthy   3306/tcp        ← internal only
# ai-health-backend   healthy   8000/tcp        ← internal only
# ai-health-frontend  healthy   0.0.0.0:80->80  ← public

# Test the app
curl http://localhost/
curl http://localhost:8000/health
```

### Step 5.6 — Open in browser

```
http://YOUR_EC2_PUBLIC_IP
```

---

## PART 6 — Make it Permanent (survive reboots)

```bash
# Auto-start Docker on boot
sudo systemctl enable docker

# Create a systemd service to auto-start the app
sudo nano /etc/systemd/system/ai-health.service
```

Paste:
```ini
[Unit]
Description=AI Health Companion
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/ai-health-companion
ExecStart=docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
ExecStop=docker compose -f docker-compose.yml -f docker-compose.prod.yml down
User=ubuntu

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-health.service
```

---

## PART 7 — Optional: Set Up Automated Backups

```bash
chmod +x scripts/backup.sh

# Test backup
./scripts/backup.sh

# Auto-backup daily at 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /home/ubuntu/ai-health-companion/scripts/backup.sh >> /var/log/ai-health-backup.log 2>&1") | crontab -
```

---

## PART 8 — Alternative: Oracle Cloud (Always Free — No 12-month limit)

If you don't want the 12-month restriction, Oracle Cloud Free Tier is **always free**:

| Resource | Oracle Free Tier | AWS Free Tier |
|----------|-----------------|---------------|
| VM       | 2x AMD micro OR 1x Ampere A1 (4 OCPU, 24 GB RAM) | t2.micro (1 OCPU, 1 GB RAM) |
| Storage  | 200 GB | 30 GB |
| Duration | **Forever** | 12 months |
| Cost     | **$0 always** | $0 for 12 months |

**Oracle Cloud signup:** https://www.oracle.com/cloud/free/

Steps are identical — same Ubuntu 22.04, same Docker install, same `docker compose up -d`.

---

## ⚠️ Important Notes Before Deploying

### 1. Get a permanent Gemini API key
Your current `AQ.` key **expires every hour**. For EC2:
1. Go to → https://aistudio.google.com/app/apikey
2. Click **"Create API key"** → copy the `AIzaSy...` key
3. Paste it in `backend/.env` on the server as `GEMINI_API_KEY`

### 2. JWT secret is now production-grade ✅
Generated and included in `.env.ec2` and `backend/.env.ec2` files.

### 3. MySQL port is NOT exposed ✅
`docker-compose.prod.yml` already removes the MySQL port mapping.

### 4. Free tier limits
- 750 hours/month = enough for ONE t2.micro running 24/7
- Only ONE free t2.micro at a time (if you launch more, you'll be charged)
- Monitor usage: AWS Console → Billing → Free Tier Usage

---

## Quick Reference — Useful Commands on EC2

```bash
# Check status
docker compose ps

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Restart a service
docker compose restart backend

# Update application (after git push)
git pull origin main
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Run health check script
./scripts/health-check.sh

# Manual DB backup
./scripts/backup.sh

# Enter MySQL shell
docker exec -it ai-health-mysql mysql -u health_user -pbiz1G7vOLG74ClXYiM5ssVXm2LrTXMuXiQu7Bur70Cs health_companion

# Stop everything
docker compose down

# Stop and wipe all data (careful!)
docker compose down -v
```

