# Test Health Endpoint
# Tests the /health endpoint to verify API is running

$BaseUrl = "https://api.getbrikk.com"

Write-Host "Testing Health Endpoint..." -ForegroundColor Cyan
Write-Host "URL: $BaseUrl/health" -ForegroundColor Gray
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET
    
    Write-Host "✓ Health check passed" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Yellow
    $response | ConvertTo-Json -Depth 3
    
} catch {
    Write-Host "✗ Health check failed" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

