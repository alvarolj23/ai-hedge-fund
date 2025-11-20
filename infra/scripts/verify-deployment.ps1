# verify-deployment.ps1
# Verifies that all infrastructure components are deployed correctly

param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')]
    [string]$SubscriptionId,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ResourceGroupName,

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string]$CommonInfraResourceGroup,

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string]$CommonCosmosAccountName,

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string]$CommonAcrName
)

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

# Suppress Python warnings for Azure CLI SSL/certificate issues
$env:PYTHONWARNINGS = "ignore"

function Test-Resource {
    param(
        [string]$Name,
        [string]$Command
    )

    Write-Host "  Checking $Name..." -NoNewline
    try {
        # Execute command and capture output, filtering warnings
        $rawOutput = Invoke-Expression "$Command 2>&1"
        $exitCode = $LASTEXITCODE
        
        # Filter out SSL/certificate warnings
        $result = $rawOutput | Where-Object { 
            $_ -notmatch 'InsecureRequestWarning' -and 
            $_ -notmatch 'Connection verification disabled' -and 
            $_ -notmatch 'urllib3/connectionpool' -and
            $_ -notmatch 'WARNING:' -and
            $_ -notmatch 'https://urllib3.readthedocs.io' -and
            $_ -notmatch 'AZURE_CLI_DISABLE_CONNECTION_VERIFICATION'
        }
        
        if ($exitCode -eq 0 -and $result) {
            Write-Host " OK" -ForegroundColor Green
            return $true
        } else {
            Write-Host " NOT FOUND" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host " ERROR: $_" -ForegroundColor Red
        return $false
    }
}

try {
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "   AI Hedge Fund - Deployment Verification" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""

    # Set subscription
    az account set --subscription $SubscriptionId --only-show-errors 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to set subscription" -ForegroundColor Red
        exit 1
    }

    $allPassed = $true
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $outputPath = Join-Path $scriptRoot 'latest-deployment.json'

    # Check if deployment outputs exist
    if (-not (Test-Path $outputPath)) {
        Write-Host "Deployment outputs not found at: $outputPath" -ForegroundColor Red
        Write-Host "Please run deploy-with-common-infra.ps1 first" -ForegroundColor Yellow
        exit 1
    }

    # Load deployment outputs
    $outputs = Get-Content $outputPath -Raw | ConvertFrom-Json

    Write-Host "Resource Group: $ResourceGroupName" -ForegroundColor Cyan
    Write-Host ""

    # Check Storage Account
    Write-Host "Storage Resources:" -ForegroundColor Cyan
    $storageOk = Test-Resource -Name "Storage Account" -Command "az storage account show --name $($outputs.storageAccountName.value) --resource-group $ResourceGroupName -o json --only-show-errors"
    $allPassed = $allPassed -and $storageOk

    # Check Queues
    if ($storageOk) {
        $queueOk = Test-Resource -Name "Analysis Queue" -Command "az storage queue exists --name $($outputs.storageQueueName.value) --account-name $($outputs.storageAccountName.value) -o json"
        $allPassed = $allPassed -and $queueOk

        $dlqOk = Test-Resource -Name "Dead Letter Queue" -Command "az storage queue exists --name $($outputs.storageDeadLetterQueueName.value) --account-name $($outputs.storageAccountName.value) -o json"
        $allPassed = $allPassed -and $dlqOk
    }

    Write-Host ""

    # Check Monitoring Resources
    Write-Host "Monitoring Resources:" -ForegroundColor Cyan
    $lawName = $outputs.logAnalyticsWorkspaceId.value.Split('/')[-1]
    $lawOk = Test-Resource -Name "Log Analytics Workspace" -Command "az monitor log-analytics workspace show --workspace-name $lawName --resource-group $ResourceGroupName -o json --only-show-errors"
    $allPassed = $allPassed -and $lawOk

    $appInsightsOk = Test-Resource -Name "Application Insights" -Command "az monitor app-insights component show --app $($outputs.appInsightsName.value) --resource-group $ResourceGroupName -o json --only-show-errors"
    $allPassed = $allPassed -and $appInsightsOk

    Write-Host ""

    # Check Container Apps
    Write-Host "Container Apps Resources:" -ForegroundColor Cyan
    $caeOk = Test-Resource -Name "Container Apps Environment" -Command "az containerapp env show --name $($outputs.managedEnvironmentName.value) --resource-group $ResourceGroupName -o json --only-show-errors"
    $allPassed = $allPassed -and $caeOk

    $apiOk = Test-Resource -Name "API Container App" -Command "az containerapp show --name $($outputs.apiContainerAppName.value) --resource-group $ResourceGroupName -o json --only-show-errors"
    $allPassed = $allPassed -and $apiOk

    $jobOk = Test-Resource -Name "Queue Worker Job" -Command "az containerapp job show --name $($outputs.queueWorkerJobName.value) --resource-group $ResourceGroupName -o json --only-show-errors"
    $allPassed = $allPassed -and $jobOk

    Write-Host ""

    # Check Function App
    Write-Host "Function App Resources:" -ForegroundColor Cyan
    $funcPlanOk = Test-Resource -Name "Function App Plan" -Command "az functionapp plan show --name $($outputs.functionPlanName.value) --resource-group $ResourceGroupName -o json --only-show-errors"
    $allPassed = $allPassed -and $funcPlanOk

    $funcOk = Test-Resource -Name "Function App" -Command "az functionapp show --name $($outputs.functionAppName.value) --resource-group $ResourceGroupName -o json --only-show-errors"
    $allPassed = $allPassed -and $funcOk

    Write-Host ""

    # Check Common Infrastructure (if specified)
    if ($CommonInfraResourceGroup -and $CommonCosmosAccountName -and $CommonAcrName) {
        Write-Host "Common Infrastructure (Shared):" -ForegroundColor Cyan
        Write-Host "Resource Group: $CommonInfraResourceGroup" -ForegroundColor Gray

        $cosmosOk = Test-Resource -Name "Cosmos DB Account" -Command "az cosmosdb show --name $CommonCosmosAccountName --resource-group $CommonInfraResourceGroup -o json --only-show-errors"
        $allPassed = $allPassed -and $cosmosOk

        if ($cosmosOk) {
            $dbName = $outputs.cosmosDatabaseName.value
            $dbOk = Test-Resource -Name "Database ($dbName)" -Command "az cosmosdb sql database show --account-name $CommonCosmosAccountName --resource-group $CommonInfraResourceGroup --name $dbName -o json --only-show-errors"
            $allPassed = $allPassed -and $dbOk

            # Check containers
            if ($dbOk) {
                Write-Host "  Checking containers..." -ForegroundColor White
                $containers = $outputs.cosmosContainers.value.PSObject.Properties | ForEach-Object { $_.Value }
                $containerOk = $true
                foreach ($container in $containers) {
                    $exists = Test-Resource -Name "    $container" -Command "az cosmosdb sql container show --account-name $CommonCosmosAccountName --resource-group $CommonInfraResourceGroup --database-name $dbName --name $container -o json --only-show-errors"
                    $containerOk = $containerOk -and $exists
                }
                $allPassed = $allPassed -and $containerOk
            }
        }

        $acrOk = Test-Resource -Name "Container Registry" -Command "az acr show --name $CommonAcrName --resource-group $CommonInfraResourceGroup -o json --only-show-errors"
        $allPassed = $allPassed -and $acrOk

        Write-Host ""
    }

    # Check Docker Images (if ACR is accessible)
    if ($CommonAcrName) {
        Write-Host "Docker Images:" -ForegroundColor Cyan
        $acrLoginServer = $outputs.containerRegistryLoginServer.value

        $apiImageOk = Test-Resource -Name "API Image" -Command "az acr repository show --name $CommonAcrName --image ai-hedge-fund-api:latest -o json --only-show-errors"
        if ($apiImageOk) {
            Write-Host "    Image: ${acrLoginServer}/ai-hedge-fund-api:latest" -ForegroundColor Gray
        } else {
            Write-Host "    Note: API image not found. Build and push required." -ForegroundColor Yellow
        }

        $workerImageOk = Test-Resource -Name "Worker Image" -Command "az acr repository show --name $CommonAcrName --image ai-hedge-fund-worker:latest -o json --only-show-errors"
        if ($workerImageOk) {
            Write-Host "    Image: ${acrLoginServer}/ai-hedge-fund-worker:latest" -ForegroundColor Gray
        } else {
            Write-Host "    Note: Worker image not found. Build and push required." -ForegroundColor Yellow
        }

        Write-Host ""
    }

    # Summary
    Write-Host "================================================================" -ForegroundColor Cyan
    if ($allPassed) {
        Write-Host "   All Infrastructure Checks Passed!" -ForegroundColor Green
        Write-Host "================================================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Next Steps:" -ForegroundColor Cyan
        Write-Host "1. Build and push Docker images (if not done yet)" -ForegroundColor White
        Write-Host "2. Deploy Function App code" -ForegroundColor White
        Write-Host "3. Configure API keys in deployment-settings.json" -ForegroundColor White
        Write-Host "4. Test the deployment end-to-end" -ForegroundColor White
    } else {
        Write-Host "   Some Checks Failed" -ForegroundColor Red
        Write-Host "================================================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Please review the errors above and fix any missing resources." -ForegroundColor Yellow
    }
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "Verification failed: $_" -ForegroundColor Red
    exit 1
}
finally {
    $ProgressPreference = 'Continue'
}
