# Allow port 7860 through Windows Firewall
# Note: This requires Administrator privileges

Write-Host ""
Write-Host "🔥 Windows Firewall Configuration" -ForegroundColor Cyan
Write-Host "=" -NoNewline; Write-Host ("=" * 50)
Write-Host ""

$ruleName = "Korean Voice Tutor Web App (Port 8080)"

# Check if rule already exists
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "✅ Firewall rule already exists: $ruleName" -ForegroundColor Green
    Write-Host ""
    Write-Host "   To remove it, run:" -ForegroundColor Yellow
    Write-Host "   Remove-NetFirewallRule -DisplayName '$ruleName'" -ForegroundColor White
} else {
    try {
        # Create firewall rule for inbound connections on port 8080
        New-NetFirewallRule `
            -DisplayName $ruleName `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort 8080 `
            -Action Allow `
            -Profile Any `
            -ErrorAction Stop | Out-Null
        
        Write-Host "✅ Firewall rule created successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "   Rule Name: $ruleName" -ForegroundColor White
        Write-Host "   Port: 8080" -ForegroundColor White
        Write-Host "   Direction: Inbound" -ForegroundColor White
        Write-Host "   Action: Allow" -ForegroundColor White
        Write-Host ""
        Write-Host "📱 You can now access the app from your phone!" -ForegroundColor Cyan
        
    } catch {
        Write-Host "❌ Failed to create firewall rule" -ForegroundColor Red
        Write-Host ""
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Write-Host "   Possible reasons:" -ForegroundColor Yellow
        Write-Host "   1. Not running as Administrator" -ForegroundColor White
        Write-Host "   2. Firewall is disabled" -ForegroundColor White
        Write-Host ""
        Write-Host "   To run as Administrator:" -ForegroundColor Yellow
        Write-Host "   Right-click PowerShell → Run as Administrator" -ForegroundColor White
        Write-Host "   cd web\backend" -ForegroundColor White
        Write-Host "   .\allow_firewall.ps1" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 50)
Write-Host ""
