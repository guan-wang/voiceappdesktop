# Stop the Korean Voice Tutor web server
# Kills any process using port 8080

Write-Host "🔍 Looking for server on port 8080..." -ForegroundColor Cyan

$connections = netstat -ano | Select-String ":8080" | Select-String "LISTENING"

if ($connections) {
    $connections | ForEach-Object {
        $line = $_.Line
        $pid = ($line -split '\s+')[-1]
        
        Write-Host "📍 Found server process: PID $pid" -ForegroundColor Yellow
        Write-Host "🛑 Stopping server..." -ForegroundColor Red
        
        taskkill /PID $pid /F | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Server stopped successfully!" -ForegroundColor Green
        } else {
            Write-Host "❌ Failed to stop server" -ForegroundColor Red
        }
    }
} else {
    Write-Host "✅ No server running on port 8080" -ForegroundColor Green
}

Write-Host "`n📝 You can now start the server with: uv run python server.py" -ForegroundColor Cyan
