# Environment Variables Configuration

## Required Variables

### Core Configuration

```bash
# Financial Datasets API (primary data source)
FINANCIAL_DATASETS_API_KEY=your_api_key_here

# Azure Storage Queue
MARKET_MONITOR_QUEUE_CONNECTION_STRING=your_connection_string
MARKET_MONITOR_QUEUE_NAME=market-signals
# Alternative env vars also supported:
# AZURE_STORAGE_QUEUE_CONNECTION_STRING
# AZURE_STORAGE_CONNECTION_STRING
# AzureWebJobsStorage

# Cosmos DB (for cooldown tracking)
COSMOS_ENDPOINT=https://your-cosmos-account.documents.azure.com:443/
COSMOS_KEY=your_cosmos_key
COSMOS_DATABASE=market-monitor
COSMOS_CONTAINER=signal-cooldowns
```

## Optional Multi-API Integration (Free Tiers)

### Real-Time Quote APIs

```bash
# Finnhub (60 calls/minute free tier)
# Sign up at: https://finnhub.io/
FINNHUB_API_KEY=your_finnhub_key

# Polygon.io (free tier available)
# Sign up at: https://polygon.io/
POLYGON_API_KEY=your_polygon_key

# Alpha Vantage (25 calls/day free tier)
# Sign up at: https://www.alphavantage.co/
ALPHA_VANTAGE_API_KEY=your_alphavantage_key

# yfinance - No API key needed (installed via pip)
```

## Monitoring Configuration

### Watchlist

```bash
# Comma-separated list of tickers to monitor
MARKET_MONITOR_WATCHLIST=AAPL,MSFT,NVDA,GOOGL,AMZN,TSLA,META

# Alternative env var names also supported:
# WATCHLIST_TICKERS
# DEFAULT_WATCHLIST
```

### Data Intervals

```bash
# Interval for 5-minute monitoring function
# Options: minute, hour, day
MARKET_MONITOR_INTERVAL=minute

# Multiplier for interval (e.g., 5 for 5-minute bars)
MARKET_MONITOR_INTERVAL_MULTIPLIER=5

# Historical data lookback for monitoring (default: 180 days)
# Must match queue worker requirements (126+ trading days)
MARKET_MONITOR_LOOKBACK_DAYS=180

# Historical data for analysis payload sent to queue
MARKET_MONITOR_ANALYSIS_LOOKBACK_DAYS=180
```

### Signal Detection Thresholds

#### 5-Minute Monitor (Comprehensive Analysis)

```bash
# Price change threshold for signal (default: 2%)
MARKET_MONITOR_PERCENT_CHANGE_THRESHOLD=0.02

# Volume spike multiplier (default: 1.5x)
MARKET_MONITOR_VOLUME_SPIKE_MULTIPLIER=1.5

# Volume lookback window in bars (default: 10)
MARKET_MONITOR_VOLUME_LOOKBACK=10

# Analysis window in minutes (default: 120)
MARKET_MONITOR_ANALYSIS_WINDOW_MINUTES=120

# Cooldown between signals for same ticker (default: 30 minutes)
MARKET_MONITOR_COOLDOWN_SECONDS=1800
```

#### 1-Minute Fast Monitor

```bash
# Fast monitor price threshold (default: 0.5%)
FAST_MONITOR_PERCENT_THRESHOLD=0.005

# Fast monitor velocity threshold (default: 0.2% per minute)
FAST_MONITOR_VELOCITY_THRESHOLD=0.002

# Fast monitor cooldown (default: 5 minutes)
FAST_MONITOR_COOLDOWN_SECONDS=300
```

### User/Strategy Identification

```bash
# User ID for queue messages (default: "market-monitor")
MARKET_MONITOR_USER_ID=market-monitor

# Strategy ID for queue messages (default: "auto-signal")
MARKET_MONITOR_STRATEGY_ID=auto-signal
```

## Recommended Configuration Tiers

### Tier 1: Basic (Financial Datasets Only)

```bash
# Minimum viable configuration
FINANCIAL_DATASETS_API_KEY=your_key
MARKET_MONITOR_WATCHLIST=AAPL,MSFT,NVDA
MARKET_MONITOR_INTERVAL=minute
MARKET_MONITOR_INTERVAL_MULTIPLIER=5
MARKET_MONITOR_LOOKBACK_DAYS=180

# Azure config
MARKET_MONITOR_QUEUE_CONNECTION_STRING=your_connection
MARKET_MONITOR_QUEUE_NAME=market-signals
COSMOS_ENDPOINT=your_endpoint
COSMOS_KEY=your_key
COSMOS_DATABASE=market-monitor
COSMOS_CONTAINER=signal-cooldowns
```

**Capabilities:**
- 5-minute intraday monitoring
- Basic signal detection
- ~5-10 minute latency

### Tier 2: Enhanced (+ yfinance)

```bash
# Add to Tier 1 config:
# (No additional API keys needed - yfinance is free)
```

**Capabilities:**
- 1-minute real-time quotes
- Faster signal detection
- ~1-2 minute latency
- No rate limits

### Tier 3: Professional (All APIs)

```bash
# Add to Tier 2 config:
FINNHUB_API_KEY=your_key
POLYGON_API_KEY=your_key
ALPHA_VANTAGE_API_KEY=your_key
```

**Capabilities:**
- Sub-minute quote updates
- Multi-source validation
- Technical indicator confirmation
- News/sentiment integration
- <1 minute latency

## API Rate Limits & Usage

| API | Free Tier | Rate Limit | Best For |
|-----|-----------|------------|----------|
| **Financial Datasets** | Varies | Moderate | Historical bars, primary data |
| **Finnhub** | Free | 60 calls/min | Real-time quotes, news |
| **Polygon** | Free tier | Limited | 1-min aggregates, VWAP |
| **Alpha Vantage** | Free | 25 calls/day | Technical indicators, validation |
| **yfinance** | Free | Unlimited | Fallback quotes, 1-min bars |

### Estimated Daily API Call Usage

**5-Minute Monitor (Running 6.5 hours/day):**
- Financial Datasets: ~78 calls/day (every 5 min × 6.5 hours)
- Per ticker: 78 calls × number of tickers

**1-Minute Fast Monitor:**
- yfinance: ~390 calls/day (every 1 min × 6.5 hours)
- Finnhub: ~390 calls/day (if enabled)
- **Total for 3 tickers:** ~1,170 calls/day (well within free tiers)

**15-Minute Validation:**
- Alpha Vantage: ~26 calls/day (every 15 min × 6.5 hours)
- **Fits within 25 calls/day limit if monitoring 1 ticker**

## Function Schedules

| Function | Schedule | Cron Expression | Purpose |
|----------|----------|-----------------|---------|
| **market_monitor** | Every 5 minutes | `0 */5 * * * *` | Comprehensive analysis with enhanced signals |
| **fast_monitor** | Every 1 minute | `0 * * * * *` | Quick detection of rapid movements |
| **validation_monitor** | Every 15 minutes | `0 */15 * * * *` | Validate signals with technical indicators |

All functions automatically:
- Only run during US market hours (9:30 AM - 4:00 PM ET)
- Skip weekends
- Skip market holidays (NYSE/NASDAQ calendar)

## Testing Configuration

For testing outside market hours, temporarily modify in code:
```python
# In function_app.py, comment out the market hours check:
# if not _is_market_hours(now_utc):
#     logging.info("Outside market hours - skipping execution")
#     return
```

## Troubleshooting

### Issue: "No price data" errors
**Solution:** Check FINANCIAL_DATASETS_API_KEY is valid and has sufficient credits

### Issue: "Insufficient intraday data"
**Solution:**
- Ensure MARKET_MONITOR_INTERVAL=minute (not "day")
- Check ticker symbol is valid
- Verify trading during market hours

### Issue: Fast monitor not working
**Solution:**
- Install yfinance: `pip install yfinance`
- Or set FINNHUB_API_KEY for alternative source

### Issue: Alpha Vantage rate limit exceeded
**Solution:**
- Reduce watchlist size for validation monitor
- Validation monitor calls Alpha Vantage for each recently triggered ticker
- Keep to 1-2 tickers or upgrade to premium

### Issue: Same values repeatedly logged
**Solution:**
- ✅ Fixed in this update! Was using daily bars, now uses intraday
- Verify MARKET_MONITOR_INTERVAL=minute

## Security Best Practices

1. **Never commit API keys to git**
   ```bash
   # Add to .gitignore
   .env
   local.settings.json
   ```

2. **Use Azure Key Vault for production**
   ```bash
   # Reference secrets in Function App settings:
   @Microsoft.KeyVault(SecretUri=https://your-vault.vault.azure.net/secrets/FinancialDatasetsApiKey/)
   ```

3. **Rotate keys regularly**
   - Set reminders to rotate API keys every 90 days

4. **Monitor API usage**
   - Check API provider dashboards weekly
   - Set up usage alerts

## Example Configuration Files

### local.settings.json (for local development)

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "FINANCIAL_DATASETS_API_KEY": "your_key_here",
    "FINNHUB_API_KEY": "your_key_here",
    "POLYGON_API_KEY": "your_key_here",
    "ALPHA_VANTAGE_API_KEY": "your_key_here",
    "MARKET_MONITOR_WATCHLIST": "AAPL,MSFT,NVDA",
    "MARKET_MONITOR_INTERVAL": "minute",
    "MARKET_MONITOR_INTERVAL_MULTIPLIER": "5",
    "MARKET_MONITOR_LOOKBACK_DAYS": "180",
    "COSMOS_ENDPOINT": "https://your-cosmos.documents.azure.com:443/",
    "COSMOS_KEY": "your_cosmos_key",
    "COSMOS_DATABASE": "market-monitor",
    "COSMOS_CONTAINER": "signal-cooldowns",
    "MARKET_MONITOR_QUEUE_CONNECTION_STRING": "your_queue_connection",
    "MARKET_MONITOR_QUEUE_NAME": "market-signals"
  }
}
```

### .env (for local development)

```bash
# Copy this template to .env and fill in your values
FINANCIAL_DATASETS_API_KEY=
FINNHUB_API_KEY=
POLYGON_API_KEY=
ALPHA_VANTAGE_API_KEY=

MARKET_MONITOR_WATCHLIST=AAPL,MSFT,NVDA
MARKET_MONITOR_INTERVAL=minute
MARKET_MONITOR_INTERVAL_MULTIPLIER=5
MARKET_MONITOR_LOOKBACK_DAYS=180

COSMOS_ENDPOINT=
COSMOS_KEY=
COSMOS_DATABASE=market-monitor
COSMOS_CONTAINER=signal-cooldowns

MARKET_MONITOR_QUEUE_CONNECTION_STRING=
MARKET_MONITOR_QUEUE_NAME=market-signals
```
