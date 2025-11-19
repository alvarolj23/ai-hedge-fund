# AI Hedge Fund - Quick Start Guide

Fast-track deployment for experienced Azure users.

## Prerequisites

- Azure CLI installed and authenticated
- PowerShell 5.1+
- Existing Cosmos DB and ACR in common infrastructure
- API keys ready (Alpaca, FinancialDatasets.ai, OpenAI)

---

## 5-Minute Deployment

### 1. Clean Up (If Needed)

```powershell
cd C:\path\to\ai-hedge-fund

.\infra\scripts\cleanup-partial-deployment.ps1 `
  -SubscriptionId "YOUR_SUBSCRIPTION_ID" `
  -ResourceGroupName "rg-ai-hedge-fund-prod"
```

Wait 5 minutes for deletion to complete.

---

### 2. Deploy Infrastructure

```powershell
.\infra\scripts\deploy-with-common-infra.ps1 `
  -SubscriptionId "YOUR_SUBSCRIPTION_ID" `
  -ResourceGroupName "rg-ai-hedge-fund-prod" `
  -CommonInfraResourceGroup "rg-common-infra" `
  -CommonCosmosAccountName "YOUR_COSMOS_ACCOUNT" `
  -CommonAcrName "YOUR_ACR_NAME" `
  -NamePrefix "aihedgefund" `
  -Location "westeurope" `
  -UsePlaceholderImages
```

**Duration:** 8-12 minutes

---

### 3. Verify Deployment

```powershell
.\infra\scripts\verify-deployment.ps1 `
  -SubscriptionId "YOUR_SUBSCRIPTION_ID" `
  -ResourceGroupName "rg-ai-hedge-fund-prod" `
  -CommonInfraResourceGroup "rg-common-infra" `
  -CommonCosmosAccountName "YOUR_COSMOS_ACCOUNT" `
  -CommonAcrName "YOUR_ACR_NAME"
```

All checks should pass ✓

---

### 4. Setup GitHub CI/CD

**Create Variables:**
- `SUBSCRIPTION_ID` = your subscription ID
- `RESOURCE_GROUP` = `rg-ai-hedge-fund-prod`

**Create Secrets:**
1. `AZURE_CREDENTIALS` = Service principal JSON
   ```bash
   az ad sp create-for-rbac --name "ai-hedge-fund-github" \
     --role contributor \
     --scopes /subscriptions/YOUR_SUB_ID/resourceGroups/rg-ai-hedge-fund-prod \
     --sdk-auth
   ```

2. `DEPLOYMENT_CONFIG` = Your API keys JSON:
   ```json
   {
     "apiAppSettings": {
       "OPENAI_API_KEY": "sk-...",
       "FINANCIAL_DATASETS_API_KEY": "..."
     },
     "workerAppSettings": {
       "OPENAI_API_KEY": "sk-...",
       "FINANCIAL_DATASETS_API_KEY": "...",
       "ALPACA_API_KEY": "...",
       "ALPACA_SECRET_KEY": "...",
       "ALPACA_BASE_URL": "https://paper-api.alpaca.markets",
       "TRADE_MODE": "paper"
     },
     "functionAppSettings": {
       "TICKERS": "AAPL,GOOGL,MSFT,NVDA,TSLA"
     }
   }
   ```

---

### 5. Deploy Application

**GitHub UI:**
1. Go to **Actions** tab
2. Select **Publish application**
3. Click **Run workflow**

**Duration:** 10-15 minutes

---

### 6. Deploy Function App

```powershell
.\infra\scripts\deploy-function.ps1 `
  -SubscriptionId "YOUR_SUBSCRIPTION_ID" `
  -ResourceGroupName "rg-ai-hedge-fund-prod"
```

**Duration:** 2-3 minutes

---

### 7. Test End-to-End

```powershell
# Get deployment outputs
$outputs = Get-Content .\infra\scripts\latest-deployment.json | ConvertFrom-Json

# Send test message to queue
$storageAccount = $outputs.storageAccountName.value
$queueName = $outputs.storageQueueName.value
$storageKey = az storage account keys list `
  --account-name $storageAccount `
  --resource-group "rg-ai-hedge-fund-prod" `
  --query "[0].value" -o tsv

az storage message put `
  --queue-name $queueName `
  --account-name $storageAccount `
  --account-key $storageKey `
  --content '{"ticker":"AAPL","user_id":"test","strategy_id":"default"}'

# Check job execution
$jobName = $outputs.queueWorkerJobName.value
az containerapp job execution list `
  --name $jobName `
  --resource-group "rg-ai-hedge-fund-prod" `
  --output table
```

---

## Done!

Your AI Hedge Fund is now running on Azure!

**Monitor:**
- Azure Portal → Application Insights → Logs
- Alpaca Dashboard → Paper Trading Orders
- Cosmos DB Data Explorer → View results

**Next Steps:**
- See [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md) for detailed monitoring
- See [Cost Optimization](DEPLOYMENT-GUIDE.md#cost-optimization) to reduce costs
- See [Troubleshooting](DEPLOYMENT-GUIDE.md#troubleshooting) if issues arise

---

## Your Infrastructure At-a-Glance

```
rg-ai-hedge-fund-prod (NEW)
├── Storage Account
│   ├── Queue: analysis-requests
│   └── Queue: analysis-deadletter
├── Container Apps Environment
│   ├── API Container App (web UI)
│   └── Queue Worker Job (analysis)
├── Function App (market monitor)
├── Log Analytics + App Insights
└── Function App Plan

rg-common-infra (SHARED)
├── Cosmos DB
│   └── Database: ai-hedge-fund
│       ├── portfolios
│       ├── analyst-signals
│       ├── decisions
│       ├── portfolioSnapshots
│       ├── hedgeFundResults
│       ├── hedgeFundStatus
│       ├── broker-orders
│       └── monitor-cooldowns
└── Container Registry (ACR)
    ├── ai-hedge-fund-api:latest
    └── ai-hedge-fund-worker:latest
```

---

**Questions?** See the full [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md)
