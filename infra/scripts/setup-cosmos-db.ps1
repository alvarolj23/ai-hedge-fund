# setup-cosmos-db.ps1
# Creates database and containers in existing Cosmos DB account

param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')]
    [string]$SubscriptionId,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ResourceGroupName,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$CosmosAccountName,

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string]$DatabaseName = 'ai-hedge-fund',

    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

try {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "AI Hedge Fund - Cosmos DB Setup" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    # Define container names
    $containers = @(
        @{ Name = 'portfolios'; Description = 'Portfolio positions and cash' },
        @{ Name = 'analyst-signals'; Description = 'AI analyst signals and recommendations' },
        @{ Name = 'decisions'; Description = 'Trading decisions and rationale' },
        @{ Name = 'portfolioSnapshots'; Description = 'Historical portfolio snapshots' },
        @{ Name = 'hedgeFundResults'; Description = 'Execution results and performance' },
        @{ Name = 'hedgeFundStatus'; Description = 'Run status and metadata' },
        @{ Name = 'broker-orders'; Description = 'Broker order history' },
        @{ Name = 'monitor-cooldowns'; Description = 'Market monitoring cooldown state' }
    )

    # Authenticate and set subscription
    Write-Host "Setting Azure subscription..." -ForegroundColor Cyan
    az account set --subscription $SubscriptionId --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw "Failed to set subscription" }

    # Verify Cosmos account exists
    Write-Host "Verifying Cosmos DB account exists..." -ForegroundColor Cyan
    $cosmosAccount = az cosmosdb show --name $CosmosAccountName --resource-group $ResourceGroupName 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Cosmos DB account '$CosmosAccountName' not found in resource group '$ResourceGroupName'"
    }

    Write-Host "Found Cosmos DB account: $CosmosAccountName" -ForegroundColor Green
    Write-Host ""

    # Check if database exists
    Write-Host "Checking if database '$DatabaseName' exists..." -ForegroundColor Cyan
    $dbExists = $false
    $databases = az cosmosdb sql database list --account-name $CosmosAccountName --resource-group $ResourceGroupName -o json | ConvertFrom-Json
    foreach ($db in $databases) {
        if ($db.name -eq $DatabaseName) {
            $dbExists = $true
            break
        }
    }

    if ($dbExists) {
        Write-Host "Database '$DatabaseName' already exists" -ForegroundColor Yellow
    } else {
        if ($WhatIf) {
            Write-Host "[WHAT-IF] Would create database: $DatabaseName" -ForegroundColor Yellow
        } else {
            Write-Host "Creating database '$DatabaseName'..." -ForegroundColor Cyan
            az cosmosdb sql database create `
                --account-name $CosmosAccountName `
                --resource-group $ResourceGroupName `
                --name $DatabaseName `
                --only-show-errors | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "Failed to create database" }
            Write-Host "Database created successfully" -ForegroundColor Green
        }
    }

    Write-Host ""
    Write-Host "Creating containers (8 total)..." -ForegroundColor Cyan
    Write-Host "This may take 2-3 minutes..." -ForegroundColor Yellow
    Write-Host ""

    # Create containers
    $created = 0
    $skipped = 0
    $failed = 0

    foreach ($container in $containers) {
        $containerName = $container.Name
        $description = $container.Description

        Write-Host "  [$($created + $skipped + $failed + 1)/8] $containerName - $description" -ForegroundColor White

        # Check if container exists
        $containerExists = $false
        $existingContainers = az cosmosdb sql container list `
            --account-name $CosmosAccountName `
            --resource-group $ResourceGroupName `
            --database-name $DatabaseName `
            -o json 2>$null | ConvertFrom-Json

        if ($LASTEXITCODE -eq 0) {
            foreach ($c in $existingContainers) {
                if ($c.name -eq $containerName) {
                    $containerExists = $true
                    break
                }
            }
        }

        if ($containerExists) {
            Write-Host "    Already exists (skipped)" -ForegroundColor Yellow
            $skipped++
            continue
        }

        if ($WhatIf) {
            Write-Host "    [WHAT-IF] Would create container" -ForegroundColor Yellow
            $created++
            continue
        }

        # Create container with /partition_key
        try {
            az cosmosdb sql container create `
                --account-name $CosmosAccountName `
                --resource-group $ResourceGroupName `
                --database-name $DatabaseName `
                --name $containerName `
                --partition-key-path '/partition_key' `
                --only-show-errors | Out-Null

            if ($LASTEXITCODE -eq 0) {
                Write-Host "    Created successfully" -ForegroundColor Green
                $created++
            } else {
                Write-Host "    Failed to create" -ForegroundColor Red
                $failed++
            }
        }
        catch {
            Write-Host "    Error: $_" -ForegroundColor Red
            $failed++
        }
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Summary:" -ForegroundColor Cyan
    Write-Host "  Created: $created" -ForegroundColor Green
    Write-Host "  Skipped: $skipped" -ForegroundColor Yellow
    Write-Host "  Failed:  $failed" -ForegroundColor $(if ($failed -gt 0) { 'Red' } else { 'White' })
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    if ($failed -gt 0) {
        Write-Host "Some containers failed to create. Please check the errors above." -ForegroundColor Red
        exit 1
    }

    if (-not $WhatIf) {
        Write-Host "Cosmos DB setup completed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Database Details:" -ForegroundColor Cyan
        Write-Host "  Account: $CosmosAccountName" -ForegroundColor White
        Write-Host "  Database: $DatabaseName" -ForegroundColor White
        Write-Host "  Containers: 8" -ForegroundColor White
        Write-Host "  Partition Key: /partition_key" -ForegroundColor White
        Write-Host ""
        Write-Host "Next step: Deploy infrastructure with these parameters:" -ForegroundColor Cyan
        Write-Host "  -ExistingCosmosResourceGroup '$ResourceGroupName'" -ForegroundColor White
        Write-Host "  -ExistingCosmosAccountName '$CosmosAccountName'" -ForegroundColor White
        Write-Host "  -ExistingCosmosDatabaseName '$DatabaseName'" -ForegroundColor White
    }
}
catch {
    Write-Host ""
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host "Stack trace:" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    exit 1
}
finally {
    $ProgressPreference = 'Continue'
}
