# AI Hedge Fund - Azure Deployment Guide

This guide walks you through deploying the AI Hedge Fund application to Azure using **common shared infrastructure** (Cosmos DB and Container Registry).

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Deployment Steps](#deployment-steps)
  - [Day 1: Infrastructure Deployment](#day-1-infrastructure-deployment)
  - [Day 2: Application Deployment](#day-2-application-deployment)
  - [Day 3: Function App Deployment](#day-3-function-app-deployment)
  - [Day 4: Integration Testing](#day-4-integration-testing)
  - [Day 5: Monitoring & Optimization](#day-5-monitoring--optimization)
- [Troubleshooting](#troubleshooting)
- [Cost Optimization](#cost-optimization)

---

## Prerequisites

### Required Software
- **Azure CLI** (2.50.0 or higher)
  ```powershell
  az --version
  ```
- **PowerShell 5.1 or higher**
- **Azure Subscription** with Contributor access
- **GitHub account** (for CI/CD workflow)

### Required Azure Resources (Existing)
- **Resource Group**: `rg-common-infra` (or your common infra RG)
- **Cosmos DB Account**: `cosmos-cryptoanalysis-prod-cqpvo3njb4joq` (or your existing account)
- **Container Registry (ACR)**: `acrcryptoanalysisprodcqpvo3njb4joq` (or your existing ACR)

### Required API Keys
You'll need API keys for:
- **Alpaca API** (paper trading)
- **FinancialDatasets.ai API** (market data)
- **OpenAI API** (or other LLM providers)
- Any other LLM providers you're using (Anthropic, Groq, etc.)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ Azure Function App (Timer Trigger)                          │
│ Triggers every 5 minutes during market hours                │
│ Checks cooldown → Sends message to queue                    │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ Azure Storage Queue (analysis-requests)                     │
│ Message queue for analysis jobs                             │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ Container Apps Job (Event-driven Worker)                    │
│ Scales 0-10 based on queue depth                            │
│ Runs your AI hedge fund analysis (main.py)                  │
│ Places paper trades via Alpaca API                          │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ Cosmos DB (8 Containers)                                    │
│ Stores portfolios, signals, decisions, results              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ API Container App (Optional Web UI)                         │
│ FastAPI web interface to view results                       │
│ Port 8000, scales 0-2                                        │
└─────────────────────────────────────────────────────────────┘
```

### Resources Created

**New Resource Group** (`rg-ai-hedge-fund-prod`):
- Storage Account + 2 Queues
- Log Analytics Workspace
- Application Insights
- Container Apps Environment
- API Container App
- Queue Worker Job
- Function App + App Service Plan

**Shared from Common Infrastructure** (`rg-common-infra`):
- Cosmos DB Account (with new database: `ai-hedge-fund`)
- Container Registry (ACR)

---

## Deployment Steps

### Day 1: Infrastructure Deployment

#### Step 1: Clean Up Partial Deployment (If Needed)

If you have a partially deployed resource group, clean it up first:

```powershell
cd C:\path\to\ai-hedge-fund

# Review resources to be deleted
.\infra\scripts\cleanup-partial-deployment.ps1 `
  -SubscriptionId "052a660f-155b-47e9-9e3a-67edf5f585e1" `
  -ResourceGroupName "rg-ai-hedge-fund-prod" `
  -WhatIf

# Confirm and delete
.\infra\scripts\cleanup-partial-deployment.ps1 `
  -SubscriptionId "052a660f-155b-47e9-9e3a-67edf5f585e1" `
  -ResourceGroupName "rg-ai-hedge-fund-prod"
```

**Wait 5-10 minutes** for the resource group to be fully deleted before proceeding.

---

#### Step 2: Deploy Infrastructure with Common Resources

Run the master deployment script:

```powershell
.\infra\scripts\deploy-with-common-infra.ps1 `
  -SubscriptionId "052a660f-155b-47e9-9e3a-67edf5f585e1" `
  -ResourceGroupName "rg-ai-hedge-fund-prod" `
  -CommonInfraResourceGroup "rg-common-infra" `
  -CommonCosmosAccountName "cosmos-cryptoanalysis-prod-cqpvo3njb4joq" `
  -CommonAcrName "acrcryptoanalysisprodcqpvo3njb4joq" `
  -NamePrefix "aihedgefund" `
  -Location "westeurope" `
  -DatabaseName "ai-hedge-fund" `
  -UsePlaceholderImages
```

**Parameters Explained:**
- `SubscriptionId`: Your Azure subscription ID
- `ResourceGroupName`: **New** resource group for AI hedge fund resources
- `CommonInfraResourceGroup`: **Existing** common infrastructure resource group
- `CommonCosmosAccountName`: **Existing** Cosmos DB account name
- `CommonAcrName`: **Existing** Container Registry name
- `NamePrefix`: Prefix for all resource names (default: `aihedgefund`)
- `Location`: Azure region (default: `westeurope`)
- `DatabaseName`: Name of database to create in Cosmos DB
- `UsePlaceholderImages`: Use Microsoft's hello-world images initially (recommended)

**What This Does:**
1. Authenticates with Azure
2. Verifies common infrastructure exists
3. Creates Cosmos DB database + 8 containers (with correct `/partition_key`)
4. Deploys all Azure infrastructure to new resource group
5. Configures Container Apps to use shared ACR
6. Saves deployment outputs to `infra/scripts/latest-deployment.json`

**Expected Duration:** 8-12 minutes

---

#### Step 3: Verify Deployment

```powershell
.\infra\scripts\verify-deployment.ps1 `
  -SubscriptionId "052a660f-155b-47e9-9e3a-67edf5f585e1" `
  -ResourceGroupName "rg-ai-hedge-fund-prod" `
  -CommonInfraResourceGroup "rg-common-infra" `
  -CommonCosmosAccountName "cosmos-cryptoanalysis-prod-cqpvo3njb4joq" `
  -CommonAcrName "acrcryptoanalysisprodcqpvo3njb4joq"
```

**Expected Output:**
- All resources should show ✓ OK
- Docker images will show as "not found" (expected - we build them next)

---

### Day 2: Application Deployment

#### Step 1: Prepare GitHub Secrets

You need to configure GitHub secrets and variables for the CI/CD pipeline.

**Create GitHub Variables** (Repository Settings → Secrets and variables → Actions → Variables):
```
SUBSCRIPTION_ID = "052a660f-155b-47e9-9e3a-67edf5f585e1"
RESOURCE_GROUP = "rg-ai-hedge-fund-prod"
```

**Create GitHub Secrets** (Repository Settings → Secrets and variables → Actions → Secrets):

1. **`AZURE_CREDENTIALS`** - Service Principal credentials:
   ```bash
   # Create a service principal
   az ad sp create-for-rbac --name "ai-hedge-fund-github" \
     --role contributor \
     --scopes /subscriptions/052a660f-155b-47e9-9e3a-67edf5f585e1/resourceGroups/rg-ai-hedge-fund-prod \
     --sdk-auth
   ```
   Copy the entire JSON output and paste as the secret value.

2. **`DEPLOYMENT_CONFIG`** - Application settings and API keys:
   ```json
   {
     "apiAppSettings": {
       "OPENAI_API_KEY": "sk-your-openai-key",
       "FINANCIAL_DATASETS_API_KEY": "your-financial-datasets-key"
     },
     "workerAppSettings": {
       "OPENAI_API_KEY": "sk-your-openai-key",
       "FINANCIAL_DATASETS_API_KEY": "your-financial-datasets-key",
       "ALPACA_API_KEY": "your-alpaca-key",
       "ALPACA_SECRET_KEY": "your-alpaca-secret",
       "ALPACA_BASE_URL": "https://paper-api.alpaca.markets",
       "TRADE_MODE": "paper"
     },
     "functionAppSettings": {
       "TICKERS": "AAPL,GOOGL,MSFT,NVDA,TSLA"
     }
   }
   ```

   **Important:** Replace all placeholder keys with your actual API keys!

---

#### Step 2: Build and Push Docker Images via GitHub Workflow

**Option A: Using GitHub UI** (Recommended)
1. Go to your repository on GitHub
2. Navigate to **Actions** tab
3. Select **Publish application** workflow
4. Click **Run workflow**
5. Leave image tags empty (will use commit SHA)
6. Click **Run workflow**

**Option B: Using GitHub CLI** (if installed)
```powershell
gh workflow run publish-app.yml
```

**What This Does:**
1. Builds Docker images for API and Worker
2. Pushes images to your shared ACR
3. Updates Container Apps to use new images
4. Configures all environment variables and secrets

**Expected Duration:** 10-15 minutes

**Monitor Progress:**
- Go to Actions tab in GitHub
- Click on the running workflow
- Watch logs for any errors

---

#### Step 3: Verify Docker Images

```powershell
# Login to ACR
az acr login --name acrcryptoanalysisprodcqpvo3njb4joq

# List images
az acr repository list --name acrcryptoanalysisprodcqpvo3njb4joq --output table

# Expected output:
# ai-hedge-fund-api
# ai-hedge-fund-worker
```

---

### Day 3: Function App Deployment

The Function App monitors the market and triggers analysis jobs.

#### Step 1: Get Function App Name

```powershell
# From deployment outputs
$outputs = Get-Content .\infra\scripts\latest-deployment.json | ConvertFrom-Json
$functionAppName = $outputs.functionAppName.value
Write-Host "Function App Name: $functionAppName"
```

#### Step 2: Deploy Function App Code

```powershell
.\infra\scripts\deploy-function.ps1 `
  -SubscriptionId "052a660f-155b-47e9-9e3a-67edf5f585e1" `
  -ResourceGroupName "rg-ai-hedge-fund-prod"
```

**What This Does:**
1. Packages the Function App code from `infra/monitoring/`
2. Deploys to Azure Function App
3. Configures timer trigger (runs every 5 minutes)

**Expected Duration:** 2-3 minutes

---

#### Step 3: Test Function App

```powershell
# Manually trigger the function
az functionapp function invoke `
  --resource-group "rg-ai-hedge-fund-prod" `
  --name $functionAppName `
  --function-name "market_monitor"

# Check logs
az functionapp logs tail `
  --resource-group "rg-ai-hedge-fund-prod" `
  --name $functionAppName
```

---

### Day 4: Integration Testing

#### Test 1: Manual Queue Message

Send a test message to the queue:

```powershell
# Get storage account name
$outputs = Get-Content .\infra\scripts\latest-deployment.json | ConvertFrom-Json
$storageAccount = $outputs.storageAccountName.value
$queueName = $outputs.storageQueueName.value

# Get storage account key
$storageKey = az storage account keys list `
  --account-name $storageAccount `
  --resource-group "rg-ai-hedge-fund-prod" `
  --query "[0].value" -o tsv

# Send test message
az storage message put `
  --queue-name $queueName `
  --account-name $storageAccount `
  --account-key $storageKey `
  --content '{"ticker":"AAPL","user_id":"test-user","strategy_id":"default"}'
```

**Expected Behavior:**
1. Queue Worker Job should start automatically (check in Azure Portal)
2. Job processes the message and runs analysis
3. Results stored in Cosmos DB
4. Check logs in Application Insights

---

#### Test 2: Check Container Apps Job Execution

```powershell
# Get job name
$jobName = $outputs.queueWorkerJobName.value

# Check job executions
az containerapp job execution list `
  --name $jobName `
  --resource-group "rg-ai-hedge-fund-prod" `
  --output table

# View logs from latest execution
$latestExecution = az containerapp job execution list `
  --name $jobName `
  --resource-group "rg-ai-hedge-fund-prod" `
  --query "[0].name" -o tsv

az containerapp job logs show `
  --name $jobName `
  --resource-group "rg-ai-hedge-fund-prod" `
  --execution $latestExecution
```

---

#### Test 3: Verify Cosmos DB Data

```powershell
# Check if data was written to Cosmos DB
$cosmosEndpoint = $outputs.cosmosEndpoint.value
$databaseName = $outputs.cosmosDatabaseName.value

# View documents in portfolios container
az cosmosdb sql container query `
  --account-name "cosmos-cryptoanalysis-prod-cqpvo3njb4joq" `
  --resource-group "rg-common-infra" `
  --database-name $databaseName `
  --name "portfolios" `
  --query "SELECT * FROM c" `
  --output table
```

---

#### Test 4: Check Alpaca Paper Trading Orders

1. Go to https://alpaca.markets/
2. Login to your account
3. Navigate to **Paper Trading → Orders**
4. Verify orders appear (if analysis resulted in trades)

---

### Day 5: Monitoring & Optimization

#### Setup Application Insights Alerts

1. Go to Azure Portal → Application Insights → `aihedgefund-appi`
2. Navigate to **Alerts** → **Create alert rule**

**Recommended Alerts:**
- **Container App Failures**: When app throws exceptions
- **Queue Depth High**: When queue has >10 messages for >5 minutes
- **Function App Errors**: When Function App fails to execute

---

#### Setup Cost Alerts

```powershell
# Check current costs
az consumption usage list `
  --start-date 2025-11-01 `
  --end-date 2025-11-19 `
  --query "[?contains(instanceName, 'aihedgefund')]" `
  --output table
```

**Cost Management:**
1. Go to Azure Portal → Cost Management + Billing
2. Create budget for resource group
3. Set alert at 80% of budget

---

#### Monitor Logs in Application Insights

```powershell
# Query recent logs
az monitor app-insights query `
  --app $outputs.appInsightsName.value `
  --resource-group "rg-ai-hedge-fund-prod" `
  --analytics-query "traces | where timestamp > ago(1h) | order by timestamp desc | take 50" `
  --output table
```

**Or use Azure Portal:**
1. Go to Application Insights → Logs
2. Run query:
   ```kusto
   traces
   | where timestamp > ago(1h)
   | where severityLevel >= 2  // Warnings and above
   | order by timestamp desc
   ```

---

## Troubleshooting

### Common Issues

#### Issue 1: "ACR SKU Basic is not supported"
**Solution:** Use the `deploy-with-common-infra.ps1` script which uses your existing ACR.

---

#### Issue 2: Container Apps Job Not Starting
**Check:**
```powershell
# Verify queue has messages
az storage message peek `
  --queue-name $queueName `
  --account-name $storageAccount `
  --account-key $storageKey

# Check job configuration
az containerapp job show `
  --name $jobName `
  --resource-group "rg-ai-hedge-fund-prod"
```

**Common Causes:**
- Queue connection string incorrect
- Docker image not found in ACR
- Insufficient permissions

---

#### Issue 3: Cosmos DB Query Errors
**Check Partition Key:**
All containers should use `/partition_key` (not `/id`).

```powershell
# Verify partition key
az cosmosdb sql container show `
  --account-name "cosmos-cryptoanalysis-prod-cqpvo3njb4joq" `
  --resource-group "rg-common-infra" `
  --database-name "ai-hedge-fund" `
  --name "portfolios" `
  --query "resource.partitionKey"
```

**Expected Output:** `{ paths: ["/partition_key"] }`

---

#### Issue 4: GitHub Workflow Fails
**Check:**
1. `AZURE_CREDENTIALS` secret is correct
2. Service principal has Contributor role
3. ACR admin user is enabled
4. `DEPLOYMENT_CONFIG` is valid JSON

---

## Cost Optimization

### Expected Monthly Costs

**Minimal Usage (Development/Testing):**
- Container Apps (scale to 0): ~$5/month
- Function App (Consumption): ~$0-5/month
- Storage Account: ~$1/month
- Log Analytics: ~$2/month
- Application Insights: ~$2/month
- Cosmos DB (Serverless, free tier): $0/month
- **Total: ~$10-15/month**

**Moderate Usage (Production):**
- Container Apps (occasional scaling): ~$20-30/month
- Function App (frequent triggers): ~$10/month
- Storage + Logs: ~$10/month
- Cosmos DB (beyond free tier): ~$20/month
- **Total: ~$60-70/month**

### Cost Reduction Tips

1. **Reduce Function App Frequency:**
   - Edit `infra/monitoring/function_app.py`
   - Change schedule from `0 */5 * * * *` (every 5 min) to `0 */15 * * * *` (every 15 min)

2. **Reduce Number of AI Analysts:**
   - Edit `src/config.py`
   - Reduce from 18 agents to 5-8 most relevant ones
   - This reduces LLM API costs significantly

3. **Use Cheaper LLM Models:**
   - Switch from GPT-4 to GPT-3.5-turbo
   - Use Groq (free tier) for some agents
   - Mix of models based on criticality

4. **Adjust Cooldown Period:**
   - Increase cooldown from 1 hour to 4-6 hours
   - Reduces frequency of analysis runs

---

## Next Steps After Deployment

1. **Monitor First Week:**
   - Check Application Insights daily
   - Verify Alpaca paper trades
   - Review Cosmos DB data

2. **Tune Parameters:**
   - Adjust confidence thresholds
   - Refine AI prompts
   - Optimize portfolio allocation

3. **Setup Dashboards:**
   - Create Azure Dashboard for monitoring
   - Setup email alerts for critical events

4. **Document Results:**
   - Track performance in `docs/backtesting_results.md`
   - Compare vs buy-and-hold benchmark
   - Document lessons learned

---

## Additional Resources

- **Bicep Templates:** `infra/bicep/main.bicep`
- **PowerShell Scripts:** `infra/scripts/`
- **Function App Code:** `infra/monitoring/`
- **Application Code:** `src/`
- **GitHub Workflow:** `.github/workflows/publish-app.yml`

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review Azure logs in Application Insights
3. Check GitHub workflow logs
4. Open an issue in the repository

---

**Deployment Guide Version:** 1.0
**Last Updated:** 2025-11-19
