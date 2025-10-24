# Test Agent Bridge Endpoint
# Tests /agents/bridge with multi-turn conversation

$BaseUrl = "https://api.getbrikk.com"
$Endpoint = "$BaseUrl/agents/bridge"

Write-Host "Testing Agent Bridge Endpoint..." -ForegroundColor Cyan
Write-Host "URL: $Endpoint" -ForegroundColor Gray
Write-Host ""

$body = @{
    from = "openai"
    to = "manus"
    message = "Ping from OpenAI"
    maxTurns = 2
} | ConvertTo-Json

Write-Host "Request Body:" -ForegroundColor Yellow
Write-Host $body
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri $Endpoint -Method POST -Body $body -ContentType "application/json"
    
    if ($response.ok -eq $true) {
        Write-Host "✓ Agent bridge test passed" -ForegroundColor Green
        Write-Host ""
        Write-Host "Summary:" -ForegroundColor Yellow
        Write-Host "  Total Turns: $($response.total_turns)" -ForegroundColor Cyan
        Write-Host "  Total Latency: $($response.total_latency_ms)ms" -ForegroundColor Cyan
        Write-Host "  Request ID: $($response.request_id)" -ForegroundColor Gray
        Write-Host ""
        
        Write-Host "Transcript:" -ForegroundColor Yellow
        Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Gray
        
        foreach ($turn in $response.transcript) {
            Write-Host ""
            Write-Host "Turn $($turn.turn + 1): $($turn.from) → $($turn.to) [$($turn.latency_ms)ms]" -ForegroundColor Magenta
            Write-Host "Message: $($turn.message)" -ForegroundColor White
            Write-Host "Response: $($turn.response)" -ForegroundColor Cyan
        }
        
        Write-Host ""
        Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Full JSON Response:" -ForegroundColor Yellow
        $response | ConvertTo-Json -Depth 5
        
    } else {
        Write-Host "✗ Agent bridge returned error" -ForegroundColor Red
        Write-Host "Error: $($response.error)" -ForegroundColor Red
        Write-Host "Response: $($response | ConvertTo-Json -Depth 5)" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "✗ Agent bridge test failed" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
    
    exit 1
}

