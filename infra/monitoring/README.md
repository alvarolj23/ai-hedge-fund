# AI Hedge Fund - Enhanced Real-Time Market Monitoring System

## 🚀 Overview

This is a **state-of-the-art multi-tier monitoring system** that detects trading signals in real-time using a hybrid approach with multiple data sources and advanced indicators.

### Key Features

✅ **Real-Time Detection** - <1 minute latency using multi-API integration
✅ **Smart Signal Detection** - 9+ indicators including VWAP, ATR, gap detection, volume velocity
✅ **Three-Tier Monitoring** - 1-min fast scan, 5-min comprehensive, 15-min validation
✅ **Market-Aware** - Automatic holiday handling, early close detection
✅ **Free Tier Friendly** - All APIs support free tiers, $0/month operation possible
✅ **Production Ready** - Cooldowns, retries, error handling, logging

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Tiered Monitoring System                         │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Fast Monitor │     │ Main Monitor │     │  Validation  │
│  (1 minute)  │────▶│  (5 minutes) │────▶│ (15 minutes) │
└──────────────┘     └──────────────┘     └──────────────┘
      │                     │                      │
      │                     │                      │
      ▼                     ▼                      ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   yfinance   │     │  Financial   │     │    Alpha     │
│   Finnhub    │     │   Datasets   │     │  Vantage     │
│  (quotes)    │     │ (5-min bars) │     │    (RSI)     │
└──────────────┘     └──────────────┘     └──────────────┘
      │                     │                      │
      │                     ▼                      │
      │              ┌──────────────┐              │
      │              │Enhanced      │              │
      └──────────────▶Signal        │◀─────────────┘
                     │Detection     │
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ Azure Queue  │
                     │ (Analysis)   │
                     └──────────────┘
```

## 🎯 What's New in This Version

### Fixed Issues

1. ✅ **CRITICAL: Real-time data issue resolved**
   - **Before:** Using daily bars (`interval=day`) - values didn't update during market hours
   - **After:** Using 5-minute intraday bars - live updates every 5 minutes

2. ✅ **Historical data mismatch fixed**
   - **Before:** Fetching 30 days (insufficient for technical indicators)
   - **After:** Fetching 180 days (126+ trading days as required)

3. ✅ **Market holiday handling added**
   - System now aware of NYSE/NASDAQ holidays
   - No failed requests on market holidays
   - Supports early close days (1:00 PM ET close)

### New Capabilities

1. **Multi-API Integration**
   - Finnhub (60 calls/min) - Real-time quotes, news
   - Polygon (free tier) - 1-min aggregates, VWAP
   - Alpha Vantage (25 calls/day) - Technical indicators
   - yfinance (unlimited) - Reliable fallback

2. **Enhanced Signal Detection**
   - Gap detection at market open
   - Volume velocity (not just volume ratio)
   - Price velocity (rate of change)
   - VWAP deviation analysis
   - Intraday breakout detection
   - Bollinger Band position
   - ATR expansion monitoring
   - Volatility regime changes

3. **Three-Tier Monitoring**
   - **1-minute:** Fast detection of rapid movements
   - **5-minute:** Comprehensive analysis with all indicators
   - **15-minute:** Validation and confirmation

## 🛠️ Setup Instructions

### 1. Install Dependencies

```bash
cd infra/monitoring
pip install -r requirements.txt
```

### 2. Get API Keys (Free Tiers)

#### Required:
- **Financial Datasets**: [financialdatasets.ai](https://financialdatasets.ai) - Historical and intraday data

#### Optional (but recommended):
- **Finnhub**: [finnhub.io](https://finnhub.io) - Free: 60 calls/min
- **Polygon**: [polygon.io](https://polygon.io) - Free tier available
- **Alpha Vantage**: [alphavantage.co](https://www.alphavantage.co) - Free: 25 calls/day
- **yfinance**: No API key needed (pip install only)

### 3. Configure Environment Variables

Create `local.settings.json` for local testing:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",

    "FINANCIAL_DATASETS_API_KEY": "your_key_here",
    "FINNHUB_API_KEY": "your_key_here",
    "ALPHA_VANTAGE_API_KEY": "your_key_here",

    "MARKET_MONITOR_WATCHLIST": "AAPL,MSFT,NVDA",
    "MARKET_MONITOR_INTERVAL": "minute",
    "MARKET_MONITOR_INTERVAL_MULTIPLIER": "5",
    "MARKET_MONITOR_LOOKBACK_DAYS": "180",

    "COSMOS_ENDPOINT": "https://your-cosmos.documents.azure.com:443/",
    "COSMOS_KEY": "your_key",
    "COSMOS_DATABASE": "market-monitor",
    "COSMOS_CONTAINER": "signal-cooldowns",

    "MARKET_MONITOR_QUEUE_CONNECTION_STRING": "your_queue_connection",
    "MARKET_MONITOR_QUEUE_NAME": "market-signals"
  }
}
```

See [ENV_VARIABLES.md](./ENV_VARIABLES.md) for complete configuration options.

### 4. Deploy to Azure

```bash
# Login to Azure
az login

# Deploy
func azure functionapp publish your-function-app
```

### 5. Configure Azure Settings

```bash
# Set environment variables in Azure
az functionapp config appsettings set \
  --name your-function-app \
  --resource-group your-rg \
  --settings \
    FINANCIAL_DATASETS_API_KEY=your_key \
    MARKET_MONITOR_WATCHLIST=AAPL,MSFT,NVDA \
    MARKET_MONITOR_INTERVAL=minute \
    MARKET_MONITOR_INTERVAL_MULTIPLIER=5
```

## 🧪 Testing

### Test Locally

```bash
# Start Functions runtime
func start
```

### Test Outside Market Hours

To test outside market hours, temporarily modify `function_app.py`:

```python
# Comment out the market hours check:
# if not _is_market_hours(now_utc):
#     logging.info("Outside market hours - skipping execution")
#     return
```

### Monitor Logs

```bash
# View real-time logs
func azure functionapp logstream your-function-app
```

## 📈 Monitoring & Observability

### Log Patterns

```bash
# Successful signal detection:
"🚨 FAST ALERT: AAPL moved 0.65% in last minute"
"AAPL: SIGNALS DETECTED - ['price_breakout', 'volume_spike'] (change: 2.15%, vol ratio: 2.1x)"

# Normal operation:
"AAPL: No signals triggered (change: -0.86%, vol ratio: 0.99x)"

# Validation:
"✓ AAPL: Strong uptrend confirmed (last 30 min)"
"⚠️ MSFT: RSI indicates overbought (78.50)"
```

## 🎛️ Tuning Signal Detection

### Reduce False Positives

```bash
# Increase thresholds
MARKET_MONITOR_PERCENT_CHANGE_THRESHOLD=0.03  # 3% instead of 2%
MARKET_MONITOR_VOLUME_SPIKE_MULTIPLIER=2.0    # 2x instead of 1.5x
MARKET_MONITOR_COOLDOWN_SECONDS=3600          # 1 hour instead of 30 min
```

### Increase Sensitivity

```bash
# Decrease thresholds
MARKET_MONITOR_PERCENT_CHANGE_THRESHOLD=0.01  # 1% instead of 2%
FAST_MONITOR_PERCENT_THRESHOLD=0.003          # 0.3% instead of 0.5%
```

## 🐛 Troubleshooting

### Problem: "No price data" errors

**Solutions:**
1. Verify `FINANCIAL_DATASETS_API_KEY` is valid
2. Check ticker symbols are correct (use uppercase)
3. Ensure `MARKET_MONITOR_LOOKBACK_DAYS=180`

### Problem: Values not updating

**Solution:**
```bash
# Ensure these are set:
MARKET_MONITOR_INTERVAL=minute
MARKET_MONITOR_INTERVAL_MULTIPLIER=5
```

### Problem: Fast monitor not working

**Solution:**
```bash
pip install yfinance>=0.2.32
```

## 📚 Module Reference

### `function_app.py`
Main Azure Functions with three timer triggers:
- `market_monitor`: Every 5 minutes, comprehensive analysis
- `fast_monitor`: Every 1 minute, rapid detection
- `validation_monitor`: Every 15 minutes, confirmation

### `signal_detection.py`
Enhanced signal detection with 9+ indicators

### `multi_api_client.py`
Multi-source data fetching with fallback

### `market_calendar.py`
Market hours and holiday handling

## 📊 Performance Characteristics

### Latency

| Component | Latency | Notes |
|-----------|---------|-------|
| Fast Monitor | <1 min | yfinance, Finnhub |
| Main Monitor | <5 min | Financial Datasets |
| Validation | <15 min | Alpha Vantage |

### API Call Volumes (3 tickers, 6.5 hr trading day)

| API | Calls/Day | Free Limit | Usage % |
|-----|-----------|------------|---------|
| Financial Datasets | ~240 | Varies | Check dashboard |
| yfinance | ~1,170 | Unlimited | 0% |
| Finnhub | ~390 | 86,400/day | <1% |
| Alpha Vantage | ~26 | 25/day | 100% |

## 🔒 Security Best Practices

1. **Never commit API keys**
   - Add `local.settings.json` to `.gitignore`
   - Use Azure Key Vault in production

2. **Use managed identities**
3. **Rotate keys regularly**
4. **Monitor access**

---

**Last Updated:** 2025-11-21
**Version:** 2.0 (Hybrid Multi-API)
