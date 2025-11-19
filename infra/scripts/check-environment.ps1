# check-environment.ps1
# Verifies that your environment is correctly configured for deployment

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Environment Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check PowerShell version
Write-Host "PowerShell Version:" -ForegroundColor Cyan
Write-Host "  Version: $($PSVersionTable.PSVersion)" -ForegroundColor White
Write-Host "  Edition: $($PSVersionTable.PSEdition)" -ForegroundColor White

if ($PSVersionTable.PSEdition -eq "Desktop") {
    Write-Host "  Status: OK (PowerShell 5.1 - Windows PowerShell)" -ForegroundColor Green
} elseif ($PSVersionTable.PSEdition -eq "Core") {
    Write-Host "  Status: Using PowerShell Core (pwsh)" -ForegroundColor Yellow
    Write-Host "  Note: PowerShell 5.1 (Windows PowerShell) is recommended for best compatibility" -ForegroundColor Yellow
} else {
    Write-Host "  Status: Unknown edition" -ForegroundColor Yellow
}
Write-Host ""

# Check Azure CLI
Write-Host "Azure CLI:" -ForegroundColor Cyan
try {
    $azVersion = az version --only-show-errors 2>&1 | Out-String
    if ($azVersion -match '"azure-cli":\s*"([^"]+)"') {
        Write-Host "  Version: $($Matches[1])" -ForegroundColor White
        Write-Host "  Status: OK" -ForegroundColor Green
    } else {
        Write-Host "  Status: Installed (version unknown)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  Status: NOT FOUND" -ForegroundColor Red
    Write-Host "  Install from: https://aka.ms/installazurecliwindows" -ForegroundColor Yellow
}
Write-Host ""

# Check for corporate environment variables
Write-Host "Corporate Environment:" -ForegroundColor Cyan
$hasProxySettings = $false

if ($env:AZURE_CLI_DISABLE_CONNECTION_VERIFICATION) {
    Write-Host "  AZURE_CLI_DISABLE_CONNECTION_VERIFICATION: $env:AZURE_CLI_DISABLE_CONNECTION_VERIFICATION" -ForegroundColor Yellow
    Write-Host "    (SSL verification disabled - common in corporate environments)" -ForegroundColor Gray
    $hasProxySettings = $true
}

if ($env:HTTP_PROXY -or $env:HTTPS_PROXY) {
    Write-Host "  Proxy detected:" -ForegroundColor Yellow
    if ($env:HTTP_PROXY) { Write-Host "    HTTP_PROXY: $env:HTTP_PROXY" -ForegroundColor Gray }
    if ($env:HTTPS_PROXY) { Write-Host "    HTTPS_PROXY: $env:HTTPS_PROXY" -ForegroundColor Gray }
    $hasProxySettings = $true
}

if (-not $hasProxySettings) {
    Write-Host "  No special settings detected" -ForegroundColor White
}
Write-Host ""

# Check Azure login status
Write-Host "Azure Authentication:" -ForegroundColor Cyan
try {
    $account = az account show --only-show-errors 2>&1 | ConvertFrom-Json
    if ($account) {
        Write-Host "  Status: Logged in" -ForegroundColor Green
        Write-Host "  Account: $($account.user.name)" -ForegroundColor White
        Write-Host "  Subscription: $($account.name)" -ForegroundColor White
        Write-Host "  Subscription ID: $($account.id)" -ForegroundColor Gray
    } else {
        Write-Host "  Status: Not logged in" -ForegroundColor Yellow
        Write-Host "  Run: az login" -ForegroundColor White
    }
}
catch {
    Write-Host "  Status: Not logged in" -ForegroundColor Yellow
    Write-Host "  Run: az login" -ForegroundColor White
}
Write-Host ""

# Check current directory
Write-Host "Current Directory:" -ForegroundColor Cyan
$currentPath = Get-Location
Write-Host "  $currentPath" -ForegroundColor White

if (Test-Path "infra\scripts\deploy-with-common-infra.ps1") {
    Write-Host "  Status: OK (in project root)" -ForegroundColor Green
} else {
    Write-Host "  Status: WARNING - Not in project root" -ForegroundColor Yellow
    Write-Host "  Navigate to project root before running deployment scripts" -ForegroundColor Yellow
}
Write-Host ""

# Recommendations
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Recommendations:" -ForegroundColor Cyan
Write-Host ""

if ($PSVersionTable.PSEdition -eq "Core") {
    Write-Host "1. Use Windows PowerShell (PowerShell 5.1) instead of PowerShell Core:" -ForegroundColor Yellow
    Write-Host "   - Close this window" -ForegroundColor White
    Write-Host "   - Open: Start Menu → Windows PowerShell" -ForegroundColor White
    Write-Host "   - DO NOT open 'PowerShell 7' or 'pwsh'" -ForegroundColor White
    Write-Host ""
}

Write-Host "Ready to deploy!" -ForegroundColor Green
Write-Host "Run: .\infra\scripts\deploy-with-common-infra.ps1 with your parameters" -ForegroundColor White
Write-Host ""
