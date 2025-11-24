<#
.SYNOPSIS
    Complete automated deployment script for AI Hedge Fund Dashboard

.DESCRIPTION
    This script:
    1. Creates missing Cosmos DB containers
    2. Deploys Static Web App using Bicep
    3. Configures environment variables
    4. Builds and deploys the dashboard
    5. Sets up GitHub secrets for CI/CD

.PARAMETER ResourceGroup
    Azure resource group name (default: rg-ai-hedge-fund-prod)

.PARAMETER AppName
    Static Web App name (default: aihedgefund-dashboard)

.PARAMETER ApiUrl
    Backend API URL

.PARAMETER GitHubRepo
    GitHub repository (format: owner/repo)

.PARAMETER GitHubBranch
    GitHub branch for deployment (default: main)

.EXAMPLE
    .\deploy-dashboard-complete.ps1 -GitHubRepo "alvarolj23/ai-hedge-fund"
#>

param(
    [string]$ResourceGroup = "rg-ai-hedge-fund-prod",
    [string]$AppName = "aihedgefund-dashboard",
    [string]$ApiUrl = "https://aihedgefund-api.wittysand-2cb74b22.westeurope.azurecontainerapps.io",
    [string]$GitHubRepo = "",
    [string]$GitHubBranch = "main",
    [string]$CosmosAccountName = "cosmos-cryptoanalysis-prod-cqpvo3njb4joq",
    [string]$CosmosResourceGroup = "rg-common-infra",
    [string]$CosmosDatabase = "ai-hedge-fund"
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "AI HEDGE FUND - Complete Dashboard Deployment" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create missing Cosmos DB containers
Write-Host "STEP 1: Creating missing Cosmos DB containers..." -ForegroundColor Yellow
Write-Host ""

$containersToCreate = @(
    @{Name="analyst-signals"; PartitionKey="/agent_name"},
    @{Name="decisions"; PartitionKey="/id"},
    @{Name="portfolioSnapshots"; PartitionKey="/id"},
    @{Name="hedgeFundResults"; PartitionKey="/messageId"},
    @{Name="hedgeFundStatus"; PartitionKey="/messageId"}
)

# Get Cosmos account name from resource group if not provided
if (-not $CosmosAccountName -or $CosmosAccountName -eq "aihedgefundcosmos") {
    Write-Host "Finding Cosmos DB account..." -ForegroundColor Gray
    $cosmosAccounts = az cosmosdb list --resource-group $CosmosResourceGroup --query "[].name" -o tsv 2>$null
    if ($cosmosAccounts) {
        $CosmosAccountName = $cosmosAccounts.Split("`n")[0]
        Write-Host "  Found: $CosmosAccountName" -ForegroundColor Gray
    }
}

foreach ($container in $containersToCreate) {
    Write-Host "Checking container: $($container.Name)..." -ForegroundColor Gray

    $exists = az cosmosdb sql container exists `
        --account-name $CosmosAccountName `
        --database-name $CosmosDatabase `
        --name $container.Name `
        --resource-group $CosmosResourceGroup `
        2>$null

    if ($exists -eq "false" -or $LASTEXITCODE -ne 0) {
        Write-Host "  Creating container: $($container.Name)..." -ForegroundColor Yellow

        az cosmosdb sql container create `
            --account-name $CosmosAccountName `
            --database-name $CosmosDatabase `
            --name $container.Name `
            --partition-key-path $container.PartitionKey `
            --resource-group $CosmosResourceGroup `
            --output none

        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Created: $($container.Name)" -ForegroundColor Green
        } else {
            Write-Host "  Failed to create: $($container.Name)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Already exists: $($container.Name)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Cosmos DB setup complete" -ForegroundColor Green
Write-Host ""

# Step 2: Deploy Static Web App
Write-Host "STEP 2: Deploying Static Web App..." -ForegroundColor Yellow
Write-Host ""

$bicepFile = Join-Path $PSScriptRoot "bicep\dashboard.bicep"

if (-not (Test-Path $bicepFile)) {
    Write-Host "ERROR: Bicep file not found: $bicepFile" -ForegroundColor Red
    exit 1
}

Write-Host "Deploying Bicep template..." -ForegroundColor Gray

$deploymentParams = @{
    staticWebAppName = $AppName
    location = "westeurope"
    sku = "Free"
}

if ($GitHubRepo) {
    $deploymentParams.repositoryUrl = "https://github.com/$GitHubRepo"
    $deploymentParams.branch = $GitHubBranch
}

$deployment = az deployment group create `
    --resource-group $ResourceGroup `
    --template-file $bicepFile `
    --parameters $deploymentParams `
    --query "properties.outputs" `
    -o json 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "Static Web App deployed" -ForegroundColor Green

    $outputs = $deployment | ConvertFrom-Json
    $staticWebAppName = $outputs.staticWebAppName.value
    $staticWebAppUrl = $outputs.staticWebAppDefaultHostname.value

    Write-Host "  Name: $staticWebAppName" -ForegroundColor Gray
    Write-Host "  URL: https://$staticWebAppUrl" -ForegroundColor Gray
} else {
    # Check if it already exists
    Write-Host "Checking if Static Web App already exists..." -ForegroundColor Gray

    $existingApp = az staticwebapp show `
        --name $AppName `
        --resource-group $ResourceGroup `
        2>$null

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Static Web App already exists" -ForegroundColor Green
        $appData = $existingApp | ConvertFrom-Json
        $staticWebAppUrl = $appData.defaultHostname
    } else {
        Write-Host "ERROR: Failed to deploy Static Web App" -ForegroundColor Red
        Write-Host "Please create it manually in Azure Portal" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""

# Step 3: Configure environment variables
Write-Host "STEP 3: Configuring environment variables..." -ForegroundColor Yellow
Write-Host ""

$envSettings = @{
    "VITE_API_URL" = $ApiUrl
}

Write-Host "Setting VITE_API_URL = $ApiUrl" -ForegroundColor Gray

az staticwebapp appsettings set `
    --name $AppName `
    --resource-group $ResourceGroup `
    --setting-names VITE_API_URL=$ApiUrl `
    --output none 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "Environment variables configured" -ForegroundColor Green
} else {
    Write-Host "WARNING: Could not set environment variables via CLI" -ForegroundColor Yellow
    Write-Host "  Please set manually in Azure Portal" -ForegroundColor Yellow
}

Write-Host ""

# Step 4: Get deployment token
Write-Host "STEP 4: Getting deployment token..." -ForegroundColor Yellow
Write-Host ""

$deploymentToken = az staticwebapp secrets list `
    --name $AppName `
    --resource-group $ResourceGroup `
    --query "properties.apiKey" `
    -o tsv 2>$null

if ($LASTEXITCODE -eq 0 -and $deploymentToken) {
    Write-Host "Deployment token retrieved" -ForegroundColor Green
    Write-Host ""

    # Step 5: Build and deploy dashboard
    Write-Host "STEP 5: Building and deploying dashboard..." -ForegroundColor Yellow
    Write-Host ""

    $dashboardPath = Join-Path $PSScriptRoot "..\dashboard"
    Push-Location $dashboardPath

    try {
        # Create .env file
        Write-Host "Creating .env file..." -ForegroundColor Gray
        "VITE_API_URL=$ApiUrl" | Out-File -FilePath ".env" -Encoding UTF8 -Force
        Write-Host ".env file created" -ForegroundColor Green

        # Install dependencies
        Write-Host "Installing dependencies..." -ForegroundColor Gray
        npm install --silent
        Write-Host "Dependencies installed" -ForegroundColor Green

        # Build
        Write-Host "Building dashboard..." -ForegroundColor Gray
        npm run build
        Write-Host "Build complete" -ForegroundColor Green

        # Check if SWA CLI is installed
        $swaCliInstalled = Get-Command swa -ErrorAction SilentlyContinue

        if (-not $swaCliInstalled) {
            Write-Host "Installing Azure Static Web Apps CLI..." -ForegroundColor Gray
            npm install -g @azure/static-web-apps-cli
            Write-Host "SWA CLI installed" -ForegroundColor Green
        }

        # Deploy
        Write-Host "Deploying to Azure Static Web Apps..." -ForegroundColor Gray
        swa deploy ./dist `
            --deployment-token $deploymentToken `
            --env production

        if ($LASTEXITCODE -eq 0) {
            Write-Host "Dashboard deployed successfully!" -ForegroundColor Green
        } else {
            Write-Host "WARNING: Deployment completed with warnings" -ForegroundColor Yellow
        }

    } finally {
        Pop-Location
    }
} else {
    Write-Host "WARNING: Could not retrieve deployment token" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Alternative: Set up GitHub Actions deployment" -ForegroundColor Cyan
    Write-Host "1. Get deployment token from Azure Portal:" -ForegroundColor White
    Write-Host "   Static Web App → Settings → Deployment tokens" -ForegroundColor Gray
    Write-Host "2. Add to GitHub Secrets:" -ForegroundColor White
    Write-Host "   Name: AZURE_STATIC_WEB_APPS_API_TOKEN" -ForegroundColor Gray
    Write-Host "   Value: <paste token>" -ForegroundColor Gray
    Write-Host "3. Add another secret:" -ForegroundColor White
    Write-Host "   Name: VITE_API_URL" -ForegroundColor Gray
    Write-Host "   Value: $ApiUrl" -ForegroundColor Gray
    Write-Host "4. Push to GitHub to trigger deployment" -ForegroundColor White
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Dashboard URL: https://$staticWebAppUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Visit the dashboard URL above" -ForegroundColor White
Write-Host "  2. Test all pages (Portfolio, Analytics, Trades, Monitoring, Config)" -ForegroundColor White
Write-Host "  3. If using GitHub Actions, set up secrets (see above)" -ForegroundColor White
Write-Host "  4. Run an analysis to populate data:" -ForegroundColor White
Write-Host "     .\test-queue.ps1 -Tickers 'NVDA' -LookbackDays 30" -ForegroundColor Gray
Write-Host ""
Write-Host "Documentation: infra/DASHBOARD_DEPLOYMENT.md" -ForegroundColor Gray
Write-Host ""
