# AI Hedge Fund - System Status & Architecture

## 🏗️ Architecture Overview

The AI Hedge Fund is a multi-agent trading system that monitors markets, performs AI-driven analysis, and executes trades. It consists of four main phases:

### 1. **Market Monitoring Phase** ✅ WORKING

**Component:** Azure Function (`infra/monitoring/function_app.py`)

**Trigger:** Timer - Every 5 minutes during market hours (9:30 AM - 4:00 PM ET, Mon-Fri)

**Process:**
1. Fetches price history for watchlist tickers (default: AAPL, MSFT, NVDA)
2. Evaluates two types of signals:
   - **Price Breakout:** >2% price change from previous close
   - **Volume Spike:** >1.5x average volume (10-day lookback)
3. Checks cooldown period (30 minutes default) via Cosmos DB
4. Enqueues analysis request to Azure Storage Queue

**Environment Variables:**
- `MARKET_MONITOR_WATCHLIST` - Comma-separated ticker symbols
- `MARKET_MONITOR_PERCENT_CHANGE_THRESHOLD` - Default: 0.02 (2%)
- `MARKET_MONITOR_VOLUME_SPIKE_MULTIPLIER` - Default: 1.5
- `MARKET_MONITOR_COOLDOWN_SECONDS` - Default: 1800 (30 min)

**Minimal Queue Message Format (manual tests, CLI, etc.):**
```json
{
  "ticker": "NVDA",
  "lookback_days": 30,
  "overrides": {
    "show_reasoning": true
  }
}
```

**Enriched Queue Message Format (produced by Azure Function):**
```json
{
  "tickers": ["AAPL"],
  "analysis_window": {
    "start": "2025-10-02T14:33:00+00:00",
    "end": "2025-10-02T16:33:00+00:00"
  },
  "correlation_hints": {
    "related_watchlist": ["MSFT", "NVDA"],
    "basis": ["price_breakout"]
  },
  "signals": ["price_breakout", "volume_spike"],
  "market_snapshot": {
    "percent_change": 0.0234,
    "volume_ratio": 1.78,
    "latest_close": 150.45,
    "previous_close": 147.02,
    "latest_volume": 89123456,
    "average_volume": 50000000
  },
  "triggered_at": "2025-10-02T16:33:00+00:00"
}
```

---

### 2. **Analysis Phase** ⚠️ PARTIALLY WORKING

**Component:** Container App Job (`src/jobs/queue_worker.py`)

**Trigger:** Azure Storage Queue polling

**Process:**
1. ✅ Polls `analysis-requests` queue for new messages
2. ✅ Deletes message immediately (ensures single execution)
3. ✅ Validates message payload structure
4. ✅ Fetches latest portfolio snapshot from Cosmos DB
5. ✅ Calls `run_hedge_fund()` to orchestrate multi-agent analysis
6. ✅ Saves results to Cosmos DB (`hedgeFundResults` container)
7. ✅ Publishes status to Cosmos DB (`hedgeFundStatus` container)
8. ❌ **NOT YET:** Does not trigger Alpaca trading execution

**Current Issue (FIXED):**
- ~~Message parsing was failing due to double base64 encoding~~
- Fixed in `test-queue.ps1` - now sends plain JSON (Azure handles encoding)

**Message Validation:**
The queue worker validates that messages contain:
- `tickers` (array of strings)
- `analysis_window` with `start` and `end` dates
- Optional `overrides` object for configuration

---

### 3. **Multi-Agent Decision Engine** 🤖 CONFIGURED BUT NOT TESTED

**Component:** `src/main.py` - `run_hedge_fund()`

**Architecture:** LangGraph state machine with sequential analyst nodes

**Available Analysts (18 total):**

| Analyst | Strategy Focus | Module |
|---------|---------------|--------|
| Warren Buffett | Value investing, quality companies | `agents/warren_buffett.py` |
| Michael Burry | Contrarian analysis, deep value | `agents/michael_burry.py` |
| Peter Lynch | Growth at reasonable price (GARP) | `agents/peter_lynch.py` |
| Charlie Munger | Quality businesses, moats | `agents/charlie_munger.py` |
| Bill Ackman | Activist investing, catalysts | `agents/bill_ackman.py` |
| Cathie Wood | Disruptive innovation, ARK-style | `agents/cathie_wood.py` |
| Stanley Druckenmiller | Macro trends, reflexivity | `agents/stanley_druckenmiller.py` |
| Mohnish Pabrai | Cloning ideas, low-risk high-reward | `agents/mohnish_pabrai.py` |
| Phil Fisher | Scuttlebutt research, growth | `agents/phil_fisher.py` |
| Rakesh Jhunjhunwala | Indian markets specialist | `agents/rakesh_jhunjhunwala.py` |
| Aswath Damodaran | Valuation expert, DCF modeling | `agents/aswath_damodaran.py` |
| Ben Graham | Classic value, margin of safety | `agents/ben_graham.py` |
| Fundamentals Agent | Financial statement analysis | `agents/fundamentals.py` |
| Technical Agent | Chart patterns, indicators | `agents/technicals.py` |
| Sentiment Agent | News, social media sentiment | `agents/sentiment.py` |
| Valuation Agent | Multiple valuation methods | `agents/valuation.py` |
| Risk Manager | Portfolio risk assessment | `agents/risk_manager.py` |
| Portfolio Manager | Final trading decisions | `agents/portfolio_manager.py` |

**Workflow:**
```
Start → [Selected Analysts] → Risk Manager → Portfolio Manager → END
```

**Output Format:**
```json
{
  "NVDA": {
    "action": "buy",
    "quantity": 100,
    "confidence": 85,
    "reasoning": "Strong growth, technical breakout..."
  }
}
```

**Analyst Signals:**
Each analyst contributes a signal with:
- `signal` (buy/sell/hold)
- `confidence` (0-100)
- `reasoning` (text explanation)

---

### 4. **Trading Execution Phase** ❌ NOT INTEGRATED IN QUEUE WORKER

**Component:** `src/brokers/execution.py` - `dispatch_paper_orders()`

**Broker:** Alpaca Paper Trading API

**Status:** 
- ✅ Function exists and works in CLI mode (`python -m src.main --trade-mode paper`)
- ❌ **NOT called by queue_worker.py**
- ❌ Queue worker only saves results to Cosmos DB

**What's Missing:**
The queue worker needs to be enhanced to:
1. Accept `trade_mode` parameter in queue message
2. Call `dispatch_paper_orders()` after analysis completes
3. Respect confidence thresholds
4. Log trade executions to Cosmos DB

**Required Enhancement:**
```python
# In queue_worker.py _process_message():
if overrides.get("trade_mode") == "paper":
    from src.brokers import dispatch_paper_orders
    
    broker_orders = dispatch_paper_orders(
        decisions=hedge_result.get("decisions"),
        analyst_signals=hedge_result.get("analyst_signals"),
        state_data={"portfolio": portfolio_data},
        confidence_threshold=overrides.get("confidence_threshold", 70),
        dry_run=overrides.get("dry_run", False),
    )
    
    result_record["broker_orders"] = broker_orders
```

---

## 📊 Data Flow & Persistence

### Cosmos DB Containers

| Container | Purpose | Partition Key | Document Structure |
|-----------|---------|---------------|-------------------|
| `portfolioSnapshots` | Current portfolio state | `/id` | Portfolio positions, cash, margin |
| `hedgeFundResults` | Full analysis results | `/messageId` | Decisions, analyst signals, metadata |
| `hedgeFundStatus` | Completion notifications | `/messageId` | Status, summary, timestamp |
| `cooldownState` | Trigger cooldown tracking | `/ticker` | Last trigger time, reasons |

### Azure Storage Queue

| Queue | Purpose | Message Retention |
|-------|---------|-------------------|
| `analysis-requests` | Analysis job triggers | 7 days |
| `analysis-deadletter` | Failed/poison messages | 7 days |

---

## 🧪 Testing Guide

### Manual Queue Testing

Use `infra/test-queue.ps1` to manually trigger analysis:

```powershell
# Single ticker
.\test-queue.ps1 -Tickers "NVDA" -LookbackDays 30

# Multiple tickers
.\test-queue.ps1 -Tickers "AAPL,MSFT,GOOGL" -LookbackDays 60

# Custom storage account
.\test-queue.ps1 `
    -Tickers "TSLA" `
    -StorageAccountName "your-storage-account" `
    -ResourceGroupName "your-rg" `
    -QueueName "analysis-requests"
```

**Message Format Sent:**
```json
{
  "ticker": "NVDA",
  "lookback_days": 30,
  "overrides": {
    "show_reasoning": true
  },
  "triggered_at": "2025-10-02T16:44:59+00:00",
  "source": "manual_test"
}
```

### Local Queue Worker Testing

For local development and testing, use the dedicated test runner:

```powershell
# Start local queue worker (with certificate setup)
python tests\test_queue_worker.py

# In another terminal, send test messages
.\infra\test-queue.ps1 -Tickers "NVDA"
```

**Benefits:**
- Test queue processing without deploying to Azure
- Full certificate setup for corporate environments
- Continuous polling with detailed logging
- Easy debugging of message processing

### Monitoring Queue Worker Logs

View Container App Job logs in Azure Portal or CLI:

```bash
az containerapp job execution logs show \
  --name <job-name> \
  --resource-group rg-ai-hedge-fund \
  --execution-name <execution-id>
```

**Expected Success Logs:**
```
INFO [__main__] Processing message <message-id>
INFO [__main__] Message <message-id> processed successfully
```

**Common Errors:**
- `PoisonMessageError: Queue message is missing a list of 'tickers'` - Message format invalid
- `RuntimeError: No portfolio snapshot available in Cosmos DB` - Need to seed portfolio data

---

## 🔧 Configuration Summary

### Queue Worker Environment Variables

**Required:**
- `QUEUE_ACCOUNT` - Azure Storage account name
- `QUEUE_NAME` - Queue to poll (default: `analysis-requests`)
- `QUEUE_SAS` - SAS token for queue access
- `COSMOS_ENDPOINT` - Cosmos DB endpoint URL
- `COSMOS_KEY` - Cosmos DB access key
- `COSMOS_DATABASE` - Database name (default: `ai-hedge-fund`)

**Optional:**
- `QUEUE_VISIBILITY_TIMEOUT` - Default: 300 seconds
- `QUEUE_MAX_ATTEMPTS` - Retry count (default: 5)
- `QUEUE_BACKOFF_SECONDS` - Initial backoff (default: 2)
- `COSMOS_SNAPSHOT_CONTAINER` - Default: `portfolioSnapshots`
- `COSMOS_RESULTS_CONTAINER` - Default: `hedgeFundResults`
- `COSMOS_STATUS_CONTAINER` - Default: `hedgeFundStatus`

### Function App Environment Variables

**Required:**
- `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DATABASE`, `COSMOS_CONTAINER`
- `MARKET_MONITOR_QUEUE_CONNECTION_STRING` or `AzureWebJobsStorage`
- `MARKET_MONITOR_QUEUE_NAME` or `ALERT_QUEUE_NAME`

**Optional:**
- `MARKET_MONITOR_WATCHLIST` - Tickers to monitor
- `MARKET_MONITOR_PERCENT_CHANGE_THRESHOLD` - Default: 0.02
- `MARKET_MONITOR_VOLUME_SPIKE_MULTIPLIER` - Default: 1.5
- `MARKET_MONITOR_VOLUME_LOOKBACK` - Days (default: 10)
- `MARKET_MONITOR_COOLDOWN_SECONDS` - Default: 1800

---

## 🐛 Known Issues & Fixes

### ✅ FIXED: Double Base64 Encoding

**Problem:** `test-queue.ps1` was manually base64-encoding messages, but Azure Storage Queue with `TextBase64DecodePolicy` automatically handles encoding/decoding.

**Solution:** Send plain JSON from PowerShell - Azure handles encoding automatically.

### ⚠️ PENDING: Trading Execution Not Integrated

**Problem:** Queue worker doesn't call Alpaca broker APIs.

**Impact:** Analysis completes but no trades are placed.

**Next Steps:**
1. Add `trade_mode` to queue message schema
2. Import and call `dispatch_paper_orders()` in queue worker
3. Save broker order results to Cosmos DB
4. Add error handling for broker API failures

### ⚠️ PENDING: Portfolio Snapshot Initialization

**Problem:** Queue worker expects a portfolio snapshot in Cosmos DB but none exists initially.

**Solution:** Create initialization script:
```python
from src.data.cosmos_repository import CosmosRepository

repo = CosmosRepository.from_environment()
initial_portfolio = {
    "id": "default-portfolio",
    "portfolio": {
        "cash": 100000.0,
        "margin_requirement": 0.0,
        "margin_used": 0.0,
        "positions": {},
        "realized_gains": {}
    }
}
# Save to Cosmos DB portfolioSnapshots container
```

---

## 🚀 Deployment Architecture

```
Azure Resource Group: rg-ai-hedge-fund
├─ Azure Function App (Market Monitoring)
│  ├─ Timer Trigger: */5 * * * * (every 5 minutes)
│  ├─ Runtime: Python 3.11
│  └─ Outputs: Azure Storage Queue
│
├─ Azure Container App Job (Queue Worker)
│  ├─ Trigger: Azure Storage Queue (analysis-requests)
│  ├─ Scaling: KEDA queue-based (1 replica per message)
│  ├─ Runtime: Python 3.11 (Docker)
│  └─ Outputs: Cosmos DB
│
├─ Azure Storage Account
│  ├─ Queue: analysis-requests
│  └─ Queue: analysis-deadletter
│
├─ Azure Cosmos DB
│  ├─ Database: ai-hedge-fund
│  ├─ Container: portfolioSnapshots
│  ├─ Container: hedgeFundResults
│  ├─ Container: hedgeFundStatus
│  └─ Container: cooldownState (used by function app)
│
└─ External: Alpaca Paper Trading API
   └─ Status: Configured but not integrated in queue worker
```

---

## 📋 Next Steps & Recommendations

### High Priority
1. ✅ **Fix message encoding** - COMPLETED
2. 🔄 **Seed initial portfolio snapshot** in Cosmos DB
3. 🔄 **Test end-to-end analysis flow** with valid message
4. 🔄 **Integrate Alpaca trading** into queue worker

### Medium Priority
5. Add comprehensive error handling for LLM API failures
6. Implement retry logic for transient Cosmos DB errors
7. Add observability (Application Insights integration)
8. Create dashboard for monitoring trade decisions

### Low Priority
9. Add support for custom analyst selection via queue message
10. Implement backtesting mode for historical analysis
11. Add notification system (email/SMS on trade execution)
12. Create admin API for portfolio management

---

## 🎯 Success Criteria

**Phase 1: Analysis Pipeline** (Current Focus)
- ✅ Function app monitors market and enqueues triggers
- ✅ Queue worker processes messages without errors
- 🔄 Multi-agent analysis completes successfully
- 🔄 Results saved to Cosmos DB

**Phase 2: Trading Integration**
- 🔄 Queue worker calls Alpaca API
- 🔄 Trades execute based on confidence thresholds
- 🔄 Portfolio state updates in Cosmos DB
- 🔄 Trade confirmations logged

**Phase 3: Production Readiness**
- 🔄 Error handling and retry mechanisms robust
- 🔄 Monitoring and alerting configured
- 🔄 Cost optimization (Cosmos RU/s, Function scaling)
- 🔄 Security hardening (managed identities, key vault)

---

*Last Updated: October 2, 2025*
*Status: Analysis pipeline functional, trading integration pending*
