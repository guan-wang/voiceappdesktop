# Get local IP address for accessing from phone
Write-Host ""
Write-Host "📱 Access from Phone - Network Info" -ForegroundColor Cyan
Write-Host "=" -NoNewline; Write-Host ("=" * 50)
Write-Host ""

# Get IPv4 addresses
$ipAddresses = Get-NetIPAddress -AddressFamily IPv4 | 
    Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.254.*" } |
    Select-Object IPAddress, InterfaceAlias

if ($ipAddresses) {
    Write-Host "🌐 Your Computer's IP Address(es):" -ForegroundColor Green
    Write-Host ""
    
    foreach ($ip in $ipAddresses) {
        $addr = $ip.IPAddress
        $iface = $ip.InterfaceAlias
        Write-Host "   Interface: $iface" -ForegroundColor Yellow
        Write-Host "   IP Address: $addr" -ForegroundColor White
        Write-Host ""
        Write-Host "   📱 Access from phone:" -ForegroundColor Cyan
        Write-Host "   http://${addr}:7860" -ForegroundColor Green
        Write-Host ""
    }
    
    Write-Host "📝 Instructions:" -ForegroundColor Yellow
    Write-Host "   1. Make sure your phone is on the SAME WiFi network"
    Write-Host "   2. Open a browser on your phone"
    Write-Host "   3. Type the URL above (use the WiFi adapter IP)"
    Write-Host "   4. If blocked, check Windows Firewall settings"
    Write-Host ""
    
} else {
    Write-Host "❌ No network adapters found" -ForegroundColor Red
    Write-Host "   Make sure you're connected to WiFi or Ethernet" -ForegroundColor Yellow
}

Write-Host "=" -NoNewline; Write-Host ("=" * 50)
Write-Host ""
