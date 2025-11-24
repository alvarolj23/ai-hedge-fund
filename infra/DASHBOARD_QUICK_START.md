# Dashboard Deployment - Quick Reference

## 🚀 FASTEST WAY TO DEPLOY (5 Minutes)

### Run the Complete Automated Script

```powershell
cd infra
.\deploy-dashboard-complete.ps1 -GitHubRepo "alvarolj23/ai-hedge-fund"
```

This script does EVERYTHING:
1. ✅ Creates missing Cosmos DB containers (`analyst-signals`, `portfolioSnapshots`, etc.)
2. ✅ Deploys Static Web App using Bicep infrastructure-as-code
3. ✅ Configures environment variables
4. ✅ Builds the dashboard
5. ✅ Deploys to Azure

**That's it!** One command and you're done.

---

## 📋 WHAT EACH SCRIPT DOES

### `deploy-dashboard-complete.ps1` ⭐ (USE THIS ONE)
**Purpose:** Complete end-to-end deployment
**What it does:**
- Creates missing Cosmos DB containers
- Deploys infrastructure (Static Web App)
- Builds and deploys dashboard
- Configures everything automatically

**When to use:** First-time setup OR anytime you want to redeploy

---

### `deploy-dashboard.ps1` (OLD - PARTIAL)
**Purpose:** Only builds and checks if app exists
**What it does:**
- Builds the dashboard
- Checks if Static Web App exists
- Shows manual deployment instructions

**When to use:** Only for building locally, not for deployment

---

### `update-backend-api.ps1` (NOT NEEDED)
**Purpose:** Update Container App backend
**What it does:**
- Creates new Container App revision

**When to use:** NEVER - The `publish-app.yml` workflow handles this automatically when you push backend changes

---

## 🔄 GITHUB ACTIONS WORKFLOWS

### `.github/workflows/publish-app.yml` ✅
**Triggers:** Backend code changes
**What it does:**
- Builds Docker image
- Pushes to Azure Container Registry
- Updates Container App
- Deploys Function App

**Status:** ✅ Working - Handles all backend deployments

---

### `.github/workflows/dashboard-deploy.yml` ✅ (FIXED)
**Triggers:** Dashboard code changes
**What it does:**
- Builds React dashboard
- Deploys to Static Web App

**Status:** ✅ Fixed - Will work once you add the GitHub secret

---

## ⚙️ SETUP GITHUB ACTIONS (ONE-TIME)

After running `deploy-dashboard-complete.ps1`, set up GitHub Actions:

### Step 1: Get Deployment Token

**Option A: From Script Output**
The script will show you the deployment token after it runs.

**Option B: From Azure Portal**
1. Go to https://portal.azure.com
2. Navigate to: `rg-ai-hedge-fund-prod` → `aihedgefund-dashboard`
3. Click "Settings" → "Deployment tokens"
4. Copy the token

### Step 2: Add to GitHub Secrets

1. Go to: https://github.com/alvarolj23/ai-hedge-fund/settings/secrets/actions
2. Click "New repository secret"
3. Add two secrets:

**Secret 1:**
- Name: `AZURE_STATIC_WEB_APPS_API_TOKEN`
- Value: <paste the deployment token from Step 1>

**Secret 2:**
- Name: `VITE_API_URL`
- Value: `https://aihedgefund-api.wittysand-2cb74b22.westeurope.azurecontainerapps.io`

### Step 3: Test It

```bash
# Make a small change to trigger the workflow
cd dashboard
echo "// test" >> src/App.tsx
git add .
git commit -m "test: trigger dashboard deployment"
git push
```

Watch the workflow run at: https://github.com/alvarolj23/ai-hedge-fund/actions

---

## 📊 COSMOS DB CONTAINERS

After running `deploy-dashboard-complete.ps1`, you'll have:

| Container | Purpose | Created By |
|-----------|---------|------------|
| `broker-orders` | Trade history | ✅ Already exists |
| `monitor-cooldowns` | Function App cooldowns | ✅ Already exists |
| `analyst-signals` | AI agent recommendations | ✅ Script creates this |
| `decisions` | Portfolio Manager decisions | ✅ Script creates this |
| `portfolioSnapshots` | Historical portfolio values | ✅ Script creates this |
| `hedgeFundResults` | Full analysis results | ✅ Script creates this |
| `hedgeFundStatus` | Job status tracking | ✅ Script creates this |

---

## 🎯 DECISION TREE: WHICH SCRIPT TO USE?

```
Need to deploy dashboard for first time?
  → Run: deploy-dashboard-complete.ps1

Need to redeploy dashboard?
  → Run: deploy-dashboard-complete.ps1
  OR
  → Just push to GitHub (if secrets are set up)

Need to update backend API?
  → Just push backend code - publish-app.yml handles it automatically
  → DON'T use update-backend-api.ps1

Need to just build dashboard locally?
  → cd dashboard && npm run build

Need to test backend APIs?
  → Run: python test-dashboard-api.py
```

---

## ✅ VERIFICATION CHECKLIST

After running `deploy-dashboard-complete.ps1`:

- [ ] Script completed without errors
- [ ] Static Web App created in Azure Portal
- [ ] Dashboard URL works (https://*.azurestaticapps.net)
- [ ] Cosmos DB has all 7 containers
- [ ] GitHub secrets added (for future auto-deployments)
- [ ] All dashboard pages load correctly

---

## 🆘 TROUBLESHOOTING

### Script fails: "Cosmos account not found"
**Solution:** Specify the Cosmos account name:
```powershell
.\deploy-dashboard-complete.ps1 `
  -CosmosAccountName "your-cosmos-account-name" `
  -GitHubRepo "alvarolj23/ai-hedge-fund"
```

### Script fails: "Static Web App already exists"
**That's OK!** The script will detect it and continue deploying.

### GitHub Actions fails: "deployment_token was not provided"
**Solution:** Add the `AZURE_STATIC_WEB_APPS_API_TOKEN` secret (see Setup section above)

### Dashboard shows blank page
**Check:**
1. Is `VITE_API_URL` set correctly in Static Web App settings?
2. Try clearing browser cache
3. Check browser console for errors (F12)

---

## 📁 FILE CLEANUP

You can **delete** these old/redundant files:
- `deploy-dashboard.ps1` (replaced by `deploy-dashboard-complete.ps1`)
- `update-backend-api.ps1` (redundant with `publish-app.yml`)
- `dashboard/deploy.sh` (redundant)

Keep these:
- `deploy-dashboard-complete.ps1` ⭐
- `test-dashboard-api.py` ⭐
- `DASHBOARD_DEPLOYMENT.md` ⭐
