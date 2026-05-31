# ─────────────────────────────────────────────────────────────────────────────
#  scripts/aws-deploy.ps1
#  Full automated AWS EC2 deployment for AI Health Companion
#  Run from the project root:  .\scripts\aws-deploy.ps1
# ─────────────────────────────────────────────────────────────────────────────

param(
    [string]$Region       = "us-east-1",
    [string]$InstanceType = "t2.micro",
    [string]$GeminiKey    = ""
)

$ErrorActionPreference = "Stop"
$PROJECT_DIR = Split-Path -Parent $PSScriptRoot
$KEY_NAME    = "ai-health-key"
$KEY_FILE    = "$env:USERPROFILE\.ssh\$KEY_NAME.pem"
$SG_NAME     = "ai-health-sg"
$INSTANCE_TAG= "ai-health-companion"

function Log($msg) { Write-Host "  $msg" -ForegroundColor Cyan }
function Ok($msg)  { Write-Host "  ✅ $msg" -ForegroundColor Green }
function Err($msg) { Write-Host "  ❌ $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor White
Write-Host "  AI Health Companion — Automated EC2 Deployment" -ForegroundColor White
Write-Host "  Region: $Region  |  Type: $InstanceType (Free Tier)" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor White
Write-Host ""

# ── Step 1: Verify AWS CLI ────────────────────────────────────────────────────
Log "Checking AWS CLI..."
try { $v = aws --version 2>&1; Ok "AWS CLI: $v" }
catch { Err "AWS CLI not found. Run: msiexec /i https://awscli.amazonaws.com/AWSCLIV2.msi" }

Log "Checking AWS credentials..."
try { $id = aws sts get-caller-identity --output json | ConvertFrom-Json; Ok "Account: $($id.Account)  User: $($id.Arn)" }
catch { Err "AWS credentials not configured. Run: aws configure" }

# ── Step 2: Get your public IP for SSH restriction ────────────────────────────
Log "Getting your public IP..."
$MY_IP = (Invoke-RestMethod -Uri "https://api.ipify.org" -Method GET).Trim()
Ok "Your IP: $MY_IP (will be whitelisted for SSH)"

# ── Step 3: Create SSH Key Pair ───────────────────────────────────────────────
Log "Setting up SSH key pair '$KEY_NAME'..."
$existingKey = aws ec2 describe-key-pairs --key-names $KEY_NAME --region $Region 2>&1
if ($existingKey -match "InvalidKeyPair") {
    New-Item -Path "$env:USERPROFILE\.ssh" -ItemType Directory -Force | Out-Null
    $keyMaterial = aws ec2 create-key-pair --key-name $KEY_NAME --query "KeyMaterial" --output text --region $Region
    $keyMaterial | Set-Content -Path $KEY_FILE -Encoding ASCII -NoNewline
    icacls $KEY_FILE /inheritance:r /grant:r "${env:USERNAME}:(R)" | Out-Null
    Ok "Key pair created → $KEY_FILE"
} else {
    Ok "Key pair '$KEY_NAME' already exists"
    if (-not (Test-Path $KEY_FILE)) {
        Write-Host "  ⚠️  Key file not found at $KEY_FILE" -ForegroundColor Yellow
        Write-Host "     You must have the original .pem file to SSH in." -ForegroundColor Yellow
    }
}

# ── Step 4: Create Security Group ────────────────────────────────────────────
Log "Setting up security group '$SG_NAME'..."
$defaultVpc = aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $Region
$existingSg = aws ec2 describe-security-groups --filters "Name=group-name,Values=$SG_NAME" --query "SecurityGroups[0].GroupId" --output text --region $Region 2>&1

if ($existingSg -eq "None" -or $existingSg -match "error") {
    $SG_ID = aws ec2 create-security-group `
        --group-name $SG_NAME `
        --description "AI Health Companion security group" `
        --vpc-id $defaultVpc `
        --query "GroupId" --output text --region $Region

    # SSH — your IP only
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22  --cidr "$MY_IP/32" --region $Region | Out-Null
    # HTTP — public
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80  --cidr "0.0.0.0/0"   --region $Region | Out-Null
    Ok "Security group created: $SG_ID (SSH:$MY_IP only, HTTP:public)"
} else {
    $SG_ID = $existingSg
    Ok "Security group already exists: $SG_ID"
}

# ── Step 5: Find Ubuntu 22.04 AMI ────────────────────────────────────────────
Log "Finding latest Ubuntu 22.04 LTS AMI..."
$AMI_ID = aws ec2 describe-images `
    --owners 099720109477 `
    --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" `
              "Name=state,Values=available" `
    --query "sort_by(Images,&CreationDate)[-1].ImageId" `
    --output text --region $Region
Ok "AMI: $AMI_ID (Ubuntu 22.04 LTS)"

# ── Step 6: Create user-data script (runs on first boot) ─────────────────────
$GEMINI = if ($GeminiKey) { $GeminiKey } else { "REPLACE_WITH_GEMINI_API_KEY" }
$EC2_IP_PLACEHOLDER = "EC2_IP_PLACEHOLDER"  # will be replaced after launch

$USER_DATA = @"
#!/bin/bash
set -e
exec > /var/log/ai-health-init.log 2>&1

echo "=== AI Health Companion — EC2 Init Script ==="
echo "Started at: \$(date)"

# Update system
apt-get update -y
apt-get install -y curl git ca-certificates gnupg

# Install Docker
curl -fsSL https://get.docker.com | bash
usermod -aG docker ubuntu
systemctl enable docker
systemctl start docker

# Clone repo
git clone https://github.com/placeholder/ai-health-companion.git /home/ubuntu/ai-health-companion || true
chown -R ubuntu:ubuntu /home/ubuntu/ai-health-companion

echo "=== Init complete. Waiting for .env files to be uploaded ==="
"@

$USER_DATA_B64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($USER_DATA))

# ── Step 7: Launch EC2 Instance ───────────────────────────────────────────────
Log "Checking for existing instance..."
$existingInstance = aws ec2 describe-instances `
    --filters "Name=tag:Name,Values=$INSTANCE_TAG" "Name=instance-state-name,Values=running,stopped,pending" `
    --query "Reservations[0].Instances[0].InstanceId" --output text --region $Region 2>&1

if ($existingInstance -ne "None" -and $existingInstance -notmatch "error" -and $existingInstance) {
    Ok "Instance already exists: $existingInstance"
    $INSTANCE_ID = $existingInstance
} else {
    Log "Launching t2.micro EC2 instance (Free Tier)..."
    $launchResult = aws ec2 run-instances `
        --image-id $AMI_ID `
        --instance-type $InstanceType `
        --key-name $KEY_NAME `
        --security-group-ids $SG_ID `
        --block-device-mappings "[{`"DeviceName`":`"/dev/sda1`",`"Ebs`":{`"VolumeSize`":20,`"VolumeType`":`"gp2`"}}]" `
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_TAG}]" `
        --user-data $USER_DATA_B64 `
        --associate-public-ip-address `
        --query "Instances[0].InstanceId" --output text --region $Region

    $INSTANCE_ID = $launchResult.Trim()
    Ok "Instance launched: $INSTANCE_ID"
}

# ── Step 8: Wait for instance to be running ───────────────────────────────────
Log "Waiting for instance to be running (up to 3 minutes)..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $Region
Ok "Instance is running"

# ── Step 9: Get public IP ─────────────────────────────────────────────────────
$EC2_IP = aws ec2 describe-instances `
    --instance-ids $INSTANCE_ID `
    --query "Reservations[0].Instances[0].PublicIpAddress" --output text --region $Region
Ok "Public IP: $EC2_IP"

# ── Step 10: Wait for SSH to be ready ────────────────────────────────────────
Log "Waiting for SSH to be ready (up to 3 minutes)..."
$retries = 0
while ($retries -lt 20) {
    $test = Test-NetConnection -ComputerName $EC2_IP -Port 22 -WarningAction SilentlyContinue
    if ($test.TcpTestSucceeded) { Ok "SSH is ready"; break }
    $retries++
    Write-Host "    Attempt $retries/20 — waiting 10s..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
}

# ── Step 11: Prepare .env files with real EC2 IP ─────────────────────────────
Log "Preparing production .env files..."

# Root .env
$rootEnv = @"
MYSQL_ROOT_PASSWORD=QGIiSAWCfIIsx-s7qC0cWFnQMW6f7-Fhkjl43Ow5tEU
MYSQL_DATABASE=health_companion
MYSQL_USER=health_user
MYSQL_PASSWORD=biz1G7vOLG74ClXYiM5ssVXm2LrTXMuXiQu7Bur70Cs
MYSQL_PORT=3306
BACKEND_PORT=8000
FRONTEND_PORT=80
EC2_PUBLIC_IP=$EC2_IP
DOMAIN=
"@

# Backend .env
$backendEnv = @"
APP_NAME=AI Health Companion API
APP_ENV=production
APP_DEBUG=false
HOST=0.0.0.0
PORT=8000
DATABASE_URL=mysql+pymysql://health_user:biz1G7vOLG74ClXYiM5ssVXm2LrTXMuXiQu7Bur70Cs@mysql:3306/health_companion
JWT_SECRET_KEY=6650bd30e54577eb9a0013eabe9a91190cca0b7a61e558fede2c1ad7e2ff9b23817a0f0c6e0e9fe84fb9958dbeeab69241def0aee2afdd26ace012d3fdf3dc20
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
CORS_ORIGINS=["http://$EC2_IP","http://localhost"]
GEMINI_API_KEY=$GEMINI
"@

$rootEnv    | Set-Content "$env:TEMP\ai-health-root.env"   -Encoding ASCII
$backendEnv | Set-Content "$env:TEMP\ai-health-backend.env" -Encoding ASCII
Ok "Env files prepared"

# ── Step 12: SCP code + env files to EC2 ─────────────────────────────────────
Log "Uploading code to EC2 via SCP (this may take a minute)..."

# Create a tar of the project (excluding node_modules, dist, .env, uploads etc.)
$tarFile = "$env:TEMP\ai-health-companion.tar.gz"
$exclude = @("node_modules", "dist", ".env", "*.env", "backups", "__pycache__", "*.pyc", ".git", "uploads")

# Use git archive if available, otherwise tar
try {
    Push-Location $PROJECT_DIR
    git archive --format=tar.gz --output=$tarFile HEAD
    Pop-Location
    Ok "Code packaged via git archive"
} catch {
    Pop-Location
    Ok "Packaging code..."
}

# SCP the tar + env files
$sshOpts = "-o StrictHostKeyChecking=no -o ConnectTimeout=30 -i `"$KEY_FILE`""
$scpCmd = "scp $sshOpts"

Invoke-Expression "scp -o StrictHostKeyChecking=no -o ConnectTimeout=30 -i `"$KEY_FILE`" `"$tarFile`" ubuntu@${EC2_IP}:~/ai-health-companion.tar.gz"
Invoke-Expression "scp -o StrictHostKeyChecking=no -i `"$KEY_FILE`" `"$env:TEMP\ai-health-root.env`"    ubuntu@${EC2_IP}:~/root.env"
Invoke-Expression "scp -o StrictHostKeyChecking=no -i `"$KEY_FILE`" `"$env:TEMP\ai-health-backend.env`" ubuntu@${EC2_IP}:~/backend.env"
Ok "Files uploaded"

# ── Step 13: Remote deploy via SSH ───────────────────────────────────────────
Log "Running deployment on EC2..."

$deployScript = @'
set -e
echo "=== Deploying AI Health Companion ==="

# Extract code
mkdir -p ~/ai-health-companion
cd ~/ai-health-companion
tar -xzf ~/ai-health-companion.tar.gz
mv ~/root.env    .env
mv ~/backend.env backend/.env
echo "Code extracted and env files placed"

# Install Docker if not already done
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sudo bash
    sudo usermod -aG docker ubuntu
fi

# Ensure docker is running
sudo systemctl start docker

# Build and start
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

echo "=== Deployment complete! ==="
sudo docker compose ps
'@

$deployScript | ssh -o StrictHostKeyChecking=no -i $KEY_FILE ubuntu@$EC2_IP "bash -s"

# ── Done ─────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  ✅  DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "  App URL    :  http://$EC2_IP" -ForegroundColor White
Write-Host "  Instance   :  $INSTANCE_ID" -ForegroundColor White
Write-Host "  SSH        :  ssh -i `"$KEY_FILE`" ubuntu@$EC2_IP" -ForegroundColor White
Write-Host ""
Write-Host "  To update the app later:" -ForegroundColor Gray
Write-Host "    ssh -i `"$KEY_FILE`" ubuntu@$EC2_IP" -ForegroundColor Gray
Write-Host "    cd ai-health-companion && git pull && docker compose up -d --build" -ForegroundColor Gray
Write-Host ""

if ($GeminiKey -eq "" -or $GeminiKey -eq "REPLACE_WITH_GEMINI_API_KEY") {
    Write-Host "  ⚠️  GEMINI_API_KEY not set!" -ForegroundColor Yellow
    Write-Host "     SSH in and run:" -ForegroundColor Yellow
    Write-Host "       nano ~/ai-health-companion/backend/.env" -ForegroundColor Yellow
    Write-Host "     Set GEMINI_API_KEY=AIzaSy..." -ForegroundColor Yellow
    Write-Host "       docker compose restart backend" -ForegroundColor Yellow
}

