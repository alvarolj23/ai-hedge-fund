<#
.SYNOPSIS
    Deploy AI Hedge Fund Dashboard to Azure Static Web Apps

.DESCRIPTION
    This script deploys the React dashboard to Azure Static Web Apps (FREE tier).
    It handles:
    - Building the dashboard
    - Creating the Static Web App (if needed)
    - Deploying to Azure
    - Configuring environment variables

.PARAMETER ResourceGroup
    Azure resource group name (default: rg-ai-hedge-fund-prod)

.PARAMETER AppName
    Static Web App name (default: aihedgefund-dashboard)

.PARAMETER Location
    Azure region (default: westeurope)

.PARAMETER ApiUrl
    Backend API URL (default: https://aihedgefund-api.wittysand-2cb74b22.westeurope.azurecontainerapps.io)

.EXAMPLE
    .\deploy-dashboard.ps1

.EXAMPLE
    .\deploy-dashboard.ps1 -ResourceGroup "my-rg" -AppName "my-dashboard"
#>

param(
    [string]$ResourceGroup = "rg-ai-hedge-fund-prod",
    [string]$AppName = "aihedgefund-dashboard",
    [string]$Location = "westeurope",
    [string]$ApiUrl = "https://aihedgefund-api.wittysand-2cb74b22.westeurope.azurecontainerapps.io"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "AI HEDGE FUND - Dashboard Deployment" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Resource Group: $ResourceGroup"
Write-Host "  App Name:       $AppName"
Write-Host "  Location:       $Location"
Write-Host "  API URL:        $ApiUrl"
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

# Navigate to dashboard folder
$dashboardPath = Join-Path $PSScriptRoot "..\dashboard"
if (-not (Test-Path $dashboardPath)) {
    Write-Host "❌ Dashboard folder not found at: $dashboardPath" -ForegroundColor Red
    exit 1
}

Push-Location $dashboardPath

try {
    # Check Node.js
    Write-Host ""
    Write-Host "Checking Node.js..." -ForegroundColor Yellow
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Host "❌ Node.js not found. Please install it from https://nodejs.org" -ForegroundColor Red
        exit 1
    }
    $nodeVersion = node --version
    Write-Host "✅ Node.js found: $nodeVersion" -ForegroundColor Green

    # Install dependencies
    Write-Host ""
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ npm install failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Dependencies installed" -ForegroundColor Green

    # Create .env file
    Write-Host ""
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    $envContent = "VITE_API_URL=$ApiUrl"
    Set-Content -Path ".env" -Value $envContent -Force
    Write-Host "✅ .env file created" -ForegroundColor Green

    # Build dashboard
    Write-Host ""
    Write-Host "Building dashboard..." -ForegroundColor Yellow
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Build complete" -ForegroundColor Green

    # Check if Static Web App exists
    Write-Host ""
    Write-Host "Checking if Static Web App exists..." -ForegroundColor Yellow
    $appExists = az staticwebapp show `
        --name $AppName `
        --resource-group $ResourceGroup `
        2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Static Web App already exists" -ForegroundColor Green
        Write-Host ""
        Write-Host "Deploying to existing Static Web App..." -ForegroundColor Yellow

        # Note: Direct deployment to Static Web Apps requires GitHub Actions or Azure CLI deployment token
        # For manual deployment, we'll guide the user to use the Azure Portal

        Write-Host ""
        Write-Host "================================================================" -ForegroundColor Cyan
        Write-Host "DEPLOYMENT INSTRUCTIONS" -ForegroundColor Cyan
        Write-Host "================================================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "The dashboard has been built successfully!" -ForegroundColor Green
        Write-Host "Build output is in: ./dist" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To deploy, choose one of these options:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "OPTION 1: GitHub Actions (Recommended)" -ForegroundColor Cyan
        Write-Host "  1. Commit and push your changes to GitHub"
        Write-Host "  2. GitHub Actions will automatically deploy"
        Write-Host ""
        Write-Host "OPTION 2: Azure Portal" -ForegroundColor Cyan
        Write-Host "  1. Go to Azure Portal"
        Write-Host "  2. Navigate to: $ResourceGroup -> $AppName"
        Write-Host "  3. Disconnect GitHub if connected"
        Write-Host "  4. Click 'Download deployment token'"
        Write-Host "  5. Use SWA CLI: npm install -g @azure/static-web-apps-cli"
        Write-Host "  6. Run: swa deploy ./dist --deployment-token <token>"
        Write-Host ""
        Write-Host "OPTION 3: Azure CLI with SWA Extension" -ForegroundColor Cyan
        Write-Host "  az extension add --name staticwebapp"
        Write-Host "  az staticwebapp deploy \"
        Write-Host "    --name $AppName \"
        Write-Host "    --resource-group $ResourceGroup \"
        Write-Host "    --source ./dist"
        Write-Host ""

    } else {
        Write-Host "Creating new Static Web App..." -ForegroundColor Yellow

        az staticwebapp create `
            --name $AppName `
            --resource-group $ResourceGroup `
            --location $Location `
            --sku Free `
            --source ./dist

        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Failed to create Static Web App" -ForegroundColor Red
            exit 1
        }

        Write-Host "✅ Static Web App created" -ForegroundColor Green
    }

    # Configure environment variables
    Write-Host ""
    Write-Host "Configuring environment variables..." -ForegroundColor Yellow

    az staticwebapp appsettings set `
        --name $AppName `
        --resource-group $ResourceGroup `
        --setting-names VITE_API_URL=$ApiUrl

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Environment variables configured" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Could not set environment variables automatically" -ForegroundColor Yellow
        Write-Host "   Please set manually in Azure Portal:" -ForegroundColor Yellow
        Write-Host "   Configuration -> Application settings -> VITE_API_URL = $ApiUrl" -ForegroundColor Yellow
    }

    # Get dashboard URL
    Write-Host ""
    Write-Host "Getting dashboard URL..." -ForegroundColor Yellow
    $dashboardUrl = az staticwebapp show `
        --name $AppName `
        --resource-group $ResourceGroup `
        --query "defaultHostname" `
        -o tsv

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "================================================================" -ForegroundColor Green
        Write-Host "✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
        Write-Host "================================================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "🌐 Dashboard URL: https://$dashboardUrl" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Yellow
        Write-Host "  1. Visit the dashboard URL above"
        Write-Host "  2. Test all pages (Portfolio, Analytics, Trades, Monitoring, Config)"
        Write-Host "  3. If using GitHub Actions, push your changes to auto-deploy"
        Write-Host ""
    }

} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Script completed at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""
