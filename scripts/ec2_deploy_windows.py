#!/usr/bin/env python3
"""
AI Health Companion — EC2 Deploy (Windows host version)
Runs on Windows host — full project available at PROJECT_DIR
"""
import os, time, textwrap, tarfile, io
import paramiko

# ── Config ────────────────────────────────────────────────────────────────────
EC2_IP       = "107.20.12.114"
KEY_FILE     = r"C:\Users\sodit\.ssh\ai-health-key.pem"
PROJECT_DIR  = r"G:\Assignments\ai-health-companion"
GEMINI_KEY_FILE = r"G:\Assignments\ai-health-companion\backend\.env"

def ok(msg):   print(f"  [OK]  {msg}", flush=True)
def log(msg):  print(f"  [ > ] {msg}", flush=True)
def info(msg): print(f"        {msg}", flush=True)

print("\n" + "="*60)
print("  AI Health Companion - EC2 Deployment (Windows)")
print(f"  Target: ubuntu@{EC2_IP}")
print("="*60 + "\n")

# ── Read Gemini key ───────────────────────────────────────────────────────────
gemini_key = "REPLACE_WITH_GEMINI_API_KEY"
try:
    with open(GEMINI_KEY_FILE, encoding="utf-8") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                gemini_key = line.strip().split("=", 1)[1]
                break
    ok(f"Gemini key found: {gemini_key[:15]}...")
except Exception as e:
    print(f"  Warning reading Gemini key: {e}")

# ── Connect via Paramiko ──────────────────────────────────────────────────────
log("Connecting to EC2 via SSH...")
pkey = paramiko.RSAKey.from_private_key_file(KEY_FILE)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(EC2_IP, username="ubuntu", pkey=pkey, timeout=30)
ok(f"SSH connected to {EC2_IP}")

def ssh_exec(cmd, timeout=900):
    """Run command on EC2, stream output in real-time."""
    transport = ssh.get_transport()
    chan = transport.open_session()
    chan.settimeout(timeout)
    chan.exec_command(cmd)
    while True:
        if chan.recv_ready():
            data = chan.recv(4096).decode("utf-8", errors="replace")
            for line in data.splitlines():
                info(line)
        if chan.recv_stderr_ready():
            data = chan.recv_stderr(4096).decode("utf-8", errors="replace")
            for line in data.splitlines():
                info(f"[err] {line}")
        if chan.exit_status_ready():
            break
        time.sleep(0.3)
    return chan.recv_exit_status()

def sftp_put(local_path, remote_path):
    sftp = ssh.open_sftp()
    size_kb = os.path.getsize(local_path) / 1024
    info(f"Uploading {os.path.basename(local_path)} ({size_kb:.0f} KB)...")
    sftp.put(local_path, remote_path)
    sftp.close()

def sftp_write(content, remote_path, mode=0o644):
    sftp = ssh.open_sftp()
    with sftp.open(remote_path, "w") as f:
        f.write(content)
    sftp.chmod(remote_path, mode)
    sftp.close()

# ── Create project tar from Windows ──────────────────────────────────────────
log("Creating project archive from full source...")
tar_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "ai-health-app.tar.gz")

EXCLUDE_DIRS  = {'.git', 'node_modules', '__pycache__', 'backups',
                 'uploads', 'dist', '.pytest_cache', '.idea', '.venv', 'venv'}
EXCLUDE_FILES = {'.env', 'backend.env', '*.pyc', '*.log'}

def should_exclude(path, is_dir=False):
    name = os.path.basename(path)
    if is_dir and name in EXCLUDE_DIRS:
        return True
    if not is_dir:
        if name.endswith('.pyc') or name.endswith('.log'):
            return True
        if name in ('.env',):
            return True
    return False

with tarfile.open(tar_path, "w:gz") as tar:
    for root, dirs, files in os.walk(PROJECT_DIR):
        # Filter excluded directories in-place
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d), is_dir=True)]

        for fname in files:
            fpath = os.path.join(root, fname)
            if should_exclude(fpath):
                continue
            arcname = os.path.relpath(fpath, PROJECT_DIR)
            try:
                tar.add(fpath, arcname=arcname)
            except (PermissionError, OSError):
                pass  # skip locked files

size_mb = os.path.getsize(tar_path) / 1024 / 1024
ok(f"Archive created: {size_mb:.1f} MB  ({tar_path})")

# ── Write production env files ────────────────────────────────────────────────
log("Writing production .env files...")
root_env = f"""MYSQL_ROOT_PASSWORD=QGIiSAWCfIIsx-s7qC0cWFnQMW6f7-Fhkjl43Ow5tEU
MYSQL_DATABASE=health_companion
MYSQL_USER=health_user
MYSQL_PASSWORD=biz1G7vOLG74ClXYiM5ssVXm2LrTXMuXiQu7Bur70Cs
MYSQL_PORT=3306
BACKEND_PORT=8000
FRONTEND_PORT=80
EC2_PUBLIC_IP={EC2_IP}
DOMAIN=
"""

backend_env = f"""APP_NAME=AI Health Companion API
APP_ENV=production
APP_DEBUG=false
HOST=0.0.0.0
PORT=8000
DATABASE_URL=mysql+pymysql://health_user:biz1G7vOLG74ClXYiM5ssVXm2LrTXMuXiQu7Bur70Cs@mysql:3306/health_companion
JWT_SECRET_KEY=6650bd30e54577eb9a0013eabe9a91190cca0b7a61e558fede2c1ad7e2ff9b23817a0f0c6e0e9fe84fb9958dbeeab69241def0aee2afdd26ace012d3fdf3dc20
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
CORS_ORIGINS=["http://{EC2_IP}","http://localhost"]
GEMINI_API_KEY={gemini_key}
"""

import tempfile
tmp = tempfile.gettempdir()
root_env_path    = os.path.join(tmp, "root.env")
backend_env_path = os.path.join(tmp, "backend.env")
with open(root_env_path,    "w") as f: f.write(root_env)
with open(backend_env_path, "w") as f: f.write(backend_env)
ok("Env files written")

# ── Upload via SFTP ───────────────────────────────────────────────────────────
log("Uploading to EC2 via SFTP...")
sftp_put(tar_path,         "/home/ubuntu/app.tar.gz")
sftp_put(root_env_path,    "/home/ubuntu/root.env")
sftp_put(backend_env_path, "/home/ubuntu/backend.env")
ok("All files uploaded")

# ── Remote deploy script ──────────────────────────────────────────────────────
log("Writing and executing deploy script on EC2...")
deploy_sh = """#!/bin/bash
set -e
echo '========================================'
echo ' AI Health Companion - EC2 Deploy'
echo '========================================'
date

# Clean previous attempt if any
rm -rf ~/ai-health-companion
mkdir -p ~/ai-health-companion
cd ~/ai-health-companion

echo '[1/6] Extracting archive...'
tar -xzf ~/app.tar.gz
echo '      Done.'

echo '[2/6] Placing env files...'
cp ~/root.env    .env
mkdir -p backend
cp ~/backend.env backend/.env
echo '      Done.'

echo '[3/6] Waiting for Docker to be ready...'
for i in $(seq 1 30); do
    if sudo docker info > /dev/null 2>&1; then
        echo "      Docker is ready"
        break
    fi
    echo "      Attempt $i/30 - waiting 10s..."
    sleep 10
done

# Ensure ubuntu user is in docker group
sudo usermod -aG docker ubuntu 2>/dev/null || true

echo '[4/6] Building Docker images (this takes 5-10 min)...'
cd ~/ai-health-companion
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache 2>&1

echo '[5/6] Starting services...'
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d 2>&1

echo '[6/6] Waiting for services to become healthy (60s)...'
sleep 60

echo ''
echo '========================================'
echo ' CONTAINER STATUS'
echo '========================================'
sudo docker compose ps 2>&1

echo ''
echo '========================================'
echo ' HEALTH CHECKS'
echo '========================================'
echo -n 'Backend : '
curl -sf http://localhost:8000/health && echo ' OK' || echo ' FAIL'

echo -n 'Frontend: '
curl -sf -o /dev/null -w '%{http_code}' http://localhost/ && echo ' OK' || echo ' FAIL'

echo ''
echo '========================================'
echo ' DEPLOYMENT COMPLETE'
echo '========================================'
"""

sftp_write(deploy_sh, "/home/ubuntu/deploy.sh", mode=0o755)

log("Executing deployment on EC2 (streaming live output)...")
log("Docker build takes 5-10 min on t2.micro - please wait...")
print("=" * 60, flush=True)

rc = ssh_exec("bash ~/deploy.sh", timeout=900)

print("=" * 60, flush=True)
ssh.close()

# ── Result ────────────────────────────────────────────────────────────────────
if rc == 0:
    print()
    print("*" * 60)
    print("  DEPLOYMENT COMPLETE!")
    print("*" * 60)
    print(f"  App URL     :  http://{EC2_IP}")
    print(f"  Login email :  demo@healthapp.com")
    print(f"  Password    :  Demo@1234")
    print(f"  SSH         :  ssh -i {KEY_FILE} ubuntu@{EC2_IP}")
    print("*" * 60)
    print("DEPLOY_SUCCESS")
else:
    print(f"\n  Deploy script exited with code: {rc}")
    print("  Check logs above for errors.")
    print("DEPLOY_FAILED")

