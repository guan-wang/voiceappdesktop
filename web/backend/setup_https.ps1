# Generate self-signed SSL certificate for local HTTPS development
Write-Host ""
Write-Host "🔐 Setting Up HTTPS for Mobile Development" -ForegroundColor Cyan
Write-Host "=" -NoNewline; Write-Host ("=" * 60)
Write-Host ""

$certPath = ".\cert.pem"
$keyPath = ".\key.pem"

# Check if OpenSSL is available
$opensslAvailable = $null -ne (Get-Command openssl -ErrorAction SilentlyContinue)

if (-not $opensslAvailable) {
    Write-Host "❌ OpenSSL not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "OpenSSL is required to generate certificates." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  1. Install OpenSSL:" -ForegroundColor White
    Write-Host "     - Download from: https://slproweb.com/products/Win32OpenSSL.html" -ForegroundColor Gray
    Write-Host "     - Or use: winget install OpenSSL.OpenSSL" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Use Python to generate certificate instead:" -ForegroundColor White
    Write-Host "     .\setup_https_python.ps1" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

# Check if certificates already exist
if ((Test-Path $certPath) -and (Test-Path $keyPath)) {
    Write-Host "✅ Certificates already exist:" -ForegroundColor Green
    Write-Host "   - $certPath" -ForegroundColor White
    Write-Host "   - $keyPath" -ForegroundColor White
    Write-Host ""
    
    $response = Read-Host "Regenerate certificates? (y/N)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Host "Keeping existing certificates." -ForegroundColor Yellow
        exit 0
    }
    
    Remove-Item $certPath -Force
    Remove-Item $keyPath -Force
}

Write-Host "🔨 Generating self-signed certificate..." -ForegroundColor Cyan
Write-Host ""

# Generate certificate valid for 365 days
$command = @"
openssl req -x509 -newkey rsa:4096 -nodes `
    -keyout $keyPath `
    -out $certPath `
    -days 365 `
    -subj "/CN=localhost" `
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:192.168.45.151,IP:10.5.0.2"
"@

try {
    Invoke-Expression $command 2>&1 | Out-Null
    
    if ((Test-Path $certPath) -and (Test-Path $keyPath)) {
        Write-Host "✅ Certificates generated successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "   Certificate: $certPath" -ForegroundColor White
        Write-Host "   Private Key: $keyPath" -ForegroundColor White
        Write-Host ""
        Write-Host "📱 Access from phone using HTTPS:" -ForegroundColor Cyan
        Write-Host "   https://192.168.45.151:7860" -ForegroundColor Green
        Write-Host ""
        Write-Host "⚠️  Important: You'll see a security warning" -ForegroundColor Yellow
        Write-Host "   (because it's self-signed)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "   On the warning page:" -ForegroundColor White
        Write-Host "   - iOS Safari: Click 'Show Details' → 'visit this website'" -ForegroundColor Gray
        Write-Host "   - Chrome: Click 'Advanced' → 'Proceed to ... (unsafe)'" -ForegroundColor Gray
        Write-Host ""
        Write-Host "🚀 Now restart the server:" -ForegroundColor Cyan
        Write-Host "   .\stop_server.ps1" -ForegroundColor White
        Write-Host "   .\start_server.ps1" -ForegroundColor White
        Write-Host ""
        
    } else {
        throw "Certificate files not created"
    }
    
} catch {
    Write-Host "❌ Failed to generate certificates" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Try the Python method instead:" -ForegroundColor Yellow
    Write-Host "   .\setup_https_python.ps1" -ForegroundColor White
    exit 1
}

Write-Host "=" -NoNewline; Write-Host ("=" * 60)
Write-Host ""
