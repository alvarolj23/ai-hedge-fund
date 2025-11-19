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

function Test-Resource {
    param(
        [string]$Name,
        [string]$Type,
        [string]$ResourceGroup,
        [scriptblock]$TestCommand
    )

    Write-Host "  Checking $Name..." -NoNewline
    try {
        $result = & $TestCommand
        if ($LASTEXITCODE -eq 0 -and $result) {
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
    az account set --subscription $SubscriptionId --only-show-errors
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
    $storageOk = Test-Resource -Name "Storage Account" -Type "Storage" -ResourceGroup $ResourceGroupName -TestCommand {
        az storage account show --name $outputs.storageAccountName.value --resource-group $ResourceGroupName -o json 2>$null
    }
    $allPassed = $allPassed -and $storageOk

    # Check Queues
    if ($storageOk) {
        $queueOk = Test-Resource -Name "Analysis Queue" -Type "Queue" -ResourceGroup $ResourceGroupName -TestCommand {
            az storage queue exists --name $outputs.storageQueueName.value --account-name $outputs.storageAccountName.value -o json 2>$null
        }
        $allPassed = $allPassed -and $queueOk

        $dlqOk = Test-Resource -Name "Dead Letter Queue" -Type "Queue" -ResourceGroup $ResourceGroupName -TestCommand {
            az storage queue exists --name $outputs.storageDeadLetterQueueName.value --account-name $outputs.storageAccountName.value -o json 2>$null
        }
        $allPassed = $allPassed -and $dlqOk
    }

    Write-Host ""

    # Check Monitoring Resources
    Write-Host "Monitoring Resources:" -ForegroundColor Cyan
    $lawOk = Test-Resource -Name "Log Analytics Workspace" -Type "Workspace" -ResourceGroup $ResourceGroupName -TestCommand {
        az monitor log-analytics workspace show --workspace-name $outputs.logAnalyticsWorkspaceId.value.Split('/')[-1] --resource-group $ResourceGroupName -o json 2>$null
    }
    $allPassed = $allPassed -and $lawOk

    $appInsightsOk = Test-Resource -Name "Application Insights" -Type "Component" -ResourceGroup $ResourceGroupName -TestCommand {
        az monitor app-insights component show --app $outputs.appInsightsName.value --resource-group $ResourceGroupName -o json 2>$null
    }
    $allPassed = $allPassed -and $appInsightsOk

    Write-Host ""

    # Check Container Apps
    Write-Host "Container Apps Resources:" -ForegroundColor Cyan
    $caeOk = Test-Resource -Name "Container Apps Environment" -Type "Environment" -ResourceGroup $ResourceGroupName -TestCommand {
        az containerapp env show --name $outputs.managedEnvironmentName.value --resource-group $ResourceGroupName -o json 2>$null
    }
    $allPassed = $allPassed -and $caeOk

    $apiOk = Test-Resource -Name "API Container App" -Type "ContainerApp" -ResourceGroup $ResourceGroupName -TestCommand {
        az containerapp show --name $outputs.apiContainerAppName.value --resource-group $ResourceGroupName -o json 2>$null
    }
    $allPassed = $allPassed -and $apiOk

    $jobOk = Test-Resource -Name "Queue Worker Job" -Type "Job" -ResourceGroup $ResourceGroupName -TestCommand {
        az containerapp job show --name $outputs.queueWorkerJobName.value --resource-group $ResourceGroupName -o json 2>$null
    }
    $allPassed = $allPassed -and $jobOk

    Write-Host ""

    # Check Function App
    Write-Host "Function App Resources:" -ForegroundColor Cyan
    $funcPlanOk = Test-Resource -Name "Function App Plan" -Type "Plan" -ResourceGroup $ResourceGroupName -TestCommand {
        az functionapp plan show --name $outputs.functionPlanName.value --resource-group $ResourceGroupName -o json 2>$null
    }
    $allPassed = $allPassed -and $funcPlanOk

    $funcOk = Test-Resource -Name "Function App" -Type "Function" -ResourceGroup $ResourceGroupName -TestCommand {
        az functionapp show --name $outputs.functionAppName.value --resource-group $ResourceGroupName -o json 2>$null
    }
    $allPassed = $allPassed -and $funcOk

    Write-Host ""

    # Check Common Infrastructure (if specified)
    if ($CommonInfraResourceGroup -and $CommonCosmosAccountName -and $CommonAcrName) {
        Write-Host "Common Infrastructure (Shared):" -ForegroundColor Cyan
        Write-Host "Resource Group: $CommonInfraResourceGroup" -ForegroundColor Gray

        $cosmosOk = Test-Resource -Name "Cosmos DB Account" -Type "CosmosDB" -ResourceGroup $CommonInfraResourceGroup -TestCommand {
            az cosmosdb show --name $CommonCosmosAccountName --resource-group $CommonInfraResourceGroup -o json 2>$null
        }
        $allPassed = $allPassed -and $cosmosOk

        if ($cosmosOk) {
            $dbName = $outputs.cosmosDatabaseName.value
            $dbOk = Test-Resource -Name "Database ($dbName)" -Type "Database" -ResourceGroup $CommonInfraResourceGroup -TestCommand {
                az cosmosdb sql database show --account-name $CommonCosmosAccountName --resource-group $CommonInfraResourceGroup --name $dbName -o json 2>$null
            }
            $allPassed = $allPassed -and $dbOk

            # Check containers
            if ($dbOk) {
                Write-Host "  Checking containers..." -ForegroundColor White
                $containers = $outputs.cosmosContainers.value.PSObject.Properties | ForEach-Object { $_.Value }
                $containerOk = $true
                foreach ($container in $containers) {
                    $exists = Test-Resource -Name "    $container" -Type "Container" -ResourceGroup $CommonInfraResourceGroup -TestCommand {
                        az cosmosdb sql container show --account-name $CommonCosmosAccountName --resource-group $CommonInfraResourceGroup --database-name $dbName --name $container -o json 2>$null
                    }
                    $containerOk = $containerOk -and $exists
                }
                $allPassed = $allPassed -and $containerOk
            }
        }

        $acrOk = Test-Resource -Name "Container Registry" -Type "ACR" -ResourceGroup $CommonInfraResourceGroup -TestCommand {
            az acr show --name $CommonAcrName --resource-group $CommonInfraResourceGroup -o json 2>$null
        }
        $allPassed = $allPassed -and $acrOk

        Write-Host ""
    }

    # Check Docker Images (if ACR is accessible)
    if ($CommonAcrName) {
        Write-Host "Docker Images:" -ForegroundColor Cyan
        $acrLoginServer = $outputs.containerRegistryLoginServer.value

        $apiImageOk = Test-Resource -Name "API Image" -Type "Image" -ResourceGroup $CommonInfraResourceGroup -TestCommand {
            az acr repository show --name $CommonAcrName --image ai-hedge-fund-api:latest -o json 2>$null
        }
        if ($apiImageOk) {
            Write-Host "    Image: ${acrLoginServer}/ai-hedge-fund-api:latest" -ForegroundColor Gray
        } else {
            Write-Host "    Note: API image not found. Build and push required." -ForegroundColor Yellow
        }

        $workerImageOk = Test-Resource -Name "Worker Image" -Type "Image" -ResourceGroup $CommonInfraResourceGroup -TestCommand {
            az acr repository show --name $CommonAcrName --image ai-hedge-fund-worker:latest -o json 2>$null
        }
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
