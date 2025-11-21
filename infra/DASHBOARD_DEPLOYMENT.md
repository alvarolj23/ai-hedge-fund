# Dashboard Deployment Guide

This guide explains how to deploy and manage the AI Hedge Fund Analytics Dashboard.

## Overview

The dashboard consists of two components:
1. **Backend API** - FastAPI endpoints (deployed to existing Container App)
2. **Frontend UI** - React dashboard (deployed to Azure Static Web Apps - FREE)

## Prerequisites

- Azure CLI installed and logged in (`az login`)
- Node.js 18+ installed
- Python 3.11+ (for testing scripts)
- Access to `rg-ai-hedge-fund-prod` resource group

## Quick Start (3 Steps)

### Step 1: Update Backend API

This deploys the new dashboard API endpoints to your existing Container App.

**PowerShell:**
```powershell
cd infra
.\update-backend-api.ps1
```

**Bash:**
```bash
cd infra
# Use Azure Portal to create a new revision instead
# Go to: Container App → Revision Management → Create new revision
```

**What it does:**
- Creates a new revision of `aihedgefund-api` Container App
- Restarts the container to load new code
- Tests the new dashboard endpoints

### Step 2: Test Backend Endpoints

Run the Python test script to verify all endpoints work:

```bash
cd infra
python test-dashboard-api.py
```

**Expected output:**
```
================================================================
AI HEDGE FUND DASHBOARD API TESTS
================================================================

Testing: Health Check
✅ Status Code: 200

Testing: Portfolio Summary
✅ Status Code: 200

... (8 more tests)

TEST SUMMARY
Total Tests: 9
✅ Passed: 9
❌ Failed: 0
```

**Common issues:**
- **404 errors**: Backend not updated → Run Step 1
- **Alpaca errors**: Missing credentials → Set `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` in Container App
- **Cosmos DB errors**: Check `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DATABASE` env vars

### Step 3: Deploy Dashboard Frontend

Deploy the React dashboard to Azure Static Web Apps (FREE tier).

**PowerShell:**
```powershell
cd infra
.\deploy-dashboard.ps1
```

**Bash:**
```bash
cd infra
chmod +x deploy-dashboard.sh
./deploy-dashboard.sh
```

**What it does:**
- Builds the React dashboard (`dashboard/dist`)
- Creates Azure Static Web App (if not exists)
- Configures environment variables
- Provides deployment instructions

**Deployment URL:** The script will output your dashboard URL like:
```
🌐 Dashboard URL: https://aihedgefund-dashboard-<random>.azurestaticapps.net
```

## Deployment Scripts

### 1. `update-backend-api.ps1`

Updates the Container App with new API endpoints.

**Usage:**
```powershell
.\update-backend-api.ps1 [-ResourceGroup "rg-name"] [-ContainerAppName "app-name"]
```

**Parameters:**
- `ResourceGroup` - Azure resource group (default: `rg-ai-hedge-fund-prod`)
- `ContainerAppName` - Container App name (default: `aihedgefund-api`)

### 2. `test-dashboard-api.py`

Tests all dashboard and configuration API endpoints.

**Usage:**
```bash
# Test default API URL
python test-dashboard-api.py

# Test custom API URL
python test-dashboard-api.py https://your-api.azurecontainerapps.io
```

**Tests performed:**
- ✅ Health check (`/`)
- ✅ Portfolio summary (`/dashboard/portfolio`)
- ✅ System health (`/dashboard/system-health`)
- ✅ Performance metrics (`/dashboard/metrics`)
- ✅ Trade history (`/dashboard/trades`)
- ✅ Agent performance (`/dashboard/agent-performance`)
- ✅ Portfolio history (`/dashboard/portfolio-history`)
- ✅ Monitor config (`/config/monitor`)
- ✅ Trading config (`/config/trading`)

### 3. `deploy-dashboard.ps1` / `deploy-dashboard.sh`

Deploys the React dashboard to Azure Static Web Apps.

**PowerShell Usage:**
```powershell
.\deploy-dashboard.ps1 `
    [-ResourceGroup "rg-name"] `
    [-AppName "app-name"] `
    [-Location "region"] `
    [-ApiUrl "https://api-url"]
```

**Bash Usage:**
```bash
./deploy-dashboard.sh [resource-group] [app-name] [location] [api-url]
```

**Parameters:**
- `ResourceGroup` - Azure resource group (default: `rg-ai-hedge-fund-prod`)
- `AppName` - Static Web App name (default: `aihedgefund-dashboard`)
- `Location` - Azure region (default: `westeurope`)
- `ApiUrl` - Backend API URL (default: your Container App URL)

## Dashboard Pages

Once deployed, the dashboard provides:

### 1. Portfolio Page (`/portfolio`)
- Real-time portfolio summary from Alpaca
- Current positions with P&L
- Cash available and buying power
- Refreshes every 30 seconds

### 2. Analytics Page (`/analytics`)
- Trading performance metrics (win rate, returns, Sharpe ratio)
- AI agent performance leaderboard
- Best/worst performing analysts
- Signal accuracy tracking

### 3. Trades Page (`/trades`)
- Complete trade history from Cosmos DB
- Filter by ticker, action, date range
- Pagination (20 trades per page)
- Trade details and confidence scores

### 4. Monitoring Page (`/monitoring`)
- System health status
- Alpaca API connection status
- Cosmos DB connection status
- Azure Queue depth and health

### 5. Config Page (`/config`)
- Market monitor settings (watchlist, thresholds, cooldown)
- Trading configuration (confidence, mode, dry run)
- Generates Azure CLI commands for configuration changes

## Environment Variables

### Backend (Container App)

Required for dashboard functionality:

| Variable | Description | Example |
|----------|-------------|---------|
| `APCA_API_KEY_ID` | Alpaca API key | `PK...` |
| `APCA_API_SECRET_KEY` | Alpaca secret key | `...` |
| `COSMOS_ENDPOINT` | Cosmos DB endpoint | `https://...` |
| `COSMOS_KEY` | Cosmos DB key | `...` |
| `COSMOS_DATABASE` | Database name | `ai-hedge-fund` |

Set in Azure Portal:
```
Container App → Settings → Environment variables
```

### Frontend (Static Web App)

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `https://aihedgefund-api...azurecontainerapps.io` |

Set in Azure Portal:
```
Static Web App → Configuration → Application settings
```

Or via CLI:
```bash
az staticwebapp appsettings set \
  --name aihedgefund-dashboard \
  --resource-group rg-ai-hedge-fund-prod \
  --setting-names VITE_API_URL=https://your-api-url
```

## Automated Deployment (GitHub Actions)

The dashboard includes a GitHub Actions workflow for automated deployment.

**Workflow file:** `.github/workflows/dashboard-deploy.yml`

**Trigger:**
- Push to `main` or `claude/*` branches
- Changes in `dashboard/` or backend API files
- Manual workflow dispatch

**Setup:**
1. Create Static Web App in Azure Portal
2. Copy deployment token
3. Add to GitHub Secrets as `AZURE_STATIC_WEB_APPS_API_TOKEN`
4. Add `VITE_API_URL` to GitHub Secrets
5. Push changes → Auto-deploys

## Troubleshooting

### Backend API returns 404
**Cause:** Container App not updated with new code

**Solution:**
```powershell
cd infra
.\update-backend-api.ps1
```

### Dashboard shows "Error loading portfolio"
**Cause:** Missing Alpaca credentials

**Solution:**
1. Go to Azure Portal → Container App
2. Settings → Environment variables
3. Add:
   - `APCA_API_KEY_ID`
   - `APCA_API_SECRET_KEY`
4. Restart Container App

### Dashboard shows empty data
**Cause:** No trades executed yet (normal for new deployments)

**Solution:** Generate test data:
```powershell
cd infra
.\test-queue.ps1 -Tickers "NVDA" -LookbackDays 30
```

### Build fails with "Module not found"
**Cause:** Dependencies not installed

**Solution:**
```bash
cd dashboard
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Static Web App deployment fails
**Cause:** GitHub token expired or incorrect permissions

**Solution:**
1. Regenerate deployment token in Azure Portal
2. Update GitHub Secret
3. Re-run workflow

## Cost Breakdown

| Component | Tier | Monthly Cost |
|-----------|------|--------------|
| **Azure Static Web Apps** | Free | $0.00 |
| **Container App API** | Existing | $0.00 (no change) |
| **Cosmos DB Queries** | Free tier | $0.00 |
| **Application Insights** | Pay-as-you-go | ~$2.30 |
| **TOTAL** | | **~$2.30/month** |

## Manual Deployment Steps

If scripts don't work, follow these manual steps:

### Backend Update

1. Azure Portal → `rg-ai-hedge-fund-prod` → `aihedgefund-api`
2. Revision Management → Create new revision
3. Click "Create" (keeps same image, restarts container)
4. Wait 2-3 minutes for new revision to be active

### Frontend Deployment

1. Build dashboard:
   ```bash
   cd dashboard
   npm install
   npm run build
   ```

2. Azure Portal → Create Resource → "Static Web App"
   - Name: `aihedgefund-dashboard`
   - Resource Group: `rg-ai-hedge-fund-prod`
   - Region: West Europe
   - SKU: Free
   - Deployment: GitHub (or manual)

3. Configure environment variable:
   - Configuration → Application settings
   - Add: `VITE_API_URL` = `https://aihedgefund-api...azurecontainerapps.io`

4. If using GitHub:
   - Copy deployment token
   - Add to repo secrets
   - Push to trigger deployment

## Support

For issues or questions:
1. Check this documentation
2. Run test script: `python test-dashboard-api.py`
3. Check Azure Portal logs:
   - Container App → Log stream
   - Static Web App → Functions
4. Review GitHub Actions logs (if using automated deployment)
