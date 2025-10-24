# Test OpenAI Relay Endpoint
# Tests the /agents/openai/chat endpoint

$BaseUrl = "https://api.getbrikk.com"
$Endpoint = "$BaseUrl/agents/openai/chat"

Write-Host "Testing OpenAI Relay Endpoint..." -ForegroundColor Cyan
Write-Host "URL: $Endpoint" -ForegroundColor Gray
Write-Host ""

$body = @{
    message = "Hello from Brikk test"
} | ConvertTo-Json

Write-Host "Request Body:" -ForegroundColor Yellow
Write-Host $body
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri $Endpoint -Method POST -Body $body -ContentType "application/json"
    
    if ($response.ok -eq $true) {
        Write-Host "✓ OpenAI relay test passed" -ForegroundColor Green
        Write-Host ""
        Write-Host "Response:" -ForegroundColor Yellow
        $response | ConvertTo-Json -Depth 3
    } else {
        Write-Host "✗ OpenAI relay returned error" -ForegroundColor Red
        Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "✗ OpenAI relay test failed" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

