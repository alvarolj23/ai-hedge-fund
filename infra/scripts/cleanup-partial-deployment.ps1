# cleanup-partial-deployment.ps1
# Deletes all resources from the partially deployed resource group

param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')]
    [string]$SubscriptionId,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ResourceGroupName,

    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

try {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "AI Hedge Fund - Cleanup Script" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    # Authenticate and set subscription
    Write-Host "Setting Azure subscription..." -ForegroundColor Cyan
    az account set --subscription $SubscriptionId --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw "Failed to set subscription" }

    # Check if resource group exists
    Write-Host "Checking if resource group exists..." -ForegroundColor Cyan
    $rgExists = az group exists --name $ResourceGroupName

    if ($rgExists -eq "false") {
        Write-Host "Resource group '$ResourceGroupName' does not exist. Nothing to clean up." -ForegroundColor Green
        return
    }

    # List resources
    Write-Host ""
    Write-Host "Resources to be deleted:" -ForegroundColor Yellow
    $resources = az resource list --resource-group $ResourceGroupName --query "[].{Name:name, Type:type, Location:location}" -o json | ConvertFrom-Json

    if ($resources.Count -eq 0) {
        Write-Host "No resources found in '$ResourceGroupName'." -ForegroundColor Green
        Write-Host ""
        Write-Host "Do you want to delete the empty resource group? (y/N): " -ForegroundColor Yellow -NoNewline
        $confirm = Read-Host
        if ($confirm -eq 'y' -or $confirm -eq 'Y') {
            if (-not $WhatIf) {
                Write-Host "Deleting resource group..." -ForegroundColor Yellow
                az group delete --name $ResourceGroupName --yes --no-wait
                Write-Host "Resource group deletion initiated (running in background)" -ForegroundColor Green
            } else {
                Write-Host "[WHAT-IF] Would delete resource group: $ResourceGroupName" -ForegroundColor Yellow
            }
        }
        return
    }

    $resources | Format-Table -AutoSize

    Write-Host ""
    Write-Host "Total resources: $($resources.Count)" -ForegroundColor White
    Write-Host ""

    if ($WhatIf) {
        Write-Host "[WHAT-IF MODE] The following resource group would be deleted:" -ForegroundColor Yellow
        Write-Host "  Resource Group: $ResourceGroupName" -ForegroundColor Yellow
        Write-Host "  Resources: $($resources.Count)" -ForegroundColor Yellow
        return
    }

    # Confirm deletion
    Write-Host "WARNING: This will delete ALL resources in '$ResourceGroupName'" -ForegroundColor Red
    Write-Host "Type the resource group name to confirm deletion: " -ForegroundColor Yellow -NoNewline
    $confirmation = Read-Host

    if ($confirmation -ne $ResourceGroupName) {
        Write-Host "Confirmation failed. Aborted." -ForegroundColor Red
        exit 1
    }

    # Delete resource group
    Write-Host ""
    Write-Host "Deleting resource group (this may take several minutes)..." -ForegroundColor Yellow
    az group delete --name $ResourceGroupName --yes --no-wait

    Write-Host ""
    Write-Host "Resource group deletion initiated successfully!" -ForegroundColor Green
    Write-Host "Deletion is running in the background. You can check status with:" -ForegroundColor Cyan
    Write-Host "  az group show --name $ResourceGroupName" -ForegroundColor White
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}
finally {
    $ProgressPreference = 'Continue'
}
