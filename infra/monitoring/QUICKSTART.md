# Quick Deploy Function App

## Fastest Way to Deploy

```powershell
# Make sure you're logged into Azure
az login
az account set --subscription "a604d967-963b-4ff5-acb7-f0aaec811978"

# Deploy with one command
.\infra\scripts\deploy-function.ps1
```

That's it! The script handles everything.

## What the Script Does

1. Packages your function + minimal dependencies (~30KB)
2. Deploys to `hedgefund-monitor` in `rg-ai-hedge-fund`
3. Shows you the status and Azure Portal link

## Required Environment Variables

Make sure these are set in your Function App (check Azure Portal):

```
✅ FINANCIAL_DATASETS_API_KEY
✅ MARKET_MONITOR_QUEUE_CONNECTION_STRING
✅ MARKET_MONITOR_QUEUE_NAME
✅ COSMOS_ENDPOINT
✅ COSMOS_KEY
✅ COSMOS_DATABASE
✅ COSMOS_CONTAINER
```

## After Deployment

**View logs:**
```powershell
az functionapp log tail --name hedgefund-monitor --resource-group rg-ai-hedge-fund
```

**Manual trigger (for testing):**
```powershell
az functionapp function invoke `
    --name hedgefund-monitor `
    --resource-group rg-ai-hedge-fund `
    --function-name market_monitor
```

**Update settings:**
```powershell
az functionapp config appsettings set `
    --name hedgefund-monitor `
    --resource-group rg-ai-hedge-fund `
    --settings "MARKET_MONITOR_WATCHLIST=AAPL,MSFT,NVDA,TSLA"
```

## Dependencies Included

Your function is **lightweight** - it only includes:
- Function code (~10KB)
- 3 modules from `src/`: models.py, cache.py, api.py (~20KB)
- Python packages installed by Azure (pandas, pydantic, requests, etc.)

Total deployment: **~30KB of your code** + pip packages

## Troubleshooting

**"Module not found" error?**
→ Redeploy using the script - it automatically includes the `src` modules

**Function not running?**
→ Check the schedule: it only runs during US market hours (9:30am-4pm ET, Mon-Fri)

**Want to test outside market hours?**
→ Use the manual trigger command above

See `DEPLOYMENT.md` for full details.
