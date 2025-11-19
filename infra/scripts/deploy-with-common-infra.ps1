# deploy-with-common-infra.ps1
# Master deployment script for AI Hedge Fund using common infrastructure

param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')]
    [string]$SubscriptionId,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ResourceGroupName,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$CommonInfraResourceGroup,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$CommonCosmosAccountName,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$CommonAcrName,

    [ValidateNotNullOrEmpty()]
    [string]$NamePrefix = 'aihedgefund',

    [ValidateNotNullOrEmpty()]
    [string]$Location = 'westeurope',

    [ValidateNotNullOrEmpty()]
    [string]$DatabaseName = 'ai-hedge-fund',

    [switch]$SkipCosmosSetup,

    [switch]$UsePlaceholderImages,

    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

try {
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "   AI Hedge Fund - Azure Deployment with Common Infrastructure" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""

    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $repoRoot = Resolve-Path (Join-Path (Join-Path $scriptRoot '..') '..')

    # Display configuration
    Write-Host "Deployment Configuration:" -ForegroundColor Cyan
    Write-Host "  Subscription:          $SubscriptionId" -ForegroundColor White
    Write-Host "  Resource Group:        $ResourceGroupName (new)" -ForegroundColor White
    Write-Host "  Location:              $Location" -ForegroundColor White
    Write-Host "  Name Prefix:           $NamePrefix" -ForegroundColor White
    Write-Host "" -ForegroundColor White
    Write-Host "Common Infrastructure (Reused):" -ForegroundColor Cyan
    Write-Host "  Resource Group:        $CommonInfraResourceGroup" -ForegroundColor White
    Write-Host "  Cosmos DB Account:     $CommonCosmosAccountName" -ForegroundColor White
    Write-Host "  Database Name:         $DatabaseName" -ForegroundColor White
    Write-Host "  Container Registry:    $CommonAcrName" -ForegroundColor White
    Write-Host ""

    if ($WhatIf) {
        Write-Host "[WHAT-IF MODE] No changes will be made" -ForegroundColor Yellow
        Write-Host ""
    }

    # Authenticate
    Write-Host "Step 1: Authenticating with Azure..." -ForegroundColor Cyan
    az account set --subscription $SubscriptionId --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw "Failed to set subscription" }
    Write-Host "  Authenticated successfully" -ForegroundColor Green
    Write-Host ""

    # Verify common infrastructure exists
    Write-Host "Step 2: Verifying common infrastructure..." -ForegroundColor Cyan

    # Check Cosmos DB
    $cosmos = az cosmosdb show --name $CommonCosmosAccountName --resource-group $CommonInfraResourceGroup -o json 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Cosmos DB account '$CommonCosmosAccountName' not found in '$CommonInfraResourceGroup'"
    }
    Write-Host "  Cosmos DB verified: $CommonCosmosAccountName" -ForegroundColor Green

    # Check ACR
    $acr = az acr show --name $CommonAcrName --resource-group $CommonInfraResourceGroup -o json 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Container Registry '$CommonAcrName' not found in '$CommonInfraResourceGroup'"
    }
    $acrData = $acr | ConvertFrom-Json
    $acrLoginServer = $acrData.loginServer
    Write-Host "  ACR verified: $CommonAcrName ($acrLoginServer)" -ForegroundColor Green
    Write-Host ""

    # Get ACR credentials
    Write-Host "Step 3: Retrieving ACR credentials..." -ForegroundColor Cyan
    $acrCredentials = az acr credential show --name $CommonAcrName --resource-group $CommonInfraResourceGroup -o json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to retrieve ACR credentials. Ensure admin user is enabled on the ACR."
    }
    $acrUsername = $acrCredentials.username
    $acrPassword = $acrCredentials.passwords[0].value
    Write-Host "  ACR credentials retrieved" -ForegroundColor Green
    Write-Host ""

    # Setup Cosmos DB
    if (-not $SkipCosmosSetup) {
        Write-Host "Step 4: Setting up Cosmos DB database and containers..." -ForegroundColor Cyan
        $cosmosSetupScript = Join-Path $scriptRoot 'setup-cosmos-db.ps1'

        if ($WhatIf) {
            & $cosmosSetupScript `
                -SubscriptionId $SubscriptionId `
                -ResourceGroupName $CommonInfraResourceGroup `
                -CosmosAccountName $CommonCosmosAccountName `
                -DatabaseName $DatabaseName `
                -WhatIf
        } else {
            & $cosmosSetupScript `
                -SubscriptionId $SubscriptionId `
                -ResourceGroupName $CommonInfraResourceGroup `
                -CosmosAccountName $CommonCosmosAccountName `
                -DatabaseName $DatabaseName
        }

        if ($LASTEXITCODE -ne 0) { throw "Cosmos DB setup failed" }
        Write-Host ""
    } else {
        Write-Host "Step 4: Skipping Cosmos DB setup (--SkipCosmosSetup specified)" -ForegroundColor Yellow
        Write-Host ""
    }

    # Deploy infrastructure
    Write-Host "Step 5: Deploying Azure infrastructure..." -ForegroundColor Cyan
    Write-Host "  This will create:" -ForegroundColor White
    Write-Host "    - Storage Account + Queues" -ForegroundColor White
    Write-Host "    - Log Analytics + Application Insights" -ForegroundColor White
    Write-Host "    - Container Apps Environment" -ForegroundColor White
    Write-Host "    - API Container App" -ForegroundColor White
    Write-Host "    - Queue Worker Job" -ForegroundColor White
    Write-Host "    - Function App (Market Monitor)" -ForegroundColor White
    Write-Host ""
    Write-Host "  This may take 5-10 minutes..." -ForegroundColor Yellow
    Write-Host ""

    $deployScript = Join-Path $scriptRoot 'deploy-infrastructure.ps1'
    $deployParams = @{
        SubscriptionId = $SubscriptionId
        ResourceGroupName = $ResourceGroupName
        NamePrefix = $NamePrefix
        Location = $Location
        ExistingCosmosResourceGroup = $CommonInfraResourceGroup
        ExistingCosmosAccountName = $CommonCosmosAccountName
        ExistingCosmosDatabaseName = $DatabaseName
        ExistingAcrResourceGroup = $CommonInfraResourceGroup
        ExistingAcrName = $CommonAcrName
        ExistingAcrUsername = $acrUsername
        ExistingAcrPassword = $acrPassword
        EnableCosmosFreeTier = $false
    }

    if ($UsePlaceholderImages) {
        $deployParams.UsePlaceholderImages = $true
    }

    if ($WhatIf) {
        $deployParams.WhatIf = $true
    }

    & $deployScript @deployParams

    if ($LASTEXITCODE -ne 0) { throw "Infrastructure deployment failed" }
    Write-Host ""

    # Display next steps
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "   Deployment Completed Successfully!" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Review deployment outputs:" -ForegroundColor Yellow
    Write-Host "   Location: $scriptRoot\latest-deployment.json" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Build and push Docker images:" -ForegroundColor Yellow
    Write-Host "   Option A: Use GitHub workflow (recommended for Windows without Docker)" -ForegroundColor White
    Write-Host "     - Set up GitHub secrets and variables" -ForegroundColor White
    Write-Host "     - Run: .github/workflows/publish-app.yml" -ForegroundColor White
    Write-Host ""
    Write-Host "   Option B: Build locally (requires Docker)" -ForegroundColor White
    Write-Host "     az acr login --name $CommonAcrName" -ForegroundColor Gray
    Write-Host "     docker build -t ${acrLoginServer}/ai-hedge-fund-api:latest -f docker/Dockerfile ." -ForegroundColor Gray
    Write-Host "     docker build -t ${acrLoginServer}/ai-hedge-fund-worker:latest -f docker/worker.Dockerfile ." -ForegroundColor Gray
    Write-Host "     docker push ${acrLoginServer}/ai-hedge-fund-api:latest" -ForegroundColor Gray
    Write-Host "     docker push ${acrLoginServer}/ai-hedge-fund-worker:latest" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Deploy Function App code:" -ForegroundColor Yellow
    Write-Host "   .\infra\scripts\deploy-function.ps1 -SubscriptionId '$SubscriptionId' -ResourceGroupName '$ResourceGroupName'" -ForegroundColor White
    Write-Host ""
    Write-Host "4. Configure application settings with API keys" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "See infra/DEPLOYMENT-GUIDE.md for detailed instructions" -ForegroundColor Cyan
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host "   Deployment Failed" -ForegroundColor Red
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Stack trace:" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    Write-Host ""
    exit 1
}
finally {
    $ProgressPreference = 'Continue'
}
