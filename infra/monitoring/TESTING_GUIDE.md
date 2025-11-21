# Testing Guide - Enhanced Signal Detection System

## 🎯 Quick Start Testing

### Step 1: Install Dependencies

```bash
cd /home/user/ai-hedge-fund/infra/monitoring
pip install -r requirements.txt
```

### Step 2: Configure Minimum Required Settings

Create `local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",

    "FINANCIAL_DATASETS_API_KEY": "your_key_here",
    "MARKET_MONITOR_WATCHLIST": "AAPL",
    "MARKET_MONITOR_INTERVAL": "minute",
    "MARKET_MONITOR_INTERVAL_MULTIPLIER": "5",
    "MARKET_MONITOR_LOOKBACK_DAYS": "180",

    "COSMOS_ENDPOINT": "your_cosmos_endpoint",
    "COSMOS_KEY": "your_cosmos_key",
    "COSMOS_DATABASE": "market-monitor",
    "COSMOS_CONTAINER": "signal-cooldowns",

    "MARKET_MONITOR_QUEUE_CONNECTION_STRING": "your_queue_connection",
    "MARKET_MONITOR_QUEUE_NAME": "market-signals"
  }
}
```

### Step 3: Test Individual Modules

#### Test Market Calendar (No API Keys Needed)

```python
# test_market_calendar.py
from market_calendar import is_market_open, is_market_holiday, is_trading_day
from datetime import datetime, date
from zoneinfo import ZoneInfo

# Test market hours
now = datetime.now(ZoneInfo("America/New_York"))
print(f"Is market open now? {is_market_open(now)}")

# Test holiday detection
thanksgiving_2025 = date(2025, 11, 27)
print(f"Is Thanksgiving a trading day? {is_trading_day(thanksgiving_2025)}")
print(f"Is Thanksgiving a holiday? {is_market_holiday(thanksgiving_2025)}")

# Test normal day
normal_day = date(2025, 11, 21)
print(f"Is Nov 21, 2025 a trading day? {is_trading_day(normal_day)}")
```

Run it:
```bash
cd infra/monitoring
python test_market_calendar.py
```

**Expected Output:**
```
Is market open now? True (if during market hours)
Is Thanksgiving a trading day? False
Is Thanksgiving a holiday? True
Is Nov 21, 2025 a trading day? True
```

#### Test Multi-API Client (Requires yfinance only)

```python
# test_multi_api.py
from multi_api_client import MultiAPIClient

client = MultiAPIClient()

# Test real-time quote (uses yfinance - no API key needed)
print("\n=== Testing Real-Time Quote ===")
quote = client.get_best_quote("AAPL")
if quote:
    print(f"Ticker: {quote.ticker}")
    print(f"Price: ${quote.price:.2f}")
    print(f"Volume: {quote.volume:,}")
    print(f"Source: {quote.source}")
    print(f"Timestamp: {quote.timestamp}")
else:
    print("Failed to get quote")

# Test intraday bars (uses yfinance - no API key needed)
print("\n=== Testing Intraday Bars ===")
bars = client.get_intraday_bars("AAPL", interval_minutes=5, limit=10)
print(f"Retrieved {len(bars)} bars")
if bars:
    latest = bars[-1]
    print(f"Latest bar - Close: ${latest.close:.2f}, Volume: {latest.volume:,}")
    print(f"Timestamp: {latest.timestamp}")
```

Run it:
```bash
python test_multi_api.py
```

**Expected Output:**
```
=== Testing Real-Time Quote ===
Ticker: AAPL
Price: $195.43
Volume: 45,234,567
Source: yfinance
Timestamp: 2025-11-21 18:45:23+00:00

=== Testing Intraday Bars ===
Retrieved 10 bars
Latest bar - Close: $195.45, Volume: 1,234,567
Timestamp: 2025-11-21 18:45:00+00:00
```

#### Test Signal Detection (Requires Price Data)

```python
# test_signal_detection.py
from signal_detection import enhanced_signal_detection
from models import Price
from datetime import datetime, timezone

# Create sample price data simulating a breakout
prices = []
base_price = 150.0

# Normal prices
for i in range(20):
    prices.append(Price(
        open=base_price,
        high=base_price + 0.5,
        low=base_price - 0.5,
        close=base_price + (i * 0.1),
        volume=1000000,
        time=datetime.now(timezone.utc).isoformat()
    ))

# Add a breakout bar
prices.append(Price(
    open=base_price + 2.0,
    high=base_price + 3.5,
    low=base_price + 1.8,
    close=base_price + 3.0,  # 2% move
    volume=3000000,  # 3x volume
    time=datetime.now(timezone.utc).isoformat()
))

# Run detection
result = enhanced_signal_detection(
    ticker="TEST",
    prices=prices,
    previous_day_close=base_price,
    percent_threshold=0.02,
    volume_multiplier=1.5
)

print(f"\n=== Signal Detection Results ===")
print(f"Triggered: {result.triggered}")
print(f"Reasons: {result.reasons}")
print(f"Confidence: {result.confidence:.2%}")
print(f"Priority: {result.priority}")
print(f"Metrics: {result.metrics}")
```

Run it:
```bash
python test_signal_detection.py
```

**Expected Output:**
```
=== Signal Detection Results ===
Triggered: True
Reasons: ['price_breakout', 'volume_spike', 'rapid_movement']
Confidence: 85%
Priority: high
Metrics: {'percent_change': 2.0, 'volume_ratio': 3.0, 'price_velocity': 0.4, ...}
```

### Step 4: Test Full Function App (During Market Hours)

#### Option A: Test Outside Market Hours (for immediate testing)

Temporarily disable market hours check in `function_app.py`:

```python
# In each monitoring function, comment out:
# if not _is_market_hours(now_utc):
#     logging.info("Outside market hours - skipping execution")
#     return
```

Then run:
```bash
func start
```

#### Option B: Test During Market Hours (9:30 AM - 4:00 PM ET)

Simply run:
```bash
func start
```

**What to Look For in Logs:**

**Fast Monitor (every 1 minute):**
```
[2025-11-21T18:45:01] Fast monitor (1-min) triggered
[2025-11-21T18:45:01] Fast monitor active - checking for immediate signals
[2025-11-21T18:45:02] Fast checking: AAPL
[2025-11-21T18:45:03] AAPL: Fast signal - Instant change 0.65%
[2025-11-21T18:45:03] 🚨 FAST ALERT: AAPL moved 0.65% in last minute
```

**Main Monitor (every 5 minutes):**
```
[2025-11-21T18:45:01] Market monitor timer triggered
[2025-11-21T18:45:01] Within market hours - proceeding with monitoring
[2025-11-21T18:45:02] Processing ticker: AAPL
[2025-11-21T18:45:03] Fetched 2340 price records for AAPL (minute/5 interval)
[2025-11-21T18:45:04] AAPL: SIGNALS DETECTED - ['price_breakout', 'volume_spike'] (change: 2.15%, vol ratio: 2.1x)
[2025-11-21T18:45:05] ✓ Enqueued analysis request for AAPL with reasons ['price_breakout', 'volume_spike']
```

**Validation Monitor (every 15 minutes):**
```
[2025-11-21T19:00:01] Validation monitor (15-min) triggered
[2025-11-21T19:00:02] Validating recent signal for AAPL (triggered 0:05:00 ago)
[2025-11-21T19:00:03] AAPL validation - RSI(14): 65.34
[2025-11-21T19:00:03] ✓ AAPL: RSI neutral (65.34)
[2025-11-21T19:00:04] ✓ AAPL: Strong uptrend confirmed (last 30 min)
```

### Step 5: Verify Real-Time Updates

Monitor the logs and verify values are changing over time:

**Before (Old System - Daily Bars):**
```
12:10:01 - AAPL: No signals (change: -0.86%, vol ratio: 0.99x)
16:40:01 - AAPL: No signals (change: -0.86%, vol ratio: 0.99x)  ❌ Same values!
```

**After (New System - 5-Minute Bars):**
```
12:10:01 - AAPL: No signals (change: -0.86%, vol ratio: 0.99x)
12:15:01 - AAPL: No signals (change: -0.42%, vol ratio: 1.12x)  ✅ Values updating!
12:20:01 - AAPL: No signals (change: +0.15%, vol ratio: 0.87x)  ✅ Real-time changes!
16:40:01 - AAPL: SIGNAL DETECTED (change: +2.34%, vol ratio: 2.3x)  ✅ Catching moves!
```

## 🧪 Advanced Testing Scenarios

### Test Gap Detection (Market Open)

Test between 9:30-9:35 AM ET when market opens to see gap detection:

```bash
# Watch logs around market open
func azure functionapp logstream your-function-app --browser
```

Look for:
```
AAPL: SIGNALS DETECTED - ['gap_up'] (change: 1.2%, gap_percent: 1.5%)
```

### Test Volume Spike Detection

During high-volume events (earnings, news), look for:
```
AAPL: SIGNALS DETECTED - ['volume_spike'] (vol ratio: 3.4x)
```

### Test Multi-API Fallback

1. Remove FINNHUB_API_KEY from settings
2. System should automatically fall back to yfinance
3. Check logs for source confirmation:
```
Fast checking: AAPL
Source: yfinance  ✅ Fallback working
```

## 📊 Performance Testing

### Measure Detection Latency

```python
# test_latency.py
import time
from multi_api_client import MultiAPIClient

client = MultiAPIClient()

# Measure quote fetch time
start = time.time()
quote = client.get_best_quote("AAPL")
latency = time.time() - start

print(f"Quote fetch latency: {latency*1000:.2f}ms")
print(f"Expected: <1000ms for yfinance")
```

### Monitor API Call Volumes

Check Azure Function App metrics:
- Invocations per hour
- Average execution time
- Error rate

Expected metrics (3 tickers):
- Fast monitor: 60 invocations/hour
- Main monitor: 12 invocations/hour
- Validation monitor: 4 invocations/hour

## 🐛 Common Issues & Solutions

### Issue: "Module not found" errors

**Solution:**
```bash
pip install -r requirements.txt
# Ensure you're in the correct directory and venv
```

### Issue: "No valid quote for AAPL"

**Possible causes:**
1. Outside market hours (use yfinance during market hours only)
2. Network issues
3. Invalid ticker

**Solution:**
```bash
# Test yfinance directly
python -c "import yfinance as yf; print(yf.Ticker('AAPL').info['regularMarketPrice'])"
```

### Issue: "Insufficient intraday data"

**Cause:** Requesting data for non-trading hours

**Solution:**
- Only test during market hours (9:30 AM - 4:00 PM ET)
- Or use historical data from last trading day

### Issue: "Cosmos DB connection failed"

**Solution:**
```bash
# Verify connection
az cosmosdb check-name-exists --name your-cosmos-account

# Check firewall rules
az cosmosdb network-rule list \
  --resource-group your-rg \
  --name your-cosmos-account
```

### Issue: Values still not updating

**Verification checklist:**
1. ✅ `MARKET_MONITOR_INTERVAL=minute` (not "day")
2. ✅ `MARKET_MONITOR_INTERVAL_MULTIPLIER=5`
3. ✅ During market hours (9:30 AM - 4:00 PM ET)
4. ✅ Not a market holiday
5. ✅ Financial Datasets API key valid

## ✅ Success Criteria

Your system is working correctly if you see:

1. **Values updating every 5 minutes** ✅
2. **Different prices at different times** ✅
3. **Fast monitor catching sub-1-minute changes** ✅
4. **Signals triggering on actual price movements** ✅
5. **No "same value" repeated throughout the day** ✅
6. **Queue messages being sent for strong signals** ✅

## 🚀 Next Steps After Testing

Once testing is successful:

1. **Deploy to Azure:**
   ```bash
   func azure functionapp publish your-function-app
   ```

2. **Configure Production Settings:**
   ```bash
   az functionapp config appsettings set \
     --name your-function-app \
     --resource-group your-rg \
     --settings @production-settings.json
   ```

3. **Monitor Production:**
   - Set up Application Insights alerts
   - Configure log analytics queries
   - Create dashboard for signal visualization

4. **Tune Thresholds:**
   - Monitor false positive rate
   - Adjust sensitivity based on market conditions
   - Fine-tune cooldown periods

5. **Scale Watchlist:**
   - Start with 1-3 tickers
   - Gradually increase based on API limits
   - Monitor costs and performance

## 📞 Support & Debugging

Enable verbose logging:
```python
# Add to function_app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check Azure Function logs:
```bash
# Real-time streaming
func azure functionapp logstream your-function-app

# Query historical logs
az monitor app-insights query \
  --app your-app-insights \
  --analytics-query "traces | where message contains 'AAPL'"
```

---

**Happy Testing! 🎉**

If you see values updating in real-time, congratulations - your signal detection system is now live and working!
