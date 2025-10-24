# Test Agent Registry Endpoints
# Tests /agents/register, /agents, and /agents/:id/chat

$BaseUrl = "https://api.getbrikk.com"

Write-Host "Testing Agent Registry Endpoints..." -ForegroundColor Cyan
Write-Host ""

# Test 1: List all agents
Write-Host "Test 1: List all agents" -ForegroundColor Yellow
Write-Host "GET $BaseUrl/agents" -ForegroundColor Gray

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/agents" -Method GET
    
    Write-Host "✓ List agents passed" -ForegroundColor Green
    Write-Host "Found $($response.count) agents" -ForegroundColor Gray
    Write-Host ""
    
    foreach ($agent in $response.agents) {
        Write-Host "  - $($agent.name) ($($agent.id))" -ForegroundColor Cyan
    }
    Write-Host ""
    
} catch {
    Write-Host "✗ List agents failed" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 2: Chat with OpenAI agent
Write-Host "Test 2: Chat with OpenAI agent" -ForegroundColor Yellow
Write-Host "POST $BaseUrl/agents/openai/chat" -ForegroundColor Gray

$chatBody = @{
    message = "Say hello in one sentence"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/agents/openai/chat" -Method POST -Body $chatBody -ContentType "application/json"
    
    if ($response.ok -eq $true) {
        Write-Host "✓ Chat with OpenAI passed" -ForegroundColor Green
        Write-Host "Latency: $($response.latency_ms)ms" -ForegroundColor Gray
        Write-Host "Response: $($response.result.output)" -ForegroundColor Cyan
        Write-Host ""
    } else {
        Write-Host "✗ Chat with OpenAI failed" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "✗ Chat with OpenAI failed" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 3: Chat with Manus agent
Write-Host "Test 3: Chat with Manus agent" -ForegroundColor Yellow
Write-Host "POST $BaseUrl/agents/manus/chat" -ForegroundColor Gray

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/agents/manus/chat" -Method POST -Body $chatBody -ContentType "application/json"
    
    if ($response.ok -eq $true) {
        Write-Host "✓ Chat with Manus passed" -ForegroundColor Green
        Write-Host "Latency: $($response.latency_ms)ms" -ForegroundColor Gray
        Write-Host "Response: $($response.result.result)" -ForegroundColor Cyan
        Write-Host ""
    } else {
        Write-Host "✗ Chat with Manus failed" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "✗ Chat with Manus failed" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "All registry tests passed! ✓" -ForegroundColor Green

