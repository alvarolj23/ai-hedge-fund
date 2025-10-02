# Azure Function Deployment Guide

This guide explains how to deploy the market monitoring Azure Function to your Function App.

## Overview

Your Function App (`hedgefund-monitor`) monitors market activity and triggers analysis jobs. It depends on a few lightweight modules from the `src` directory:

- `src.data.models.Price` - Pydantic model for price data
- `src.tools.api.get_prices` - API client for fetching prices
- `src.data.cache` - Simple in-memory cache

**Total deployment size**: ~50-100KB of Python code (excluding dependencies)

## Prerequisites

1. **Azure CLI** installed and authenticated:
   ```powershell
   az login
   az account set --subscription "a604d967-963b-4ff5-acb7-f0aaec811978"
   ```

2. **Function App Configuration**: Ensure your Function App has the required environment variables configured. Check the Azure Portal or run:
   ```powershell
   az functionapp config appsettings list `
       --name hedgefund-monitor `
       --resource-group rg-ai-hedge-fund
   ```

   Required settings (see `infra/monitoring/README.md` for full list):
   - `FINANCIAL_DATASETS_API_KEY`
   - `MARKET_MONITOR_QUEUE_CONNECTION_STRING`
   - `MARKET_MONITOR_QUEUE_NAME`
   - `COSMOS_ENDPOINT`
   - `COSMOS_KEY`
   - `COSMOS_DATABASE`
   - `COSMOS_CONTAINER`

## Deployment Method 1: Using the Deployment Script (Recommended)

Run the provided PowerShell script from anywhere:

```powershell
.\infra\scripts\deploy-function.ps1
```

Or with explicit parameters:

```powershell
.\infra\scripts\deploy-function.ps1 -FunctionAppName "hedgefund-monitor" -ResourceGroup "rg-ai-hedge-fund"
```

The script will:
1. ✅ Create a temporary deployment package
2. ✅ Copy function code and only the required `src` modules
3. ✅ Create a ZIP archive
4. ✅ Deploy to Azure with remote build
5. ✅ Show deployment status and portal link
6. ✅ Clean up temporary files

### What Gets Deployed

```
function-package/
├── host.json                    # Azure Functions configuration
├── requirements.txt             # Python dependencies
├── market_monitor/              # Your function code
│   ├── __init__.py
│   └── function.json
└── src/                         # Minimal dependencies (only ~3 files)
    ├── __init__.py
    ├── data/
    │   ├── __init__.py
    │   ├── models.py            # ~5KB - Pydantic models
    │   └── cache.py             # ~3KB - Simple cache
    └── tools/
        ├── __init__.py
        └── api.py               # ~12KB - API client
```

**Total Python code**: ~20KB + function code (~10KB) = **~30KB**

## Deployment Method 2: Manual Deployment with Azure Functions Core Tools

If you prefer to use the Azure Functions Core Tools:

```powershell
# Navigate to monitoring directory
cd infra\monitoring

# Ensure src modules are accessible (temporary workaround)
# The function uses sys.path manipulation to find them

# Deploy using func CLI
func azure functionapp publish hedgefund-monitor --python
```

## Deployment Method 3: Direct ZIP Upload

For manual control:

```powershell
# Create the package manually
$WorkspaceRoot = "c:\Users\ama5332\OneDrive - Toyota Motor Europe\Documents\genai\ai-hedge-fund"
$TempDir = "$env:TEMP\function-deploy"
$ZipFile = "$env:TEMP\function-app.zip"

# Copy files
New-Item -ItemType Directory -Path $TempDir -Force
Copy-Item -Path "$WorkspaceRoot\infra\monitoring\*" -Destination $TempDir -Recurse -Exclude '.venv','__pycache__','.vscode','local.settings.json'

# Copy src dependencies
New-Item -ItemType Directory -Path "$TempDir\src\data" -Force
New-Item -ItemType Directory -Path "$TempDir\src\tools" -Force
Copy-Item -Path "$WorkspaceRoot\src\__init__.py" -Destination "$TempDir\src\" -ErrorAction SilentlyContinue
Copy-Item -Path "$WorkspaceRoot\src\data\*.py" -Destination "$TempDir\src\data\"
Copy-Item -Path "$WorkspaceRoot\src\tools\api.py" -Destination "$TempDir\src\tools\"
New-Item -Path "$TempDir\src\tools\__init__.py" -ItemType File -Force

# Create ZIP
Compress-Archive -Path "$TempDir\*" -DestinationPath $ZipFile -Force

# Deploy
az functionapp deployment source config-zip `
    --resource-group rg-ai-hedge-fund `
    --name hedgefund-monitor `
    --src $ZipFile `
    --build-remote true

# Cleanup
Remove-Item -Path $TempDir -Recurse -Force
Remove-Item -Path $ZipFile -Force
```

## Verify Deployment

### Check Function Status

```powershell
az functionapp show `
    --name hedgefund-monitor `
    --resource-group rg-ai-hedge-fund `
    --query "{name:name, state:state, hostname:defaultHostName}"
```

### View Logs

```powershell
# Stream live logs
az functionapp log tail `
    --name hedgefund-monitor `
    --resource-group rg-ai-hedge-fund

# Or view in Application Insights
az monitor app-insights component show `
    --app hedgefund-appi `
    --resource-group rg-ai-hedge-fund
```

### Test the Function

The function runs on a timer (every 5 minutes during market hours). To manually trigger it:

1. Go to Azure Portal
2. Navigate to your Function App: `hedgefund-monitor`
3. Go to Functions → `market_monitor`
4. Click "Code + Test"
5. Click "Test/Run" and "Run"

Or trigger via Azure CLI:

```powershell
az functionapp function invoke `
    --name hedgefund-monitor `
    --resource-group rg-ai-hedge-fund `
    --function-name market_monitor
```

## Configuration Updates

To update environment variables after deployment:

```powershell
# Set a single variable
az functionapp config appsettings set `
    --name hedgefund-monitor `
    --resource-group rg-ai-hedge-fund `
    --settings "MARKET_MONITOR_WATCHLIST=AAPL,MSFT,NVDA,TSLA"

# Set multiple variables
az functionapp config appsettings set `
    --name hedgefund-monitor `
    --resource-group rg-ai-hedge-fund `
    --settings `
        "MARKET_MONITOR_PERCENT_CHANGE_THRESHOLD=0.02" `
        "MARKET_MONITOR_VOLUME_SPIKE_MULTIPLIER=1.5" `
        "MARKET_MONITOR_COOLDOWN_SECONDS=1800"
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'src'`:

- **Cause**: The deployment package doesn't include the `src` directory
- **Fix**: Use the deployment script which automatically includes the required modules

### Remote Build Failures

If remote build fails with package installation errors:

```powershell
# Check build logs
az functionapp deployment list `
    --name hedgefund-monitor `
    --resource-group rg-ai-hedge-fund

# View specific deployment
az functionapp deployment show `
    --name hedgefund-monitor `
    --resource-group rg-ai-hedge-fund `
    --deployment-id <deployment-id>
```

### Function Not Triggering

1. Check the timer schedule in `market_monitor/function.json`
2. Verify the function is enabled:
   ```powershell
   az functionapp function show `
       --name hedgefund-monitor `
       --resource-group rg-ai-hedge-fund `
       --function-name market_monitor
   ```

3. Check Application Insights for errors

## Making the Function Even Lighter

If you want to eliminate the `src` dependency entirely, you can:

1. **Copy the minimal code directly into the function**:
   - Copy `Price` model into `market_monitor/__init__.py`
   - Inline the `get_prices` API call
   - Remove `src` imports

2. **Create a standalone module**:
   - Create `infra/monitoring/shared/api.py` with just what you need
   - Update imports in `market_monitor/__init__.py`

Let me know if you'd like me to create this standalone version!

## Next Steps

After successful deployment:

1. ✅ Monitor the first few executions in Application Insights
2. ✅ Verify messages are being sent to the analysis queue
3. ✅ Check Cosmos DB for cooldown records
4. ✅ Adjust thresholds based on alert frequency

## Resources

- [Azure Functions Python Developer Guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [Function App Settings Reference](https://learn.microsoft.com/en-us/azure/azure-functions/functions-app-settings)
- [Application Insights for Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-monitoring)
