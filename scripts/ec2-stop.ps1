
# ─────────────────────────────────────────────────────────────────
#  EC2 STOP Script  (stops containers first, then the instance)
#  Run: .\scripts\ec2-stop.ps1
# ─────────────────────────────────────────────────────────────────

$env:Path = "C:\Program Files\Amazon\AWSCLIV2;" + $env:Path
$INSTANCE_ID = "i-02ae99f74353bf2a5"
$KEY         = "$env:USERPROFILE\.ssh\ai-health-key.pem"

function Log($msg)  { Write-Host "  $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "  OK  $msg" -ForegroundColor Green }

Write-Host ""
Write-Host "=================================================" -ForegroundColor White
Write-Host "   AI Health Companion - STOP EC2" -ForegroundColor White
Write-Host "=================================================" -ForegroundColor White
Write-Host ""

# ── Step 1: Check state ───────────────────────────────────────────
$state = aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[0].Instances[0].State.Name" --output text
if ($state -ne "running") {
    Write-Host "  Instance is already $state - nothing to do." -ForegroundColor Yellow
    exit 0
}

$IP = aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[0].Instances[0].PublicIpAddress" --output text
Log "Instance IP: $IP  |  State: $state"

# ── Step 2: Gracefully stop Docker containers ─────────────────────
Log "Stopping Docker containers gracefully..."
ssh -i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=10 ubuntu@$IP `
    "cd ~/ai-health-companion && docker compose down" 2>$null
Ok "Containers stopped!"

# ── Step 3: Stop EC2 instance ─────────────────────────────────────
Log "Stopping EC2 instance (data is PRESERVED)..."
aws ec2 stop-instances --instance-ids $INSTANCE_ID | Out-Null
aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID
Ok "EC2 instance STOPPED!"

Write-Host ""
Write-Host "=================================================" -ForegroundColor Green
Write-Host "   INSTANCE STOPPED - $0 compute cost now" -ForegroundColor Green
Write-Host "   Data & volumes are PRESERVED" -ForegroundColor Green
Write-Host "   Run ec2-start.ps1 to bring it back up" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green
Write-Host ""

