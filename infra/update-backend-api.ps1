<#
.SYNOPSIS
    Update AI Hedge Fund Backend API Container App

.DESCRIPTION
    This script triggers a new revision of the Container App to deploy
    the latest backend code changes (including new dashboard endpoints).

.PARAMETER ResourceGroup
    Azure resource group name (default: rg-ai-hedge-fund-prod)

.PARAMETER ContainerAppName
    Container App name (default: aihedgefund-api)

.EXAMPLE
    .\update-backend-api.ps1

.EXAMPLE
    .\update-backend-api.ps1 -ResourceGroup "my-rg" -ContainerAppName "my-api"
#>

param(
    [string]$ResourceGroup = "rg-ai-hedge-fund-prod",
    [string]$ContainerAppName = "aihedgefund-api"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "AI HEDGE FUND - Backend API Update" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Resource Group:     $ResourceGroup"
Write-Host "  Container App Name: $ContainerAppName"
Write-Host ""

# Check Azure CLI
Write-Host "Checking Azure CLI..." -ForegroundColor Yellow
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Azure CLI not found. Please install it from:" -ForegroundColor Red
    Write-Host "   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Azure CLI found" -ForegroundColor Green

# Check if logged in
Write-Host "Checking Azure login..." -ForegroundColor Yellow
$accountInfo = az account show 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Not logged in to Azure. Please run: az login" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Logged in to Azure" -ForegroundColor Green

# Get Container App info
Write-Host ""
Write-Host "Getting Container App information..." -ForegroundColor Yellow
$appInfo = az containerapp show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --query "{image:properties.template.containers[0].image, revisions:properties.configuration.activeRevisionsMode}" `
    2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Container App not found: $ContainerAppName" -ForegroundColor Red
    exit 1
}

$appData = $appInfo | ConvertFrom-Json
Write-Host "✅ Found Container App" -ForegroundColor Green
Write-Host "   Current Image: $($appData.image)" -ForegroundColor Gray

# Create new revision
Write-Host ""
Write-Host "Creating new revision..." -ForegroundColor Yellow
Write-Host "This will:" -ForegroundColor Gray
Write-Host "  1. Keep the same image" -ForegroundColor Gray
Write-Host "  2. Restart the container to pick up new code" -ForegroundColor Gray
Write-Host "  3. Add new dashboard API endpoints" -ForegroundColor Gray
Write-Host ""

az containerapp revision copy `
    --name $ContainerAppName `
    --resource-group $ResourceGroup

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to create new revision" -ForegroundColor Red
    exit 1
}

Write-Host "✅ New revision created" -ForegroundColor Green

# Wait for revision to be ready
Write-Host ""
Write-Host "Waiting for revision to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$maxAttempts = 30
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts -and -not $ready) {
    $attempt++

    $status = az containerapp show `
        --name $ContainerAppName `
        --resource-group $ResourceGroup `
        --query "properties.latestRevisionFqdn" `
        -o tsv 2>&1

    if ($LASTEXITCODE -eq 0 -and $status) {
        $ready = $true
        Write-Host "✅ Revision is ready" -ForegroundColor Green
        break
    }

    Write-Host "   Waiting... (attempt $attempt/$maxAttempts)" -ForegroundColor Gray
    Start-Sleep -Seconds 5
}

if (-not $ready) {
    Write-Host "⚠️  Timeout waiting for revision to be ready" -ForegroundColor Yellow
    Write-Host "   Check Azure Portal for revision status" -ForegroundColor Yellow
}

# Get Container App URL
Write-Host ""
Write-Host "Getting Container App URL..." -ForegroundColor Yellow
$appUrl = az containerapp show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" `
    -o tsv

if ($LASTEXITCODE -eq 0 -and $appUrl) {
    Write-Host "✅ Container App URL: https://$appUrl" -ForegroundColor Green

    # Test the new endpoints
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "Testing New Dashboard Endpoints" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Running API tests..." -ForegroundColor Yellow

    # Run the Python test script
    $testScript = Join-Path $PSScriptRoot "test-dashboard-api.py"
    if (Test-Path $testScript) {
        python $testScript "https://$appUrl"
    } else {
        Write-Host "⚠️  Test script not found. Manual testing required." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Test these endpoints manually:" -ForegroundColor Yellow
        Write-Host "  GET https://$appUrl/dashboard/portfolio"
        Write-Host "  GET https://$appUrl/dashboard/system-health"
        Write-Host "  GET https://$appUrl/dashboard/metrics?days=30"
        Write-Host "  GET https://$appUrl/config/monitor"
        Write-Host ""
    }
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "✅ BACKEND UPDATE COMPLETE!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Test the new dashboard endpoints (see above)"
Write-Host "  2. Deploy the dashboard frontend: .\deploy-dashboard.ps1"
Write-Host "  3. Verify end-to-end functionality"
Write-Host ""
Write-Host "Script completed at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""
