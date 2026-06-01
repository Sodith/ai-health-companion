
# ─────────────────────────────────────────────────────────────────
#  EC2 STATUS Script  - check everything at a glance
#  Run: .\scripts\ec2-status.ps1
# ─────────────────────────────────────────────────────────────────

$env:Path = "C:\Program Files\Amazon\AWSCLIV2;" + $env:Path
$INSTANCE_ID = "i-02ae99f74353bf2a5"
$KEY         = "$env:USERPROFILE\.ssh\ai-health-key.pem"

Write-Host ""
Write-Host "=================================================" -ForegroundColor White
Write-Host "   AI Health Companion - STATUS CHECK" -ForegroundColor White
Write-Host "=================================================" -ForegroundColor White
Write-Host ""

# EC2 State
$info  = aws ec2 describe-instances --instance-ids $INSTANCE_ID `
         --query "Reservations[0].Instances[0].{State:State.Name,IP:PublicIpAddress,Type:InstanceType}" `
         --output json | ConvertFrom-Json

$state = $info.State
$IP    = $info.IP
$type  = $info.Type

$color = if ($state -eq "running") { "Green" } elseif ($state -eq "stopped") { "Yellow" } else { "Red" }
Write-Host "  EC2 Instance : $INSTANCE_ID" -ForegroundColor White
Write-Host "  Type         : $type (Free Tier)" -ForegroundColor White
Write-Host "  State        : $state" -ForegroundColor $color
Write-Host "  Public IP    : $IP" -ForegroundColor White

if ($state -eq "running" -and $IP) {

    Write-Host ""
    Write-Host "  Docker Containers:" -ForegroundColor White
    ssh -i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=8 ubuntu@$IP `
        "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null" 2>$null

    Write-Host ""
    Write-Host "  Memory Usage:" -ForegroundColor White
    ssh -i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=8 ubuntu@$IP `
        "free -m | grep -E 'Mem|Swap'" 2>$null

    Write-Host ""
    Write-Host "  App URLs:" -ForegroundColor Green
    Write-Host "   Frontend : http://$IP" -ForegroundColor Green
    Write-Host "   API Docs : http://$IP/api/v1/docs" -ForegroundColor Green
}

Write-Host ""
Write-Host "=================================================" -ForegroundColor White
Write-Host ""

