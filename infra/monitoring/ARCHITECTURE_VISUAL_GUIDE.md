# Visual Architecture Guide - How Your Signal Detection System Works Now

## 🎯 **Quick Answer**

**YES, Financial Datasets API is still your PRIMARY source!** The new APIs (yfinance, Finnhub, etc.) are **optional add-ons** for faster real-time detection. If they fail or aren't configured, the system falls back gracefully.

---

## 📊 **Architecture Diagram - Before vs After**

### **BEFORE (Your Original System)**

```
┌─────────────────────────────────────────────────────────┐
│            market_monitor (Every 5 minutes)             │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Financial Datasets API (Daily Bars)              │  │
│  │ interval=day                                     │  │
│  │                                                  │  │
│  │ Problem: Gets same value all day! ❌            │  │
│  └──────────────────────────────────────────────────┘  │
│                          ↓                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Simple Detection (2 indicators)                  │  │
│  │ - Price change %                                 │  │
│  │ - Volume ratio                                   │  │
│  └──────────────────────────────────────────────────┘  │
│                          ↓                              │
│                   Azure Queue                           │
└─────────────────────────────────────────────────────────┘
```

**Issues:**
- ❌ Same values throughout the day (stale data)
- ❌ Only 2 basic indicators
- ❌ Single point of failure (1 API)
- ❌ 5-10 minute detection latency

---

### **AFTER (New Enhanced System - Option 4)**

```
╔═══════════════════════════════════════════════════════════════════════╗
║                    THREE-TIER MONITORING SYSTEM                        ║
╚═══════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│  TIER 1: fast_monitor (Every 1 minute) - OPTIONAL                      │
│  Purpose: Catch rapid movements                                        │
│                                                                         │
│  ┌────────────────────────────────────────────────────────┐            │
│  │ Primary: yfinance (FREE, no API key)                   │            │
│  │ - Real-time quotes                                     │            │
│  │ - 1-minute bars                                        │            │
│  │                                                        │            │
│  │ Fallback 1: Finnhub (optional, 60 calls/min)          │            │
│  │ Fallback 2: Skip if both fail (not critical)          │            │
│  └────────────────────────────────────────────────────────┘            │
│                          ↓                                              │
│  Quick check: >0.5% move in last minute?                               │
│  If YES → Flag for main monitor                                        │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  TIER 2: market_monitor (Every 5 minutes) - REQUIRED                   │
│  Purpose: Comprehensive analysis with enhanced indicators              │
│                                                                         │
│  ┌────────────────────────────────────────────────────────┐            │
│  │ PRIMARY: Financial Datasets API ⭐                     │            │
│  │ interval=minute (NOT day anymore!)                     │            │
│  │ interval_multiplier=5 (5-minute bars)                  │            │
│  │                                                        │            │
│  │ ✅ This is still your main data source!               │            │
│  │ ✅ Gets REAL intraday data now                        │            │
│  │ ✅ Values update every 5 minutes                      │            │
│  └────────────────────────────────────────────────────────┘            │
│                          ↓                                              │
│  ┌────────────────────────────────────────────────────────┐            │
│  │ Enhanced Signal Detection (9+ indicators)              │            │
│  │ - Gap detection                                        │            │
│  │ - Volume velocity                                      │            │
│  │ - Price velocity                                       │            │
│  │ - VWAP deviation                                       │            │
│  │ - Intraday breakouts                                   │            │
│  │ - Bollinger Bands                                      │            │
│  │ - ATR expansion                                        │            │
│  │ - Volatility analysis                                  │            │
│  │ - Multi-timeframe                                      │            │
│  └────────────────────────────────────────────────────────┘            │
│                          ↓                                              │
│  If signal detected → Send to Azure Queue                              │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  TIER 3: validation_monitor (Every 15 minutes) - OPTIONAL              │
│  Purpose: Validate recent signals, reduce false positives              │
│                                                                         │
│  ┌────────────────────────────────────────────────────────┐            │
│  │ Primary: Alpha Vantage (optional, 25 calls/day)        │            │
│  │ - RSI indicator                                        │            │
│  │ - Trend confirmation                                   │            │
│  │                                                        │            │
│  │ Fallback: yfinance for trend analysis                 │            │
│  │ Skip if not configured (not critical)                  │            │
│  └────────────────────────────────────────────────────────┘            │
│                          ↓                                              │
│  Log validation results for monitoring                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 **How the Fallback System Works**

### **Scenario 1: Only Financial Datasets API Configured (Minimum)**

```
User Configuration:
✅ FINANCIAL_DATASETS_API_KEY=abc123
❌ FINNHUB_API_KEY=not set
❌ ALPHA_VANTAGE_API_KEY=not set

What Happens:
┌─────────────────────────────────┐
│ fast_monitor (1-min)            │
│ - Tries yfinance (no key needed)│
│ - If fails: SKIPS ✓             │
│ - Not critical, continues       │
└─────────────────────────────────┘
           ↓
┌─────────────────────────────────┐
│ market_monitor (5-min)          │
│ - Uses Financial Datasets ✅    │
│ - Gets 5-minute bars            │
│ - Works perfectly!              │
└─────────────────────────────────┘
           ↓
┌─────────────────────────────────┐
│ validation_monitor (15-min)     │
│ - Tries Alpha Vantage           │
│ - Not configured: SKIPS ✓       │
│ - Not critical, continues       │
└─────────────────────────────────┘

Result: ✅ System works with just Financial Datasets!
```

### **Scenario 2: All APIs Configured (Maximum Performance)**

```
User Configuration:
✅ FINANCIAL_DATASETS_API_KEY=abc123
✅ FINNHUB_API_KEY=xyz789
✅ ALPHA_VANTAGE_API_KEY=def456

What Happens:
┌─────────────────────────────────┐
│ fast_monitor (1-min)            │
│ - Uses yfinance ✅              │
│ - Gets real-time quotes         │
│ - Detects rapid moves           │
└─────────────────────────────────┘
           ↓
┌─────────────────────────────────┐
│ market_monitor (5-min)          │
│ - Uses Financial Datasets ✅    │
│ - Gets 5-minute bars            │
│ - Runs enhanced detection       │
└─────────────────────────────────┘
           ↓
┌─────────────────────────────────┐
│ validation_monitor (15-min)     │
│ - Uses Alpha Vantage ✅         │
│ - Confirms with RSI             │
│ - Validates signals             │
└─────────────────────────────────┘

Result: ✅ Full system with <1 min detection!
```

### **Scenario 3: API Failure During Runtime**

```
Runtime Situation:
Financial Datasets API temporarily fails

What Happens:
┌─────────────────────────────────┐
│ market_monitor tries to fetch   │
│ Financial Datasets API          │
│        ↓                        │
│   [ERROR 503]                   │
│        ↓                        │
│ Exception logged ✓              │
│ Skip this ticker                │
│ Continue with next ticker       │
└─────────────────────────────────┘

Result: ✅ Graceful degradation, logs error
```

---

## 📋 **API Usage Breakdown**

### **Which Function Uses Which API**

| Function | Primary API | Fallback API | Can Skip? | Purpose |
|----------|-------------|--------------|-----------|---------|
| **fast_monitor** | yfinance | Finnhub | ✅ Yes | Quick real-time check |
| **market_monitor** | **Financial Datasets** | None | ❌ No | Main signal detection |
| **validation_monitor** | Alpha Vantage | yfinance | ✅ Yes | Signal confirmation |

### **Data Flow for Each Function**

#### **fast_monitor (Every 1 minute)**
```python
def fast_monitor():
    # OPTIONAL - Can be disabled by not providing API keys

    # Try to get real-time quote
    quote = yfinance.get_quote("AAPL")  # No API key needed

    if quote fails:
        quote = finnhub.get_quote("AAPL")  # Optional

    if quote still fails:
        log warning and skip  # Not critical
        return

    # Quick check: Did price move >0.5%?
    if price_change > 0.5%:
        log "FAST ALERT"
        # Main monitor will catch it on next 5-min run
```

#### **market_monitor (Every 5 minutes)**
```python
def market_monitor():
    # REQUIRED - This is your main function!

    # Fetch intraday data from Financial Datasets
    prices = get_prices(
        ticker="AAPL",
        interval="minute",           # ← Changed from "day"
        interval_multiplier=5,       # ← 5-minute bars
        start_date="2024-05-24",
        end_date="2024-11-21"
    )

    # NO FALLBACK - Financial Datasets is required
    # If this fails, exception is logged and ticker is skipped

    # Run enhanced signal detection (9+ indicators)
    result = enhanced_signal_detection(prices)

    if result.triggered:
        send_to_queue(result)  # Trigger full analysis
```

#### **validation_monitor (Every 15 minutes)**
```python
def validation_monitor():
    # OPTIONAL - Only runs if API keys configured

    # Check recent signals from last 15 minutes
    recent_signals = get_recent_signals()

    for ticker in recent_signals:
        # Try to validate with RSI
        rsi = alpha_vantage.get_rsi(ticker)  # Optional

        if rsi not available:
            # Fall back to yfinance for trend
            bars = yfinance.get_bars(ticker)
            check_trend(bars)

        log validation results  # Just for monitoring
```

---

## 🎛️ **Configuration Options**

### **Minimum Configuration (Works with ONLY Financial Datasets)**

```json
{
  "FINANCIAL_DATASETS_API_KEY": "your_key",
  "MARKET_MONITOR_INTERVAL": "minute",
  "MARKET_MONITOR_INTERVAL_MULTIPLIER": "5"
}
```

**What works:**
- ✅ market_monitor (main function) - Uses Financial Datasets
- ⚠️ fast_monitor - Tries yfinance (free), skips if fails
- ⚠️ validation_monitor - Skips (no Alpha Vantage key)

**Detection latency:** ~5 minutes (same as before, but with REAL-TIME data now!)

---

### **Recommended Configuration (Add yfinance support)**

```json
{
  "FINANCIAL_DATASETS_API_KEY": "your_key",
  "MARKET_MONITOR_INTERVAL": "minute",
  "MARKET_MONITOR_INTERVAL_MULTIPLIER": "5"
}
```

**No extra API keys needed!** yfinance is free and requires no API key.

**What works:**
- ✅ market_monitor - Uses Financial Datasets
- ✅ fast_monitor - Uses yfinance (free)
- ⚠️ validation_monitor - Skips (no Alpha Vantage key)

**Detection latency:** <1 minute (fast_monitor catches rapid moves)

---

### **Full Configuration (Maximum Performance)**

```json
{
  "FINANCIAL_DATASETS_API_KEY": "your_key",
  "FINNHUB_API_KEY": "your_finnhub_key",
  "ALPHA_VANTAGE_API_KEY": "your_av_key",
  "MARKET_MONITOR_INTERVAL": "minute",
  "MARKET_MONITOR_INTERVAL_MULTIPLIER": "5"
}
```

**What works:**
- ✅ market_monitor - Uses Financial Datasets
- ✅ fast_monitor - Uses yfinance + Finnhub fallback
- ✅ validation_monitor - Uses Alpha Vantage + yfinance fallback

**Detection latency:** <1 minute with validation

---

## 🔑 **Key Changes Explained**

### **What Changed in api_client.py**

**BEFORE:**
```python
def get_prices(ticker, start_date, end_date):
    url = f"...interval=day&..."  # ← Always daily bars
```

**AFTER:**
```python
def get_prices(ticker, start_date, end_date, interval="day", interval_multiplier=1):
    url = f"...interval={interval}&interval_multiplier={interval_multiplier}..."
    # ← Now configurable! Defaults to "day" for backward compatibility
```

**Impact:**
- ✅ Still uses Financial Datasets API (your existing source)
- ✅ Now can request intraday bars (minute, 5-minute, 15-minute, etc.)
- ✅ Backward compatible (still defaults to daily if not specified)

---

### **What Changed in function_app.py**

**BEFORE:**
```python
# Only one function
def market_monitor():
    prices = get_prices(ticker, start, end)  # Gets daily bars
    # Simple 2-indicator check
```

**AFTER:**
```python
# Three functions working together

def fast_monitor():  # NEW - Every 1 minute
    # Optional - uses yfinance/Finnhub
    # Quick check for rapid moves

def market_monitor():  # ENHANCED - Every 5 minutes
    prices = get_prices(
        ticker, start, end,
        interval="minute",        # ← Request intraday data
        interval_multiplier=5     # ← 5-minute bars
    )
    # Still uses Financial Datasets!
    # Now with 9+ indicators instead of 2

def validation_monitor():  # NEW - Every 15 minutes
    # Optional - uses Alpha Vantage
    # Validates recent signals
```

---

## 💡 **Common Questions**

### **Q: Do I NEED to get API keys for Finnhub, Polygon, etc.?**
**A:** NO! Financial Datasets is still your primary source. The others are optional for faster detection.

### **Q: What if yfinance/Finnhub fail?**
**A:** The fast_monitor logs a warning and skips. The market_monitor (your main function) still runs normally every 5 minutes.

### **Q: Is Financial Datasets still being used?**
**A:** YES! It's the PRIMARY source for the market_monitor (your main 5-minute function). Nothing changed there except we now request intraday bars instead of daily bars.

### **Q: Why add these other APIs if Financial Datasets works?**
**A:**
- **Speed:** yfinance can give you updates every 1 minute (vs 5 minutes)
- **Redundancy:** If Financial Datasets is slow, yfinance provides alternative
- **Free:** yfinance requires no API key
- **Optional:** You can disable them completely

### **Q: Can I disable the fast_monitor and validation_monitor?**
**A:** YES! Just don't set the optional API keys. The main market_monitor will still work perfectly with just Financial Datasets.

---

## 🎯 **Bottom Line**

```
┌──────────────────────────────────────────────────────┐
│  CORE SYSTEM (Required - Same as before)             │
│  ✅ Financial Datasets API                           │
│  ✅ market_monitor (every 5 minutes)                 │
│  ✅ Enhanced from daily → 5-minute intraday bars     │
│  ✅ Enhanced from 2 → 9+ indicators                  │
└──────────────────────────────────────────────────────┘
                      +
┌──────────────────────────────────────────────────────┐
│  BONUS FEATURES (Optional - New additions)           │
│  ⚡ fast_monitor (1-minute with yfinance/Finnhub)   │
│  ⚡ validation_monitor (15-min with Alpha Vantage)  │
│  ⚡ Can be disabled by not providing API keys       │
└──────────────────────────────────────────────────────┘
```

**You can use the system with JUST Financial Datasets and it will work great!** The other APIs are bonuses for even faster detection.

---

**Does this clarify the architecture?** Let me know if you want me to explain any specific part in more detail!
