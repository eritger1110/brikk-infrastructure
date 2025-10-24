# Run All Agent Tests
# Executes all test scripts in sequence

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Brikk Agent Bridge - Test Suite" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$tests = @(
    "test-health.ps1",
    "test-openai.ps1",
    "test-registry.ps1",
    "test-bridge.ps1"
)

$passed = 0
$failed = 0

foreach ($test in $tests) {
    $testPath = Join-Path $scriptPath $test
    
    Write-Host ""
    Write-Host "Running: $test" -ForegroundColor Yellow
    Write-Host "───────────────────────────────────────────────────────" -ForegroundColor Gray
    
    try {
        & $testPath
        if ($LASTEXITCODE -eq 0 -or $null -eq $LASTEXITCODE) {
            $passed++
            Write-Host "✓ $test PASSED" -ForegroundColor Green
        } else {
            $failed++
            Write-Host "✗ $test FAILED" -ForegroundColor Red
        }
    } catch {
        $failed++
        Write-Host "✗ $test FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Test Results" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Passed: $passed" -ForegroundColor Green
Write-Host "  Failed: $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host "  Total:  $($passed + $failed)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if ($failed -gt 0) {
    exit 1
} else {
    Write-Host "All tests passed! ✓" -ForegroundColor Green
    exit 0
}

