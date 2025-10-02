# Deploy Azure Function App
# This script packages and deploys the market monitoring function

param(
    [string]$FunctionAppName = "hedgefund-monitor",
    [string]$ResourceGroup = "rg-ai-hedge-fund"
)

$ErrorActionPreference = "Stop"

Write-Host "==> Deploying Azure Function: $FunctionAppName" -ForegroundColor Cyan

# Get workspace root (two levels up from this script)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$MonitoringDir = Join-Path $WorkspaceRoot "infra\monitoring"
$SrcDir = Join-Path $WorkspaceRoot "src"
$TempDir = Join-Path $env:TEMP "azure-function-deploy-$(Get-Date -Format 'yyyyMMddHHmmss')"

Write-Host "Workspaces: $WorkspaceRoot" -ForegroundColor Gray
Write-Host "Monitoring dir: $MonitoringDir" -ForegroundColor Gray
Write-Host "Temp dir: $TempDir" -ForegroundColor Gray

try {
    # Create temporary deployment directory
    Write-Host "`n[PACKAGE] Creating deployment package..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

    # Copy function app files
    Write-Host "  + Copying function app files..." -ForegroundColor Gray
    Copy-Item -Path "$MonitoringDir\*" -Destination $TempDir -Recurse -Force -Exclude @('.venv', '__pycache__', '.vscode', 'local.settings.json', '*.md')

    # Copy necessary src modules
    Write-Host "  + Copying src dependencies..." -ForegroundColor Gray
    $TempSrcDir = Join-Path $TempDir "src"
    New-Item -ItemType Directory -Path $TempSrcDir -Force | Out-Null
    New-Item -ItemType Directory -Path "$TempSrcDir\data" -Force | Out-Null
    New-Item -ItemType Directory -Path "$TempSrcDir\tools" -Force | Out-Null

    # Copy only required files
    Copy-Item -Path "$SrcDir\__init__.py" -Destination "$TempSrcDir\__init__.py" -Force -ErrorAction SilentlyContinue
    Copy-Item -Path "$SrcDir\data\__init__.py" -Destination "$TempSrcDir\data\__init__.py" -Force -ErrorAction SilentlyContinue
    Copy-Item -Path "$SrcDir\data\models.py" -Destination "$TempSrcDir\data\models.py" -Force
    Copy-Item -Path "$SrcDir\data\cache.py" -Destination "$TempSrcDir\data\cache.py" -Force
    Copy-Item -Path "$SrcDir\tools\__init__.py" -Destination "$TempSrcDir\tools\__init__.py" -Force -ErrorAction SilentlyContinue
    Copy-Item -Path "$SrcDir\tools\api.py" -Destination "$TempSrcDir\tools\api.py" -Force

    # Create deployment package
    $ZipFile = Join-Path $env:TEMP "function-app-$(Get-Date -Format 'yyyyMMddHHmmss').zip"
    Write-Host "  + Creating ZIP archive..." -ForegroundColor Gray
    
    Push-Location $TempDir
    Compress-Archive -Path ".\*" -DestinationPath $ZipFile -Force
    Pop-Location

    Write-Host "  + Package created: $ZipFile" -ForegroundColor Green
    Write-Host "    Size: $([math]::Round((Get-Item $ZipFile).Length / 1MB, 2)) MB" -ForegroundColor Gray

    # Deploy to Azure
    Write-Host "`n[CLOUD] Deploying to Azure..." -ForegroundColor Yellow
    Write-Host "  Function App: $FunctionAppName" -ForegroundColor Gray
    Write-Host "  Resource Group: $ResourceGroup" -ForegroundColor Gray

    # Run the deployment command
    $deployCommand = "az functionapp deployment source config-zip --resource-group '$ResourceGroup' --name '$FunctionAppName' --src '$ZipFile' --build-remote true --timeout 600"
    Invoke-Expression $deployCommand
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        Write-Host "`n[SUCCESS] Deployment successful!" -ForegroundColor Green
        Write-Host "`n[STATUS] Checking function status..." -ForegroundColor Yellow
        
        # Get function app details
        $functionApp = az functionapp show `
            --name $FunctionAppName `
            --resource-group $ResourceGroup `
            --output json | ConvertFrom-Json

        Write-Host "  State: $($functionApp.state)" -ForegroundColor Gray
        Write-Host "  Default hostname: $($functionApp.defaultHostName)" -ForegroundColor Gray
        Write-Host "`n[LINK] View in Azure Portal:" -ForegroundColor Cyan
        Write-Host "  https://portal.azure.com/#resource$($functionApp.id)" -ForegroundColor Blue
        
        Write-Host "`n[TIP] To view logs, run:" -ForegroundColor Cyan
        Write-Host "  az functionapp log tail --name $FunctionAppName --resource-group $ResourceGroup" -ForegroundColor Gray
    } else {
        Write-Host "`n[ERROR] Deployment failed with exit code $exitCode!" -ForegroundColor Red
        exit 1
    }

} catch {
    Write-Host "`n[ERROR] Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ScriptStackTrace) {
        Write-Host $_.ScriptStackTrace -ForegroundColor Red
    }
    exit 1
} finally {
    # Cleanup
    if (Test-Path $TempDir) {
        Write-Host "`n[CLEANUP] Cleaning up temporary files..." -ForegroundColor Gray
        Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $ZipFile) {
        Remove-Item -Path $ZipFile -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "`n[DONE] Done!" -ForegroundColor Green
