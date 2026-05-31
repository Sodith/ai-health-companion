#!/usr/bin/env python3
"""
AI Health Companion — EC2 Application Deployment via Paramiko
No scp/ssh binaries needed — pure Python SSH
"""
import os, time, textwrap, tarfile
import paramiko

EC2_IP   = "107.20.12.114"
KEY_FILE = "/tmp/ai-health-key.pem"

def ok(msg):   print(f"  ✅ {msg}", flush=True)
def log(msg):  print(f"  ➜  {msg}", flush=True)
def info(msg): print(f"     {msg}", flush=True)

print("\n" + "="*60)
print("  AI Health Companion — EC2 Deployment")
print(f"  Target: ubuntu@{EC2_IP}")
print("="*60 + "\n")

# ── Read Gemini key ───────────────────────────────────────────────────────────
gemini_key = "REPLACE_WITH_GEMINI_API_KEY"
try:
    with open("/app/backend/.env") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                gemini_key = line.strip().split("=", 1)[1]
                break
    ok(f"Gemini key: {gemini_key[:15]}...")
except Exception as e:
    print(f"  Warning: {e}")

# ── Connect via Paramiko ──────────────────────────────────────────────────────
log("Connecting to EC2 via SSH...")
key = paramiko.RSAKey.from_private_key_file(KEY_FILE)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(EC2_IP, username="ubuntu", pkey=key, timeout=30)
ok(f"SSH connected to {EC2_IP}")

def ssh_exec(cmd, timeout=900):
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
        time.sleep(0.5)
    return chan.recv_exit_status()

def sftp_put(local, remote):
    sftp = ssh.open_sftp()
    size_kb = os.path.getsize(local) / 1024
    info(f"Uploading {os.path.basename(local)} ({size_kb:.0f} KB)...")
    sftp.put(local, remote)
    sftp.close()

# ── Create project tar archive ────────────────────────────────────────────────
log("Creating project archive...")
tar_path = "/tmp/ai-health-app.tar.gz"
exclude_dirs  = {'.git','node_modules','__pycache__','backups','uploads','dist','.pytest_cache'}
exclude_files = {'.env','backend/.env'}

with tarfile.open(tar_path, "w:gz") as tar:
    base = "/app"
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for fname in files:
            if fname.endswith('.pyc') or fname == '.env':
                continue
            fpath = os.path.join(root, fname)
            arcname = os.path.relpath(fpath, base)
            tar.add(fpath, arcname=arcname)

ok(f"Archive: {os.path.getsize(tar_path)/1024/1024:.1f} MB")

# ── Write env files ───────────────────────────────────────────────────────────
log("Writing production env files...")
with open("/tmp/root.env", "w") as f:
    f.write(f"""MYSQL_ROOT_PASSWORD=QGIiSAWCfIIsx-s7qC0cWFnQMW6f7-Fhkjl43Ow5tEU
MYSQL_DATABASE=health_companion
MYSQL_USER=health_user
MYSQL_PASSWORD=biz1G7vOLG74ClXYiM5ssVXm2LrTXMuXiQu7Bur70Cs
MYSQL_PORT=3306
BACKEND_PORT=8000
FRONTEND_PORT=80
EC2_PUBLIC_IP={EC2_IP}
DOMAIN=
""")

with open("/tmp/backend.env", "w") as f:
    f.write(f"""APP_NAME=AI Health Companion API
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
""")
ok("Env files written")

# ── Upload via SFTP ───────────────────────────────────────────────────────────
log("Uploading files to EC2 via SFTP...")
sftp_put(tar_path,          "/home/ubuntu/app.tar.gz")
sftp_put("/tmp/root.env",    "/home/ubuntu/root.env")
sftp_put("/tmp/backend.env", "/home/ubuntu/backend.env")
ok("Files uploaded")

# ── Write and run deploy script ───────────────────────────────────────────────
log("Deploying on EC2 (8-10 min for first Docker build)...")
deploy_script = textwrap.dedent(f"""
    #!/bin/bash
    set -e
    echo '=== AI Health Companion EC2 Deploy ==='
    date

    mkdir -p ~/ai-health-companion
    cd ~/ai-health-companion
    echo 'Extracting archive...'
    tar -xzf ~/app.tar.gz
    cp ~/root.env    .env
    cp ~/backend.env backend/.env
    echo 'Env files placed'

    echo 'Waiting for Docker...'
    for i in $(seq 1 30); do
        if sudo docker info > /dev/null 2>&1; then echo 'Docker ready'; break; fi
        echo "  Waiting ($i/30)..."; sleep 10
    done

    sudo usermod -aG docker ubuntu 2>/dev/null || true

    echo 'Building images...'
    cd ~/ai-health-companion
    sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache

    echo 'Starting services...'
    sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

    sleep 30
    echo '=== Container Status ==='
    sudo docker compose ps
    echo '=== Backend Health ==='
    curl -sf http://localhost:8000/health && echo ' [OK]' || echo ' [FAIL]'
    echo '=== Frontend ==='
    curl -sf http://localhost/ > /dev/null && echo 'Frontend OK' || echo 'Frontend FAIL'
    echo '=== DONE ==='
""").strip()

sftp = ssh.open_sftp()
with sftp.open("/home/ubuntu/deploy.sh", "w") as f:
    f.write(deploy_script)
sftp.chmod("/home/ubuntu/deploy.sh", 0o755)
sftp.close()

print("-"*60, flush=True)
rc = ssh_exec("bash ~/deploy.sh", timeout=900)
print("-"*60, flush=True)
ssh.close()

if rc == 0:
    print("\n" + "="*60)
    print("  DEPLOYMENT COMPLETE!")
    print("="*60)
    print(f"  App URL  :  http://{EC2_IP}")
    print(f"  Login    :  demo@healthapp.com  /  Demo@1234")
    print(f"  SSH      :  ssh -i C:\\Users\\sodit\\.ssh\\ai-health-key.pem ubuntu@{EC2_IP}")
    print("="*60)
    print("DEPLOY_SUCCESS")
else:
    print(f"  Exit code: {rc}")
    print("DEPLOY_FAILED")

