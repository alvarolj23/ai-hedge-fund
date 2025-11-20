#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Send a test message to the Azure Storage Queue for testing the hedge fund worker.

.DESCRIPTION
    This script is a PowerShell wrapper around send_test_message.py that handles
    Python environment activation and passes parameters correctly.

.PARAMETER Ticker
    Single ticker symbol to analyze (e.g., AAPL, MSFT, NVDA)

.PARAMETER Tickers
    Multiple ticker symbols to analyze (e.g., AAPL, MSFT, GOOGL)

.PARAMETER UserId
    User ID for the analysis (default: test-user)

.PARAMETER StrategyId
    Strategy ID for the analysis (default: default)

.EXAMPLE
    .\infra\scripts\send-test-message.ps1
    Sends a default test message for AAPL

.EXAMPLE
    .\infra\scripts\send-test-message.ps1 -Ticker MSFT
    Sends a test message for MSFT

.EXAMPLE
    .\infra\scripts\send-test-message.ps1 -Tickers AAPL,MSFT,GOOGL
    Sends a test message for multiple tickers
#>

param(
    [string]$Ticker = "",
    [string[]]$Tickers = @(),
    [string]$UserId = "test-user",
    [string]$StrategyId = "default"
)

$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptRoot '..' '..')
$pythonScript = Join-Path $scriptRoot 'send_test_message.py'

# Check if Python script exists
if (-not (Test-Path $pythonScript)) {
    Write-Error "Python script not found: $pythonScript"
    exit 1
}

# Build Python command
$pythonArgs = @($pythonScript)

if ($Ticker) {
    $pythonArgs += @("--ticker", $Ticker)
}

if ($Tickers.Count -gt 0) {
    $pythonArgs += "--tickers"
    $pythonArgs += $Tickers
}

$pythonArgs += @("--user-id", $UserId)
$pythonArgs += @("--strategy-id", $StrategyId)

# Try to use venv Python if available, otherwise use system Python
$pythonCmd = "python"
$venvPython = Join-Path $repoRoot "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    Write-Host "Using virtual environment Python: $venvPython" -ForegroundColor Cyan
    $pythonCmd = $venvPython
} else {
    Write-Host "Using system Python" -ForegroundColor Cyan
}

# Run the Python script
Write-Host "Running: $pythonCmd $($pythonArgs -join ' ')" -ForegroundColor Gray
& $pythonCmd @pythonArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to send test message (exit code: $LASTEXITCODE)"
    exit $LASTEXITCODE
}
