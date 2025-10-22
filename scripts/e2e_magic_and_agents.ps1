#!/usr/bin/env pwsh
<#
.SYNOPSIS
    E2E validation script for magic link authentication and agent execution

.DESCRIPTION
    This script tests the complete flow:
    1. Generates a magic link using admin token
    2. Verifies the magic link token works
    3. Executes all three demo agents via API
    4. Validates responses and collects request IDs

.PARAMETER AdminToken
    Admin token for magic link generation (defaults to BRIKK_ADMIN_TOKEN env var)

.PARAMETER ApiBase
    Base URL for the API (defaults to https://api.getbrikk.com)

.EXAMPLE
    ./e2e_magic_and_agents.ps1
    
.EXAMPLE
    ./e2e_magic_and_agents.ps1 -AdminToken "your-admin-token" -ApiBase "https://api.getbrikk.com"
#>

param(
    [string]$AdminToken = $env:BRIKK_ADMIN_TOKEN,
    [string]$ApiBase = "https://api.getbrikk.com"
)

# Color output functions
function Write-Success { param([string]$Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Error { param([string]$Message) Write-Host "❌ $Message" -ForegroundColor Red }
function Write-Info { param([string]$Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warning { param([string]$Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }

# Validate inputs
if (-not $AdminToken) {
    Write-Error "Admin token is required. Set BRIKK_ADMIN_TOKEN environment variable or pass -AdminToken parameter"
    exit 1
}

Write-Info "Starting E2E validation for Brikk Platform"
Write-Info "API Base: $ApiBase"
Write-Host ""

# Track results
$results = @{
    MagicLinkGeneration = $false
    TokenVerification = $false
    ApiKeyRetrieval = $false
    CsvAnalyzer = $false
    EmailSummarizer = $false
    CodeReviewer = $false
    RequestIds = @()
}

# Step 1: Generate magic link
Write-Info "Step 1: Generating magic link..."
try {
    $magicLinkBody = @{
        user_id = "e2e_test_user_$(Get-Date -Format 'yyyyMMddHHmmss')"
        email = "e2e-test@example.com"
        org_id = "beta_e2e_test"
        scopes = @("demo_portal", "demo_playground")
    } | ConvertTo-Json

    $magicLinkResponse = Invoke-RestMethod `
        -Uri "$ApiBase/api/v1/access/magic-link" `
        -Method Post `
        -Headers @{
            "Authorization" = "Bearer $AdminToken"
            "Content-Type" = "application/json"
        } `
        -Body $magicLinkBody

    if ($magicLinkResponse.success) {
        Write-Success "Magic link generated successfully"
        Write-Info "  Portal URL: $($magicLinkResponse.portal_url.Substring(0, 80))..."
        Write-Info "  Expires: $($magicLinkResponse.expires_at)"
        Write-Info "  Request ID: $($magicLinkResponse.request_id)"
        $results.RequestIds += $magicLinkResponse.request_id
        $results.MagicLinkGeneration = $true
        
        # Extract token from URL
        $token = $magicLinkResponse.portal_url -replace '.*#token=', ''
        Write-Info "  Token extracted: $($token.Substring(0, 20))..."
    } else {
        Write-Error "Failed to generate magic link: $($magicLinkResponse.error)"
        exit 1
    }
} catch {
    Write-Error "Exception during magic link generation: $_"
    Write-Error $_.Exception.Message
    exit 1
}

Write-Host ""

# Step 2: Verify token with /access/me
Write-Info "Step 2: Verifying token with /access/me..."
try {
    $meResponse = Invoke-RestMethod `
        -Uri "$ApiBase/api/v1/access/me" `
        -Method Get `
        -Headers @{
            "Authorization" = "Bearer $token"
        }

    if ($meResponse.success) {
        Write-Success "Token verified successfully"
        Write-Info "  User ID: $($meResponse.user.id)"
        Write-Info "  Email: $($meResponse.user.email)"
        Write-Info "  Org ID: $($meResponse.user.org_id)"
        Write-Info "  Request ID: $($meResponse.request_id)"
        $results.RequestIds += $meResponse.request_id
        $results.TokenVerification = $true
    } else {
        Write-Error "Token verification failed: $($meResponse.error)"
        exit 1
    }
} catch {
    Write-Error "Exception during token verification: $_"
    Write-Error $_.Exception.Message
    exit 1
}

Write-Host ""

# Step 3: Get API key
Write-Info "Step 3: Retrieving API key..."
try {
    $apiKeyResponse = Invoke-RestMethod `
        -Uri "$ApiBase/api/v1/usage/api-key" `
        -Method Get `
        -Headers @{
            "Authorization" = "Bearer $token"
        }

    if ($apiKeyResponse.success) {
        Write-Success "API key retrieved successfully"
        $apiKey = $apiKeyResponse.api_key
        Write-Info "  API Key: $($apiKey.Substring(0, 15))..."
        Write-Info "  Created: $($apiKeyResponse.created_at)"
        $results.ApiKeyRetrieval = $true
    } else {
        Write-Error "Failed to retrieve API key: $($apiKeyResponse.error)"
        exit 1
    }
} catch {
    Write-Error "Exception during API key retrieval: $_"
    Write-Error $_.Exception.Message
    exit 1
}

Write-Host ""

# Step 4: Test CSV Analyzer agent
Write-Info "Step 4: Testing CSV Analyzer agent..."
try {
    $csvInput = @{
        agent_id = "csv-analyzer"
        input = @{
            file_url = "https://example.com/sales-data.csv"
            analyze = @("trends", "outliers")
        }
    } | ConvertTo-Json -Depth 10

    $csvResponse = Invoke-RestMethod `
        -Uri "$ApiBase/api/v1/marketplace/agents/call" `
        -Method Post `
        -Headers @{
            "X-API-Key" = $apiKey
            "Content-Type" = "application/json"
        } `
        -Body $csvInput

    if ($csvResponse.success) {
        Write-Success "CSV Analyzer executed successfully"
        Write-Info "  Execution time: $($csvResponse.execution_time_ms)ms"
        Write-Info "  Request ID: $($csvResponse.request_id)"
        Write-Info "  Result keys: $($csvResponse.result.PSObject.Properties.Name -join ', ')"
        $results.RequestIds += $csvResponse.request_id
        $results.CsvAnalyzer = $true
        
        # Validate response structure
        if ($csvResponse.result.summary -and $csvResponse.result.insights) {
            Write-Success "  Response structure valid (has summary and insights)"
        } else {
            Write-Warning "  Response structure incomplete"
        }
    } else {
        Write-Error "CSV Analyzer failed: $($csvResponse.error)"
    }
} catch {
    Write-Error "Exception during CSV Analyzer execution: $_"
    Write-Error $_.Exception.Message
}

Write-Host ""

# Step 5: Test Email Summarizer agent
Write-Info "Step 5: Testing Email Summarizer agent..."
try {
    $emailInput = @{
        agent_id = "email-summarizer"
        input = @{
            emails = @(
                @{
                    from = "john@example.com"
                    subject = "Q4 Project Update"
                    body = "Hi team, here's the latest update on our Q4 project. We're on track but need additional design resources."
                }
            )
        }
    } | ConvertTo-Json -Depth 10

    $emailResponse = Invoke-RestMethod `
        -Uri "$ApiBase/api/v1/marketplace/agents/call" `
        -Method Post `
        -Headers @{
            "X-API-Key" = $apiKey
            "Content-Type" = "application/json"
        } `
        -Body $emailInput

    if ($emailResponse.success) {
        Write-Success "Email Summarizer executed successfully"
        Write-Info "  Execution time: $($emailResponse.execution_time_ms)ms"
        Write-Info "  Request ID: $($emailResponse.request_id)"
        Write-Info "  Result keys: $($emailResponse.result.PSObject.Properties.Name -join ', ')"
        $results.RequestIds += $emailResponse.request_id
        $results.EmailSummarizer = $true
        
        # Validate response structure
        if ($emailResponse.result.summary -and $emailResponse.result.action_items) {
            Write-Success "  Response structure valid (has summary and action_items)"
        } else {
            Write-Warning "  Response structure incomplete"
        }
    } else {
        Write-Error "Email Summarizer failed: $($emailResponse.error)"
    }
} catch {
    Write-Error "Exception during Email Summarizer execution: $_"
    Write-Error $_.Exception.Message
}

Write-Host ""

# Step 6: Test Code Reviewer agent
Write-Info "Step 6: Testing Code Reviewer agent..."
try {
    $codeInput = @{
        agent_id = "code-reviewer"
        input = @{
            language = "python"
            code = @"
def calculate_total(items):
    total = 0
    for item in items:
        total += item['price']
    return total
"@
        }
    } | ConvertTo-Json -Depth 10

    $codeResponse = Invoke-RestMethod `
        -Uri "$ApiBase/api/v1/marketplace/agents/call" `
        -Method Post `
        -Headers @{
            "X-API-Key" = $apiKey
            "Content-Type" = "application/json"
        } `
        -Body $codeInput

    if ($codeResponse.success) {
        Write-Success "Code Reviewer executed successfully"
        Write-Info "  Execution time: $($codeResponse.execution_time_ms)ms"
        Write-Info "  Request ID: $($codeResponse.request_id)"
        Write-Info "  Result keys: $($codeResponse.result.PSObject.Properties.Name -join ', ')"
        $results.RequestIds += $codeResponse.request_id
        $results.CodeReviewer = $true
        
        # Validate response structure
        if ($codeResponse.result.overall_quality -and $codeResponse.result.suggestions) {
            Write-Success "  Response structure valid (has overall_quality and suggestions)"
        } else {
            Write-Warning "  Response structure incomplete"
        }
    } else {
        Write-Error "Code Reviewer failed: $($codeResponse.error)"
    }
} catch {
    Write-Error "Exception during Code Reviewer execution: $_"
    Write-Error $_.Exception.Message
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "E2E VALIDATION SUMMARY" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# Display results
$totalTests = 6
$passedTests = 0

foreach ($test in $results.Keys) {
    if ($test -eq "RequestIds") { continue }
    
    $status = if ($results[$test]) { 
        $passedTests++
        "✅ PASS" 
    } else { 
        "❌ FAIL" 
    }
    
    $testName = $test -replace '([A-Z])', ' $1' -replace '^ ', ''
    Write-Host "$status - $testName"
}

Write-Host ""
Write-Host "Results: $passedTests/$totalTests tests passed" -ForegroundColor $(if ($passedTests -eq $totalTests) { "Green" } else { "Yellow" })
Write-Host ""

# Display request IDs
Write-Info "Request IDs collected (for log correlation):"
foreach ($reqId in $results.RequestIds) {
    Write-Host "  - $reqId" -ForegroundColor Gray
}

Write-Host ""

# Exit code
if ($passedTests -eq $totalTests) {
    Write-Success "All E2E tests passed! 🎉"
    exit 0
} else {
    Write-Warning "Some tests failed. Please review the output above."
    exit 1
}

