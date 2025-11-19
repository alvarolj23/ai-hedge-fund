# AI Hedge Fund - Infrastructure

This folder contains all Azure infrastructure as code (IaC) and deployment scripts for the AI Hedge Fund application.

## Quick Navigation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute deployment guide
- **[DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md)** - Comprehensive deployment guide with troubleshooting
- **[bicep/](bicep/)** - Bicep infrastructure templates
- **[scripts/](scripts/)** - PowerShell deployment scripts
- **[monitoring/](monitoring/)** - Azure Function App code for market monitoring

---

## Architecture Overview

The application runs on Azure with an event-driven architecture:

1. **Function App** - Timer trigger (every 5 minutes) checks market conditions
2. **Storage Queue** - Receives analysis requests
3. **Container Apps Job** - Event-driven worker that runs AI hedge fund analysis
4. **Cosmos DB** - Stores portfolios, signals, decisions, and results
5. **Container Registry** - Hosts Docker images
6. **Application Insights** - Monitoring and logging

---

## Folder Structure

```
infra/
├── QUICKSTART.md                    # Fast-track deployment guide
├── DEPLOYMENT-GUIDE.md              # Comprehensive deployment documentation
├── README.md                        # This file
│
├── bicep/                          # Infrastructure as Code
│   ├── main.bicep                  # Main Bicep template
│   └── modules/
│       └── cosmos-containers.bicep # Cosmos DB containers (8 containers)
│
├── scripts/                        # Deployment automation
│   ├── deploy-with-common-infra.ps1      # Master deployment script (USE THIS!)
│   ├── setup-cosmos-db.ps1               # Creates Cosmos DB database & containers
│   ├── cleanup-partial-deployment.ps1    # Removes failed/partial deployments
│   ├── verify-deployment.ps1             # Verifies infrastructure is correct
│   ├── deploy-infrastructure.ps1         # Low-level infrastructure deployment
│   ├── publish-app.ps1                   # Builds & deploys Docker images
│   ├── deploy-function.ps1               # Deploys Function App code
│   └── deployment-settings.example.json  # Template for API keys
│
└── monitoring/                     # Function App code
    ├── function_app.py             # Market monitor timer trigger
    ├── api_client.py               # Queue message sender
    ├── models.py                   # Data models
    ├── requirements.txt            # Python dependencies
    └── host.json                   # Function App configuration
```

---

## Deployment Options

### Option 1: Using Common Infrastructure (Recommended)

If you have existing Cosmos DB and Container Registry in a common resource group:

```powershell
.\infra\scripts\deploy-with-common-infra.ps1 `
  -SubscriptionId "YOUR_SUBSCRIPTION_ID" `
  -ResourceGroupName "rg-ai-hedge-fund-prod" `
  -CommonInfraResourceGroup "rg-common-infra" `
  -CommonCosmosAccountName "YOUR_COSMOS_ACCOUNT" `
  -CommonAcrName "YOUR_ACR_NAME" `
  -UsePlaceholderImages
```

See [QUICKSTART.md](QUICKSTART.md) for complete instructions.

---

### Option 2: Standalone Deployment

If you want to create all new resources:

```powershell
.\infra\scripts\deploy-infrastructure.ps1 `
  -SubscriptionId "YOUR_SUBSCRIPTION_ID" `
  -ResourceGroupName "rg-ai-hedge-fund-prod" `
  -NamePrefix "aihedgefund" `
  -Location "westeurope" `
  -AcrSku "Standard" `
  -UsePlaceholderImages
```

**Note:** Use `Standard` or `Premium` ACR SKU (not `Basic`) as it's not supported in all regions.

---

## Key Features

### Infrastructure Highlights

- **Serverless Cosmos DB** - Free tier eligible, auto-scales
- **Container Apps Jobs** - Event-driven, scales 0-10 based on queue depth
- **Function App** - Consumption plan, runs every 5 minutes during market hours
- **Zero-cost when idle** - All compute scales to zero when not in use

### Fixed Bugs (Version 1.1)

✅ **Partition Key Fixed** - All Cosmos containers now use `/partition_key` (was `/id`)
✅ **ACR SKU Issue Resolved** - Script supports reusing existing ACR
✅ **Common Infrastructure Support** - Can now share Cosmos DB and ACR across projects

---

## Cosmos DB Schema

The application uses 8 containers in Cosmos DB:

| Container | Purpose | Partition Key |
|-----------|---------|---------------|
| `portfolios` | Current portfolio positions | `/partition_key` |
| `analyst-signals` | AI analyst recommendations | `/partition_key` |
| `decisions` | Trading decisions & rationale | `/partition_key` |
| `portfolioSnapshots` | Historical portfolio states | `/partition_key` |
| `hedgeFundResults` | Execution results | `/partition_key` |
| `hedgeFundStatus` | Run status & metadata | `/partition_key` |
| `broker-orders` | Broker order history | `/partition_key` |
| `monitor-cooldowns` | Market monitor cooldown state | `/partition_key` |

**Partition Key Format:** `{user_id}::{strategy_id}`

---

## Required Environment Variables

The application requires these environment variables (configured automatically during deployment):

### Cosmos DB
- `COSMOS_ENDPOINT` - Cosmos DB endpoint URL
- `COSMOS_KEY` - Cosmos DB access key
- `COSMOS_DATABASE` - Database name (default: `ai-hedge-fund`)
- `COSMOS_PORTFOLIOS_CONTAINER` - Portfolios container name
- `COSMOS_ANALYST_SIGNALS_CONTAINER` - Analyst signals container
- `COSMOS_DECISIONS_CONTAINER` - Decisions container
- (+ 5 more container names)

### Storage Queue
- `QUEUE_ACCOUNT` - Storage account name
- `QUEUE_SAS` - Storage account key
- `QUEUE_NAME` - Queue name (default: `analysis-requests`)
- `QUEUE_DEAD_LETTER_NAME` - Dead letter queue name

### API Keys (Required - Add via DEPLOYMENT_CONFIG secret)
- `OPENAI_API_KEY` - OpenAI API key
- `FINANCIAL_DATASETS_API_KEY` - FinancialDatasets.ai API key
- `ALPACA_API_KEY` - Alpaca API key (paper trading)
- `ALPACA_SECRET_KEY` - Alpaca secret key
- `ALPACA_BASE_URL` - Alpaca base URL (`https://paper-api.alpaca.markets`)

---

## Monitoring

### Application Insights Queries

**Recent Logs:**
```kusto
traces
| where timestamp > ago(1h)
| order by timestamp desc
| take 100
```

**Errors Only:**
```kusto
traces
| where timestamp > ago(24h)
| where severityLevel >= 2
| order by timestamp desc
```

**Queue Processing Time:**
```kusto
dependencies
| where type == "Azure Queue"
| summarize avg(duration) by bin(timestamp, 5m)
```

---

## Cost Estimates

### Minimal Usage (Dev/Test)
- Container Apps (scale to 0): ~$5/month
- Function App (Consumption): ~$0-5/month
- Storage: ~$1/month
- Monitoring: ~$4/month
- Cosmos DB (Free tier): $0/month
- **Total: ~$10-15/month**

### Production Usage
- Container Apps: ~$20-30/month
- Function App: ~$10/month
- Storage + Logs: ~$10/month
- Cosmos DB: ~$20/month
- **Total: ~$60-70/month**

*Plus LLM API costs (OpenAI, etc.)*

See [Cost Optimization](DEPLOYMENT-GUIDE.md#cost-optimization) for tips to reduce costs.

---

## Troubleshooting

### Common Issues

1. **"ACR SKU Basic is not supported"**
   - Solution: Use `deploy-with-common-infra.ps1` with existing ACR

2. **Container Apps Job not starting**
   - Check queue connection string
   - Verify Docker images exist in ACR
   - Check logs in Application Insights

3. **Cosmos DB query errors**
   - Verify partition key is `/partition_key` (not `/id`)
   - Check container names match environment variables

4. **Function App not triggering**
   - Verify timer trigger schedule
   - Check Function App logs
   - Ensure all environment variables are set

See [DEPLOYMENT-GUIDE.md#troubleshooting](DEPLOYMENT-GUIDE.md#troubleshooting) for detailed troubleshooting.

---

## Next Steps

1. **Deploy Infrastructure** - Follow [QUICKSTART.md](QUICKSTART.md)
2. **Setup GitHub CI/CD** - Configure secrets for automated builds
3. **Deploy Application** - Build and push Docker images
4. **Monitor & Optimize** - Track performance and costs

---

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Fast 5-minute deployment
- **[DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md)** - Complete step-by-step guide
- **[monitoring/README.md](monitoring/README.md)** - Function App documentation
- **[scripts/deployment-settings.example.json](scripts/deployment-settings.example.json)** - API keys template

---

**Infrastructure Version:** 1.1
**Last Updated:** 2025-11-19
**Key Changes:** Fixed partition key bug, added common infrastructure support
