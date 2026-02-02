# Start the Korean Voice Tutor web server
# Checks if port is in use first

Write-Host "🔍 Checking if port 8080 is available..." -ForegroundColor Cyan

$connections = netstat -ano | Select-String ":8080" | Select-String "LISTENING"

if ($connections) {
    Write-Host "⚠️  Port 8080 is already in use!" -ForegroundColor Yellow
    Write-Host "📝 Run: .\stop_server.ps1 to stop the existing server" -ForegroundColor Cyan
    exit 1
}

Write-Host "✅ Port 8080 is available" -ForegroundColor Green
Write-Host "🚀 Starting Korean Voice Tutor Web Server..." -ForegroundColor Cyan
Write-Host "📱 Open https://localhost:8080 in your browser" -ForegroundColor Green
Write-Host "🛑 Press Ctrl+C to stop the server`n" -ForegroundColor Yellow

# Use uv run to automatically manage environment and dependencies
uv run python server.py
