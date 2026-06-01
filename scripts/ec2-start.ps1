
# ─────────────────────────────────────────────────────────────────
#  EC2 START + AUTO-REDEPLOY Script
#  Run: .\scripts\ec2-start.ps1
# ─────────────────────────────────────────────────────────────────

$env:Path = "C:\Program Files\Amazon\AWSCLIV2;" + $env:Path
$INSTANCE_ID = "i-02ae99f74353bf2a5"
$KEY         = "$env:USERPROFILE\.ssh\ai-health-key.pem"

function Log($msg)  { Write-Host "  $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "  OK  $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  !!  $msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "=================================================" -ForegroundColor White
Write-Host "   AI Health Companion - START EC2" -ForegroundColor White
Write-Host "=================================================" -ForegroundColor White
Write-Host ""

# ── Step 1: Start instance ────────────────────────────────────────
Log "Starting EC2 instance $INSTANCE_ID ..."
$state = aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[0].Instances[0].State.Name" --output text
if ($state -eq "running") {
    Warn "Instance is already running!"
} else {
    aws ec2 start-instances --instance-ids $INSTANCE_ID | Out-Null
    Ok "Start command sent!"
}

# ── Step 2: Wait for running state ───────────────────────────────
Log "Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID
Ok "Instance is RUNNING!"

# ── Step 3: Get public IP ─────────────────────────────────────────
$IP = aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[0].Instances[0].PublicIpAddress" --output text
Ok "Public IP: $IP"

# ── Step 4: Wait for SSH ──────────────────────────────────────────
Log "Waiting for SSH to be ready (up to 60s)..."
$ready = $false
for ($i = 0; $i -lt 12; $i++) {
    $result = ssh -i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=5 ubuntu@$IP "echo OK" 2>$null
    if ($result -eq "OK") { $ready = $true; break }
    Write-Host "    SSH not ready yet, retrying..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
}
if (-not $ready) { Write-Host "  SSH timeout - try again in 30s" -ForegroundColor Red; exit 1 }
Ok "SSH is ready!"

# ── Step 5: Start Docker containers ──────────────────────────────
Log "Starting Docker containers..."
ssh -i $KEY -o StrictHostKeyChecking=no ubuntu@$IP @"
cd ~/ai-health-companion
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
sleep 15
docker ps --format 'table {{.Names}}\t{{.Status}}'
"@

# ── Step 6: Done ──────────────────────────────────────────────────
Write-Host ""
Write-Host "=================================================" -ForegroundColor Green
Write-Host "   APP IS LIVE!" -ForegroundColor Green
Write-Host "   http://$IP" -ForegroundColor Green
Write-Host "   API Docs: http://$IP/api/v1/docs" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green
Write-Host ""

