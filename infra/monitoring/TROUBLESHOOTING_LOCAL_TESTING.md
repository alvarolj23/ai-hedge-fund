# Troubleshooting Local Testing - "AccountIsDisabled" Error

## 🔴 **The Error You're Seeing**

```
Status: 403 (The specified account is disabled.)
ErrorCode: AccountIsDisabled
```

## 🎯 **Root Cause**

Your `AzureWebJobsStorage` connection string points to a **disabled or invalid** Azure Storage account. This is an Azure Functions **runtime requirement** - it has nothing to do with our monitoring code or the APIs we use for price data.

## 🔧 **Solution Options**

### **Option 1: Use Azurite (Recommended for Local Testing)** ⭐

This is the **easiest and fastest** way to test locally without needing any Azure resources.

**Step 1: Install Azurite**
```powershell
npm install -g azurite
```

**Step 2: Start Azurite** (in a separate PowerShell terminal)
```powershell
azurite
```

You should see:
```
Azurite Blob service is starting at http://127.0.0.1:10000
Azurite Queue service is starting at http://127.0.0.1:10001
Azurite Table service is starting at http://127.0.0.1:10002
```

**Step 3: Update your `local.settings.json`**
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

**Step 4: Start your function app**
```powershell
func start
```

✅ **This should work!**

---

### **Option 2: Check Your Current Storage Account**

If you want to use your existing Azure Storage account, let's check why it's disabled:

**Step 1: Check account status**
```powershell
# Find your storage account name from the connection string
# It's the part after "AccountName=" in your connection string

az storage account show \
  --name YOUR_STORAGE_ACCOUNT_NAME \
  --resource-group YOUR_RESOURCE_GROUP \
  --query "properties.provisioningState"
```

**Step 2: If it shows anything other than "Succeeded", the account is disabled**

Possible reasons:
- Account was deleted
- Subscription expired
- Account was manually disabled
- Network restrictions blocking access

---

### **Option 3: Create a New Development Storage Account**

If your storage account is disabled and you can't re-enable it:

```powershell
# Create new storage account
az storage account create \
  --name aihedgefunddev \
  --resource-group your-rg \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2

# Get the connection string
az storage account show-connection-string \
  --name aihedgefunddev \
  --resource-group your-rg \
  --output tsv
```

Then update your `local.settings.json` with the new connection string.

---

## ⚡ **Quick Test Without Azure Storage (Skip Optional Features)**

If you just want to test the **core monitoring logic** without worrying about Azure Storage, you can test the individual modules directly:

### **Test 1: Test Market Calendar (No Azure needed)**

Create `test_calendar.py`:
```python
from market_calendar import is_market_open, is_market_holiday
from datetime import datetime, date
from zoneinfo import ZoneInfo

now = datetime.now(ZoneInfo("America/New_York"))
print(f"Is market open now? {is_market_open(now)}")

thanksgiving = date(2025, 11, 27)
print(f"Is Thanksgiving a holiday? {is_market_holiday(thanksgiving)}")
```

Run it:
```powershell
cd infra\monitoring
python test_calendar.py
```

---

### **Test 2: Test Signal Detection (No Azure needed)**

Create `test_signals.py`:
```python
from signal_detection import enhanced_signal_detection
from models import Price
from datetime import datetime, timezone

# Create sample price data
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
    previous_day_close=base_price
)

print(f"\n=== Signal Detection Test ===")
print(f"Triggered: {result.triggered}")
print(f"Reasons: {result.reasons}")
print(f"Confidence: {result.confidence:.0%}")
print(f"Priority: {result.priority}")
print(f"Metrics:")
for key, value in result.metrics.items():
    print(f"  {key}: {value}")
```

Run it:
```powershell
python test_signals.py
```

Expected output:
```
=== Signal Detection Test ===
Triggered: True
Reasons: ['price_breakout', 'volume_spike', 'rapid_movement']
Confidence: 85%
Priority: high
Metrics:
  percent_change: 2.0
  volume_ratio: 3.0
  price_velocity: 0.4
  ...
```

---

### **Test 3: Test Multi-API Client (No Azure needed)**

Create `test_apis.py`:
```python
from multi_api_client import MultiAPIClient

client = MultiAPIClient()

print("\n=== Testing Real-Time Quote ===")
quote = client.get_best_quote("AAPL")
if quote:
    print(f"Ticker: {quote.ticker}")
    print(f"Price: ${quote.price:.2f}")
    print(f"Source: {quote.source}")
else:
    print("Failed to get quote")

print("\n=== Testing Intraday Bars ===")
bars = client.get_intraday_bars("AAPL", interval_minutes=5, limit=5)
print(f"Retrieved {len(bars)} bars")
if bars:
    latest = bars[-1]
    print(f"Latest bar - Close: ${latest.close:.2f}, Volume: {latest.volume:,}")
```

Run it:
```powershell
python test_apis.py
```

---

## 📋 **Checklist: Which Solution Should You Use?**

**Choose Azurite if:**
- ✅ You want to test locally without Azure resources
- ✅ You don't want to deal with Azure Storage account issues
- ✅ You want the fastest setup (5 minutes)

**Choose New Storage Account if:**
- ✅ You want to test with real Azure resources
- ✅ You want to test the full end-to-end flow including queues
- ✅ Your current storage account is permanently disabled

**Choose Direct Module Testing if:**
- ✅ You just want to verify the core logic works
- ✅ You don't need to test the Azure Functions timer triggers
- ✅ You want to test without any Azure setup

---

## 🎯 **Recommended Path**

For quickest testing, I recommend:

1. **Start Azurite** (1 minute)
2. **Update local.settings.json** to use `"UseDevelopmentStorage=true"` (1 minute)
3. **Run `func start`** (works!)

Total time: **2-3 minutes** to get running!

---

## ❓ **Still Having Issues?**

### Issue: "npm: command not found"

Install Node.js first:
1. Download from https://nodejs.org/
2. Install (includes npm)
3. Restart PowerShell
4. Run `npm install -g azurite`

### Issue: Azurite won't start

Try specifying a custom location:
```powershell
azurite --location c:\azurite --debug c:\azurite\debug.log
```

### Issue: Functions still won't start

Check if port 10000 is already in use:
```powershell
netstat -ano | findstr :10000
```

If it's in use, stop Azurite and start again.

---

**Bottom line: Your storage account issue is NOT related to the Financial Datasets API or our new enhancements. It's just an Azure Functions runtime requirement for local testing.**
