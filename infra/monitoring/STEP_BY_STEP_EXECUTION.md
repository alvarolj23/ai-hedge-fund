# Step-by-Step Execution Flow

## 🎬 **What Happens When Your Function App Runs**

This shows exactly what happens minute-by-minute when your monitoring system is running.

---

## ⏰ **Timeline: A Typical 15-Minute Period**

```
📅 November 21, 2025 - Market Hours (9:30 AM - 4:00 PM ET)
Watching: AAPL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ 14:00:00 - Multiple Functions Trigger
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌────────────────────────────────────────────────────────┐
│ fast_monitor (1-minute)                                │
│ ⏱️  Started at 14:00:00                                │
└────────────────────────────────────────────────────────┘
  │
  ├─ 1. Check if market is open
  │    ├─ Current time: 14:00:00 ET
  │    ├─ Is it 9:30 AM - 4:00 PM ET? YES ✅
  │    ├─ Is it a holiday? NO ✅
  │    └─ PROCEED with monitoring
  │
  ├─ 2. Fetch real-time quote
  │    ├─ Try yfinance.get_quote("AAPL")
  │    │    ├─ API call... (200ms)
  │    │    └─ SUCCESS: Price = $195.43
  │    │
  │    ├─ If yfinance failed:
  │    │    └─ Try finnhub.get_quote("AAPL")
  │    │    └─ If that fails too: Log warning, skip
  │
  ├─ 3. Quick signal check
  │    ├─ Current price: $195.43
  │    ├─ Previous price: $195.12
  │    ├─ Change: +$0.31 (0.16%)
  │    ├─ Threshold: 0.5%
  │    └─ 0.16% < 0.5% → No fast alert
  │
  └─ ⏱️  Completed at 14:00:01 (1 second)
      Log: "AAPL: No fast signals (change: +0.16%)"

┌────────────────────────────────────────────────────────┐
│ market_monitor (5-minute) - MAIN FUNCTION             │
│ ⏱️  Started at 14:00:00                                │
└────────────────────────────────────────────────────────┘
  │
  ├─ 1. Check if market is open
  │    └─ Same checks as above → PROCEED ✅
  │
  ├─ 2. Fetch intraday price data
  │    ├─ API: Financial Datasets (your main source!)
  │    ├─ URL: https://api.financialdatasets.ai/prices/
  │    │    ?ticker=AAPL
  │    │    &interval=minute          ← 5-min bars
  │    │    &interval_multiplier=5
  │    │    &start_date=2024-05-24    ← 180 days back
  │    │    &end_date=2024-11-21
  │    │
  │    ├─ API call... (1-2 seconds)
  │    │
  │    └─ SUCCESS: 2,340 price bars received
  │         Each bar is 5 minutes of data:
  │         [
  │           {time: "14:00", open: 195.10, close: 195.43, volume: 123,456},
  │           {time: "13:55", open: 194.95, close: 195.12, volume: 98,234},
  │           {time: "13:50", open: 195.20, close: 194.95, volume: 145,678},
  │           ... (2,337 more bars)
  │         ]
  │
  ├─ 3. Fetch previous day's close (for gap detection)
  │    ├─ Previous trading day: Nov 20, 2025
  │    ├─ API: Financial Datasets
  │    ├─ URL: ...interval=day&start_date=2024-11-20&end_date=2024-11-20
  │    └─ Result: Previous close = $194.50
  │
  ├─ 4. Run ENHANCED signal detection (9+ indicators)
  │    │
  │    ├─ Indicator 1: Price Change
  │    │    ├─ Latest close: $195.43
  │    │    ├─ Previous close: $195.12
  │    │    ├─ Change: +0.16%
  │    │    ├─ Threshold: 2.0%
  │    │    └─ 0.16% < 2.0% → ❌ No signal
  │    │
  │    ├─ Indicator 2: Volume Spike
  │    │    ├─ Latest volume: 123,456
  │    │    ├─ Avg volume (last 10 bars): 118,234
  │    │    ├─ Ratio: 1.04x
  │    │    ├─ Threshold: 1.5x
  │    │    └─ 1.04x < 1.5x → ❌ No signal
  │    │
  │    ├─ Indicator 3: Gap Detection
  │    │    ├─ Today's open: $194.80
  │    │    ├─ Previous close: $194.50
  │    │    ├─ Gap: +0.15%
  │    │    ├─ Threshold: 1.5%
  │    │    └─ 0.15% < 1.5% → ❌ No gap signal
  │    │
  │    ├─ Indicator 4: Volume Velocity
  │    │    └─ Checking acceleration... → ❌ No signal
  │    │
  │    ├─ Indicator 5: Price Velocity
  │    │    └─ Rate of change... → ❌ No signal
  │    │
  │    ├─ Indicator 6: VWAP Deviation
  │    │    ├─ Calculate VWAP from all bars
  │    │    ├─ VWAP: $195.20
  │    │    ├─ Current: $195.43
  │    │    ├─ Deviation: +0.12%
  │    │    ├─ Threshold: 2σ (2.0%)
  │    │    └─ 0.12% < 2.0% → ❌ No signal
  │    │
  │    ├─ Indicator 7: Intraday Breakout
  │    │    └─ Checking highs/lows... → ❌ No breakout
  │    │
  │    ├─ Indicator 8: Bollinger Bands
  │    │    └─ Position: 0.52 (neutral) → ❌ No signal
  │    │
  │    └─ Indicator 9: ATR Expansion
  │         └─ Volatility normal → ❌ No signal
  │
  ├─ 5. Combine all indicators
  │    ├─ Triggered signals: [] (none)
  │    ├─ Confidence: 0%
  │    └─ Priority: low
  │
  ├─ 6. Decision: NO SIGNAL
  │    └─ Do NOT send to Azure Queue
  │
  └─ ⏱️  Completed at 14:00:03 (3 seconds)
      Log: "AAPL: No signals triggered (change: +0.16%, vol ratio: 1.04x)"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ 14:01:00 - fast_monitor runs again
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌────────────────────────────────────────────────────────┐
│ fast_monitor (1-minute)                                │
└────────────────────────────────────────────────────────┘
  │
  ├─ yfinance.get_quote("AAPL")
  ├─ Price: $195.50 (+0.04% from 1 min ago)
  └─ Log: "AAPL: No fast signals (change: +0.04%)"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ 14:02:00 - fast_monitor runs again
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Similar to above... no significant change

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ 14:03:00 - fast_monitor detects movement!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌────────────────────────────────────────────────────────┐
│ fast_monitor (1-minute)                                │
│ ⏱️  Started at 14:03:00                                │
└────────────────────────────────────────────────────────┘
  │
  ├─ yfinance.get_quote("AAPL")
  ├─ Current price: $196.75
  ├─ Previous price: $195.50
  ├─ Change: +$1.25 (0.64%)
  ├─ Threshold: 0.5%
  │
  ├─ 0.64% > 0.5% → 🚨 FAST ALERT!
  │
  ├─ Update Cosmos DB cooldown
  │    └─ Store: AAPL last triggered at 14:03:00
  │
  └─ ⏱️  Completed at 14:03:01
      Log: "🚨 FAST ALERT: AAPL moved 0.64% in last minute"
      Log: "Signal will be picked up by 5-min monitor at 14:05"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ 14:04:00 - fast_monitor (skipped due to cooldown)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌────────────────────────────────────────────────────────┐
│ fast_monitor (1-minute)                                │
└────────────────────────────────────────────────────────┘
  │
  ├─ Check cooldown in Cosmos DB
  │    ├─ Last trigger: 14:03:00 (1 minute ago)
  │    ├─ Cooldown period: 5 minutes
  │    └─ Still in cooldown → Skip checking
  │
  └─ Log: "AAPL in cooldown, skipping"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ 14:05:00 - market_monitor catches the movement!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌────────────────────────────────────────────────────────┐
│ market_monitor (5-minute) - MAIN FUNCTION             │
│ ⏱️  Started at 14:05:00                                │
└────────────────────────────────────────────────────────┘
  │
  ├─ 1. Fetch intraday data from Financial Datasets
  │    └─ 2,341 bars (includes new 14:05 bar!)
  │         Latest bar: {time: "14:05", close: 196.85, volume: 456,789}
  │
  ├─ 2. Run ENHANCED signal detection
  │    │
  │    ├─ Indicator 1: Price Change
  │    │    ├─ Latest: $196.85
  │    │    ├─ Previous (14:00): $195.43
  │    │    ├─ Change: +0.73%
  │    │    ├─ Threshold: 2.0%
  │    │    └─ 0.73% < 2.0% → ❌ Still below threshold
  │    │
  │    ├─ Indicator 2: Volume Spike
  │    │    ├─ Latest volume: 456,789
  │    │    ├─ Avg volume: 118,234
  │    │    ├─ Ratio: 3.86x
  │    │    ├─ Threshold: 1.5x
  │    │    └─ 3.86x > 1.5x → ✅ VOLUME SPIKE DETECTED!
  │    │
  │    ├─ Indicator 3: Price Velocity
  │    │    ├─ Moved $1.42 in 5 minutes
  │    │    ├─ Velocity: 0.28%/min
  │    │    ├─ Threshold: 0.1%/min
  │    │    └─ 0.28% > 0.1% → ✅ RAPID MOVEMENT DETECTED!
  │    │
  │    ├─ Indicator 4: Volume Velocity
  │    │    └─ Accelerating → ✅ SIGNAL!
  │    │
  │    └─ Other indicators...
  │         Some trigger, some don't
  │
  ├─ 3. Combine all indicators
  │    ├─ Triggered signals: ["volume_spike", "rapid_movement", "volume_velocity"]
  │    ├─ Confidence: 78%
  │    └─ Priority: HIGH
  │
  ├─ 4. Check cooldown
  │    ├─ Last trigger: 14:03:00 (2 minutes ago) - from fast_monitor
  │    ├─ Cooldown: 30 minutes
  │    └─ Not in cooldown → PROCEED
  │
  ├─ 5. Build queue payload
  │    {
  │      "tickers": ["AAPL"],
  │      "analysis_window": {
  │        "start": "2024-05-24",
  │        "end": "2024-11-21"
  │      },
  │      "signals": ["volume_spike", "rapid_movement", "volume_velocity"],
  │      "market_snapshot": {
  │        "percent_change": 0.73,
  │        "volume_ratio": 3.86,
  │        "latest_close": 196.85,
  │        "previous_close": 195.43,
  │        "price_velocity": 0.28
  │      },
  │      "triggered_at": "2024-11-21T14:05:00Z"
  │    }
  │
  ├─ 6. Send to Azure Queue
  │    ├─ Queue: "market-signals"
  │    └─ SUCCESS ✅
  │
  ├─ 7. Update Cosmos DB cooldown
  │    └─ Store: AAPL last triggered at 14:05:00
  │
  └─ ⏱️  Completed at 14:05:04 (4 seconds)
      Log: "✓ Enqueued analysis request for AAPL with reasons ['volume_spike', 'rapid_movement']"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ 14:10:00 - market_monitor (in cooldown, skips)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌────────────────────────────────────────────────────────┐
│ market_monitor (5-minute)                              │
└────────────────────────────────────────────────────────┘
  │
  ├─ Fetch data from Financial Datasets... OK
  ├─ Run signal detection... 2 signals found
  ├─ Check cooldown
  │    ├─ Last trigger: 14:05:00 (5 minutes ago)
  │    ├─ Cooldown: 30 minutes
  │    └─ Still in cooldown → SKIP sending to queue
  │
  └─ Log: "AAPL: Signals detected but skipped due to cooldown"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ 14:15:00 - validation_monitor checks recent signal
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌────────────────────────────────────────────────────────┐
│ validation_monitor (15-minute)                         │
│ ⏱️  Started at 14:15:00                                │
└────────────────────────────────────────────────────────┘
  │
  ├─ 1. Check Cosmos DB for recent signals
  │    └─ Found: AAPL triggered at 14:05:00 (10 minutes ago)
  │
  ├─ 2. Validate with Alpha Vantage RSI
  │    ├─ If ALPHA_VANTAGE_API_KEY set:
  │    │    ├─ API call to Alpha Vantage...
  │    │    ├─ RSI(14, 5min): 67.3
  │    │    └─ Result: Neutral (not overbought/oversold)
  │    │
  │    └─ If not set:
  │         └─ Skip (optional feature)
  │
  ├─ 3. Validate trend with yfinance
  │    ├─ Get last 12 bars (1 hour)
  │    ├─ Count up vs down bars: 8 up, 4 down
  │    └─ Result: "Strong uptrend confirmed"
  │
  └─ ⏱️  Completed at 14:15:03
      Log: "✓ AAPL: RSI neutral (67.3)"
      Log: "✓ AAPL: Strong uptrend confirmed (last 60 min)"
```

---

## 📊 **API Call Summary for This 15-Minute Period**

| Time | Function | API Used | Purpose | Result |
|------|----------|----------|---------|--------|
| 14:00 | fast_monitor | yfinance | Real-time quote | No alert |
| 14:00 | market_monitor | **Financial Datasets** | 5-min bars | No signal |
| 14:00 | market_monitor | **Financial Datasets** | Previous close | Got data |
| 14:01 | fast_monitor | yfinance | Real-time quote | No alert |
| 14:02 | fast_monitor | yfinance | Real-time quote | No alert |
| 14:03 | fast_monitor | yfinance | Real-time quote | **🚨 Fast alert!** |
| 14:04 | fast_monitor | *(skipped cooldown)* | - | Skipped |
| 14:05 | market_monitor | **Financial Datasets** | 5-min bars | **✅ Signal detected!** |
| 14:10 | market_monitor | **Financial Datasets** | 5-min bars | Cooldown skip |
| 14:15 | validation_monitor | Alpha Vantage | RSI | Validation |
| 14:15 | validation_monitor | yfinance | Trend | Confirmed |

**Financial Datasets calls:** 4 times (every 5 minutes for market_monitor)
**yfinance calls:** 8 times (every 1 minute + validation)
**Alpha Vantage calls:** 1 time (every 15 minutes, only if signal exists)

---

## 🎯 **Key Takeaways**

1. **Financial Datasets is STILL the primary source** - Used for all main signal detection
2. **yfinance provides early warning** - Catches rapid moves 2 minutes before main monitor
3. **All functions are independent** - If one fails, others continue
4. **Cooldowns prevent spam** - Won't flood your queue with duplicate alerts
5. **Validation is optional** - Provides extra confidence but not required

---

## 💡 **What If APIs Fail?**

### Scenario: Financial Datasets API is down

```
⏰ 14:05:00
┌────────────────────────────────────────┐
│ market_monitor                         │
└────────────────────────────────────────┘
  │
  ├─ Try Financial Datasets API...
  ├─ ERROR: 503 Service Unavailable
  │
  ├─ Log: "Failed to fetch prices for AAPL: 503"
  ├─ SKIP this ticker
  └─ Continue with next ticker in watchlist

Result: Function continues, just skips this ticker
        Will try again in 5 minutes
```

### Scenario: yfinance is down

```
⏰ 14:03:00
┌────────────────────────────────────────┐
│ fast_monitor                           │
└────────────────────────────────────────┘
  │
  ├─ Try yfinance.get_quote("AAPL")...
  ├─ ERROR: Timeout
  │
  ├─ If FINNHUB_API_KEY set:
  │    └─ Try Finnhub...
  │
  ├─ If no fallback available:
  │    ├─ Log: "No valid quote for AAPL"
  │    └─ SKIP (not critical)
  │
  └─ market_monitor will still run normally at 14:05

Result: Fast monitor fails gracefully
        Main monitor continues normally
```

---

**Does this help clarify how everything works?** The key point is: **Financial Datasets is still your primary source**, and the other APIs are optional enhancements!
