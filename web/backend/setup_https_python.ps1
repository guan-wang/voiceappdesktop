# Generate self-signed SSL certificate using Python (no OpenSSL needed)
Write-Host ""
Write-Host "🔐 Setting Up HTTPS Using Python" -ForegroundColor Cyan
Write-Host "=" -NoNewline; Write-Host ("=" * 60)
Write-Host ""

$pythonScript = @"
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import ipaddress

# Generate private key
print("🔑 Generating private key...")
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

# Generate certificate
print("📜 Generating certificate...")
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
])

cert = x509.CertificateBuilder().subject_name(
    subject
).issuer_name(
    issuer
).public_key(
    private_key.public_key()
).serial_number(
    x509.random_serial_number()
).not_valid_before(
    datetime.datetime.utcnow()
).not_valid_after(
    datetime.datetime.utcnow() + datetime.timedelta(days=365)
).add_extension(
    x509.SubjectAlternativeName([
        x509.DNSName(u"localhost"),
        x509.IPAddress(ipaddress.IPv4Address(u"127.0.0.1")),
        x509.IPAddress(ipaddress.IPv4Address(u"192.168.45.151")),
        x509.IPAddress(ipaddress.IPv4Address(u"10.5.0.2")),
    ]),
    critical=False,
).sign(private_key, hashes.SHA256())

# Write private key
print("💾 Saving key.pem...")
with open("key.pem", "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))

# Write certificate
print("💾 Saving cert.pem...")
with open("cert.pem", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print("✅ Done!")
"@

# Save Python script temporarily
$tempScript = ".\generate_cert_temp.py"
$pythonScript | Out-File -FilePath $tempScript -Encoding UTF8

try {
    Write-Host "🐍 Running Python script to generate certificates..." -ForegroundColor Cyan
    Write-Host ""
    
    # Try to run with uv first (project's package manager)
    $uvAvailable = $null -ne (Get-Command uv -ErrorAction SilentlyContinue)
    
    if ($uvAvailable) {
        Write-Host "Using uv run..." -ForegroundColor Gray
        uv run python $tempScript
    } else {
        Write-Host "Using python..." -ForegroundColor Gray
        python $tempScript
    }
    
    if ((Test-Path ".\cert.pem") -and (Test-Path ".\key.pem")) {
        Write-Host ""
        Write-Host "✅ Certificates generated successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "   Certificate: cert.pem" -ForegroundColor White
        Write-Host "   Private Key: key.pem" -ForegroundColor White
        Write-Host ""
        Write-Host "📱 Access from phone using HTTPS:" -ForegroundColor Cyan
        Write-Host "   https://192.168.45.151:7860" -ForegroundColor Green
        Write-Host ""
        Write-Host "⚠️  Important: You'll see a security warning" -ForegroundColor Yellow
        Write-Host "   (because it's self-signed - this is normal for local dev)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "   On the warning page:" -ForegroundColor White
        Write-Host "   - iOS Safari: Tap 'Show Details' → 'visit this website'" -ForegroundColor Gray
        Write-Host "   - Android Chrome: Tap 'Advanced' → 'Proceed to ... (unsafe)'" -ForegroundColor Gray
        Write-Host ""
        Write-Host "🚀 Now restart the server:" -ForegroundColor Cyan
        Write-Host "   .\stop_server.ps1" -ForegroundColor White
        Write-Host "   .\start_server.ps1" -ForegroundColor White
        Write-Host ""
    } else {
        throw "Certificate files were not created"
    }
    
} catch {
    Write-Host ""
    Write-Host "❌ Failed to generate certificates" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure cryptography package is installed:" -ForegroundColor Yellow
    Write-Host "   uv pip install cryptography" -ForegroundColor White
    Write-Host ""
    exit 1
} finally {
    # Clean up temp script
    if (Test-Path $tempScript) {
        Remove-Item $tempScript -Force
    }
}

Write-Host "=" -NoNewline; Write-Host ("=" * 60)
Write-Host ""
