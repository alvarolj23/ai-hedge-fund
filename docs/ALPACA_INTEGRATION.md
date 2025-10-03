# Alpaca Paper Trading Integration

## Overview

The AI Hedge Fund now supports **direct integration with Alpaca Paper Trading**, eliminating the need for Cosmos DB portfolio snapshots. The system fetches real-time portfolio data from your Alpaca paper account before each analysis, ensuring decisions are based on current positions and available cash.

## Architecture Changes

### Before (Cosmos DB-first)
```
Queue Message → Cosmos DB Portfolio → AI Analysis → Cosmos DB Results
```

### After (Alpaca-first)
```
Queue Message → Alpaca Portfolio (live) → AI Analysis → Optional Cosmos DB → Alpaca Orders
```

## Benefits

✅ **Real-time data** - Portfolio positions, cash, and buying power fetched directly from Alpaca  
✅ **Single source of truth** - No sync issues between broker and database  
✅ **Simpler deployment** - Cosmos DB is now optional  
✅ **Paper trading ready** - Test strategies safely with Alpaca's paper account  
✅ **Production path** - Easy switch from paper → live trading in future  

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Alpaca Paper Trading API Credentials
APCA_API_KEY_ID=your_alpaca_key_here
APCA_API_SECRET_KEY=your_alpaca_secret_here
APCA_API_BASE_URL=https://paper-api.alpaca.markets/v2

# Queue Worker Settings
USE_ALPACA_PORTFOLIO=true          # Use Alpaca for portfolio data (default: true)
SAVE_TO_COSMOS=false               # Save results to Cosmos DB (default: false)

# Optional: Cosmos DB (if you want to log results)
COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/
COSMOS_KEY=your_cosmos_key
COSMOS_DATABASE=ai-hedge-fund
```

### Getting Alpaca Credentials

1. Sign up for a free account at [Alpaca](https://alpaca.markets/)
2. Navigate to **Paper Trading** section
3. Generate API keys (keep secret!)
4. Copy the keys to your `.env` file

## Usage

### 1. Analysis Mode (No Trading)

Default mode - analyzes tickers without executing trades:

```powershell
python .\infra\test_queue_python.py --tickers AAPL MSFT --lookback-days 30
```

**What happens:**
- Fetches current portfolio from Alpaca
- Runs multi-agent AI analysis
- Generates trading recommendations
- **Does NOT execute any trades**

### 2. Paper Trading Mode (Execute Orders)

Executes trades via Alpaca's paper trading API:

```powershell
python .\infra\test_queue_python.py `
    --tickers NVDA `
    --lookback-days 30 `
    --trade-mode paper
```

**What happens:**
- Fetches current portfolio from Alpaca
- Runs multi-agent AI analysis
- Generates trading decisions
- **Submits market orders to Alpaca paper account**
- Orders execute at real market prices (paper money)

### 3. Dry Run Mode (Simulate Orders)

Simulates orders without submitting to broker:

```powershell
python .\infra\test_queue_python.py `
    --tickers TSLA `
    --trade-mode paper `
    --dry-run
```

**What happens:**
- Fetches current portfolio from Alpaca
- Runs AI analysis
- Generates order objects
- **Simulates execution without calling Alpaca API**
- Useful for testing order logic

## Queue Message Format

### Basic Analysis (No Trading)
```json
{
  "ticker": "AAPL",
  "lookback_days": 30,
  "overrides": {
    "show_reasoning": true,
    "trade_mode": "analysis"
  },
  "triggered_at": "2025-10-03T08:00:00+00:00",
  "source": "manual_test"
}
```

### Paper Trading
```json
{
  "ticker": "NVDA",
  "lookback_days": 30,
  "overrides": {
    "show_reasoning": false,
    "trade_mode": "paper",
    "dry_run": false,
    "confidence_threshold": 70
  },
  "triggered_at": "2025-10-03T08:00:00+00:00",
  "source": "azure_function"
}
```

## Portfolio Data Structure

The Alpaca fetcher returns a standardized portfolio format:

```python
{
    "cash": 100000.0,              # Available cash
    "equity": 105000.0,            # Total account value
    "buying_power": 200000.0,      # Buying power (includes margin)
    "margin_requirement": 0.5,     # Margin requirement (50%)
    "margin_used": 0.0,            # Margin currently in use
    "positions": {
        "AAPL": {
            "long": 10,            # 10 shares long
            "short": 0,
            "long_cost_basis": 150.0,
            "short_cost_basis": 0.0,
            "short_margin_used": 0.0
        },
        "MSFT": {
            "long": 0,
            "short": 5,            # 5 shares short
            "long_cost_basis": 0.0,
            "short_cost_basis": 400.0,
            "short_margin_used": 1000.0
        }
    },
    "realized_gains": {
        "AAPL": {"long": 0.0, "short": 0.0},
        "MSFT": {"long": 0.0, "short": 0.0}
    }
}
```

## Migration from Cosmos DB

If you're currently using Cosmos DB for portfolio snapshots:

### Option 1: Full Migration (Recommended)
1. Set `USE_ALPACA_PORTFOLIO=true` in `.env`
2. Set `SAVE_TO_COSMOS=false` in `.env`
3. Manually replicate your Cosmos portfolio in Alpaca (execute trades to match positions)
4. Cosmos DB becomes optional (only for logging)

### Option 2: Hybrid Mode
1. Keep `USE_ALPACA_PORTFOLIO=false`
2. Set `SAVE_TO_COSMOS=true`
3. System uses Cosmos for portfolio, saves results to Cosmos
4. Manually execute Alpaca trades based on Cosmos results

### Option 3: Gradual Migration
1. Start with `USE_ALPACA_PORTFOLIO=true` and `SAVE_TO_COSMOS=true`
2. Compare Alpaca portfolio vs Cosmos results
3. After validation, set `SAVE_TO_COSMOS=false`

## Troubleshooting

### Error: Missing Alpaca Credentials
```
ValueError: Missing Alpaca credentials. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY
```

**Solution:** Add credentials to `.env` file (see Configuration section)

### Error: Failed to fetch portfolio from Alpaca
```
RuntimeError: Failed to fetch Alpaca portfolio: (403) Forbidden
```

**Causes:**
- Invalid API keys
- Corporate firewall blocking Alpaca API
- Certificate issues (Windows corporate environments)

**Solution:**
```python
# In tests/windows_cert_helpers.py - ensure certificate patching is enabled
from windows_cert_helpers import patch_ssl_with_windows_trust_store
patch_ssl_with_windows_trust_store()
```

### No positions showing in Alpaca
**Solution:** Manually place a test order in Alpaca's web interface first, or use the CLI:

```python
python -m src.main \
    --tickers AAPL \
    --start-date 2025-09-01 \
    --end-date 2025-10-03 \
    --trade-mode paper
```

## Testing Workflow

### Local Development
```powershell
# 1. Start queue worker locally
python tests\test_queue_worker.py

# 2. In another terminal, send test message
python .\infra\test_queue_python.py --tickers AAPL --trade-mode paper

# 3. Check Alpaca web interface for executed orders
```

### Verify Alpaca Connection
```python
# Quick test script
from src.brokers.portfolio_fetcher import AlpacaPortfolioFetcher

fetcher = AlpacaPortfolioFetcher(paper=True)
account = fetcher.get_account_info()
print(f"Account: {account['account_number']}")
print(f"Cash: ${account['cash']:.2f}")
print(f"Equity: ${account['equity']:.2f}")

portfolio = fetcher.get_portfolio_snapshot(tickers=["AAPL", "MSFT"])
print(f"Positions: {portfolio['positions']}")
```

## Next Steps

1. **Test with small positions** - Start with 1 share to verify execution
2. **Monitor paper account** - Check Alpaca dashboard for order fills
3. **Validate decisions** - Compare AI recommendations vs actual executions
4. **Scale gradually** - Increase position sizes as confidence grows
5. **Consider live trading** - After thorough paper testing (months recommended)

## Security Notes

⚠️ **Never commit API keys to git**  
⚠️ **Use paper trading for testing**  
⚠️ **Validate all orders before live trading**  
⚠️ **Monitor rate limits** - Alpaca has API call limits  
⚠️ **Test failure scenarios** - What happens if Alpaca is down?  

## Support

- **Alpaca Docs:** https://docs.alpaca.markets/
- **Paper Trading:** https://app.alpaca.markets/paper/dashboard/overview
- **API Reference:** https://docs.alpaca.markets/reference/
