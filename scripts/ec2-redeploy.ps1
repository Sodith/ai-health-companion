
# ─────────────────────────────────────────────────────────────────
#  EC2 REDEPLOY Script  - pull latest code & rebuild containers
#  Run: .\scripts\ec2-redeploy.ps1
# ─────────────────────────────────────────────────────────────────

$env:Path = "C:\Program Files\Amazon\AWSCLIV2;" + $env:Path
$INSTANCE_ID = "i-02ae99f74353bf2a5"
$KEY         = "$env:USERPROFILE\.ssh\ai-health-key.pem"

function Log($msg) { Write-Host "  $msg" -ForegroundColor Cyan }
function Ok($msg)  { Write-Host "  OK  $msg" -ForegroundColor Green }

Write-Host ""
Write-Host "=================================================" -ForegroundColor White
Write-Host "   AI Health Companion - REDEPLOY" -ForegroundColor White
Write-Host "=================================================" -ForegroundColor White
Write-Host ""

$IP = aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[0].Instances[0].PublicIpAddress" --output text
$state = aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[0].Instances[0].State.Name" --output text

if ($state -ne "running") {
    Write-Host "  Instance is $state. Run ec2-start.ps1 first!" -ForegroundColor Red
    exit 1
}

Log "Pulling latest code from GitHub..."
ssh -i $KEY -o StrictHostKeyChecking=no ubuntu@$IP "cd ~/ai-health-companion && git fetch origin && git reset --hard origin/main"
Ok "Code updated!"

Log "Rebuilding and restarting containers (this takes 2-3 min)..."
ssh -i $KEY -o StrictHostKeyChecking=no ubuntu@$IP @"
cd ~/ai-health-companion
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
sleep 20
docker ps --format 'table {{.Names}}\t{{.Status}}'
"@

Write-Host ""
Ok "Redeploy complete!"
Write-Host "  http://$IP" -ForegroundColor Green
Write-Host ""

