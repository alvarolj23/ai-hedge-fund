Perfect! Now I understand your entire architecture. Let me create a comprehensive diagram and explanation:

🏗️ Your AI Hedge Fund Architecture Explained
Why So Much Infrastructure? Event-Driven Scalability!
Your architecture follows an event-driven, queue-based pattern that allows:

✅ Scale to Zero (pay nothing when idle)
✅ Auto-scaling (handle multiple tickers in parallel)
✅ Retry logic (handle transient failures)
✅ Separation of concerns (monitoring vs processing)
📊 Architecture Diagram with Data Flow
┌─────────────────────────────────────────────────────────────────────┐
│                    🕐 TIME-BASED TRIGGER                             │
│                     Every 5 minutes during                           │
│                     market hours (9:30am-4pm ET)                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  📦 COMPONENT 1: Function App (aihedgefund-monitor)                 │
│  ═══════════════════════════════════════════════════════════════    │
│  CODE: infra/monitoring/function_app.py                             │
│  TRIGGER: Timer (every 5 min)                                       │
│                                                                      │
│  WHAT IT DOES:                                                      │
│  1. Check if market is open (weekdays 9:30am-4pm ET)               │
│  2. Fetch prices for watchlist: [AAPL, MSFT, NVDA, etc.]          │
│  3. Detect signals:                                                 │
│     • Price breakout: >2% price change                             │
│     • Volume spike: >1.5x average volume                           │
│  4. Check cooldown (avoid analyzing same ticker too often)         │
│  5. If signal detected → Send message to queue                     │
│                                                                      │
│  USES:                                                              │
│  • Financial Datasets API (price data)                             │
│  • Cosmos DB (monitor-cooldowns container) - store last trigger    │
└────────────────────────────┬────────────────────────────────────────┘
                             │ Sends JSON message:
                             │ {
                             │   "tickers": ["AAPL"],
                             │   "signals": ["price_breakout"],
                             │   "percent_change": 0.025,
                             │   "volume_ratio": 1.8
                             │ }
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  💾 COMPONENT 2: Storage Queue (analysis-requests)                  │
│  ═══════════════════════════════════════════════════════════════    │
│  RESOURCE: aihedgefundstedriebl4q34/analysis-requests               │
│                                                                      │
│  WHAT IT DOES:                                                      │
│  • Buffers analysis requests                                        │
│  • Triggers Queue Worker when messages arrive                      │
│  • Provides retry logic (if worker fails)                          │
│  • Dead-letter queue for poison messages                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │ Queue depth triggers worker
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  🤖 COMPONENT 3: Queue Worker Job (aihedgefund-queuejob)           │
│  ═══════════════════════════════════════════════════════════════    │
│  CODE: src/jobs/queue_worker.py → src/main.py                      │
│  TRIGGER: Queue message (auto-starts when queue has messages)      │
│  CONTAINER: Docker image from worker.Dockerfile                    │
│                                                                      │
│  WHAT IT DOES:                                                      │
│  1. Picks up message from queue                                    │
│  2. Loads portfolio from Cosmos DB                                 │
│  3. Runs AI hedge fund analysis (18 analyst agents!):             │
│     ┌──────────────────────────────────────────────────────┐      │
│     │  👔 Market Data Analyst                              │      │
│     │  📈 Technical Analyst                                │      │
│     │  💰 Fundamentals Analyst                             │      │
│     │  📰 Sentiment Analyst                                │      │
│     │  ... 14 more agents ...                             │      │
│     └──────────────────────────────────────────────────────┘      │
│  4. Portfolio Manager aggregates all signals                       │
│  5. Risk Manager validates decisions                               │
│  6. Executes paper trades via Alpaca API                          │
│  7. Saves results to Cosmos DB                                     │
│                                                                      │
│  SCALING:                                                           │
│  • Min replicas: 0 (no cost when idle)                            │
│  • Max replicas: 10 (parallel processing)                         │
│  • Scales based on queue depth                                     │
│                                                                      │
│  USES:                                                              │
│  • OpenAI API (18 LLM calls per analysis!)                        │
│  • Financial Datasets API (market data)                           │
│  • Alpaca API (paper trading)                                      │
│  • Cosmos DB (save results)                                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
     ┌──────────────────────┐  ┌──────────────────────┐
     │  💾 Cosmos DB        │  │  📈 Alpaca API       │
     │  (8 containers)      │  │  (Paper Trading)     │
     │                      │  │                      │
     │  • portfolios        │  │  Place paper orders: │
     │  • analyst-signals   │  │  • BUY AAPL 10 @ MKT │
     │  • decisions         │  │  • SELL MSFT 5 @ LMT │
     │  • portfolioSnapshots│  │                      │
     │  • hedgeFundResults  │  └──────────────────────┘
     │  • hedgeFundStatus   │
     │  • broker-orders     │
     │  • monitor-cooldowns │
     └──────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  📊 COMPONENT 4: API Container App (aihedgefund-api)               │
│  ═══════════════════════════════════════════════════════════════    │
│  CODE: docker/Dockerfile → src/main.py                             │
│  STATUS: Currently runs same code as worker (placeholder)          │
│                                                                      │
│  INTENDED FUTURE USE:                                               │
│  • Web UI to view portfolio                                        │
│  • REST API to query Cosmos DB                                     │
│  • Display analyst signals & decisions                             │
│                                                                      │
│  CURRENT STATE: Uses placeholder/same image as worker              │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  📝 COMPONENT 5: Supporting Infrastructure                          │
│  ═══════════════════════════════════════════════════════════════    │
│  • Application Insights (aihedgefund-appi)                         │
│    → Logs, metrics, traces for all components                     │
│                                                                      │
│  • Log Analytics Workspace (aihedgefund-law)                       │
│    → Centralized log storage                                       │
│                                                                      │
│  • Storage Account (aihedgefundstedriebl4q34)                      │
│    → Queues + Function App storage                                 │
│                                                                      │
│  • App Service Plan (aihedgefund-func-plan)                        │
│    → Hosting plan for Function App (consumption/serverless)        │
│                                                                      │
│  • Smart Detector Alert (Failure Anomalies)                        │
│    → Auto-detect unusual error rates                               │
└─────────────────────────────────────────────────────────────────────┘


🔄 Complete Execution Flow (Step-by-Step)
Scenario: AAPL jumps 3% on high volume at 10:00 AM
⏰ 10:00:00 - Timer triggers Function App
   ↓
🔍 10:00:02 - Function fetches prices for [AAPL, MSFT, NVDA, GOOGL, TSLA]
   ↓
📊 10:00:05 - Detects AAPL signal:
              • Price change: +3.2% (threshold: 2%)
              • Volume ratio: 1.8x (threshold: 1.5x)
              • Reasons: ["price_breakout", "volume_spike"]
   ↓
⏳ 10:00:06 - Check cooldown in Cosmos DB
              Last trigger: 9:30 AM (30 min ago) → OK to proceed
   ↓
📤 10:00:07 - Send message to queue (analysis-requests):
              {
                "tickers": ["AAPL"],
                "signals": ["price_breakout", "volume_spike"],
                "triggered_at": "2025-11-20T15:00:07Z",
                "analysis_window": {
                  "start": "2025-11-20T13:00:07Z",
                  "end": "2025-11-20T15:00:07Z"
                }
              }
   ↓
💾 10:00:08 - Update cooldown in Cosmos DB (prevent re-triggering)
   ↓
⚡ 10:00:10 - Queue Worker Job AUTO-STARTS (Container Apps Job)
              (scales from 0 → 1 replica)
   ↓
🤖 10:00:15 - Worker loads portfolio from Cosmos DB
   ↓
🧠 10:00:20 - Run AI analysis with 18 agents:
              [Takes ~2-5 minutes depending on LLM speed]
              
              Agent Flow (LangGraph):
              1. Market Data Analyst → fetch recent data
              2. Technical Analyst → RSI, MACD, moving averages
              3. Fundamentals Analyst → P/E ratio, earnings
              4. Sentiment Analyst → news, social media
              ... 14 more analysts ...
              17. Portfolio Manager → aggregate signals
              18. Risk Manager → validate decisions
   ↓
💼 10:05:30 - Portfolio Manager decision:
              {
                "AAPL": {
                  "action": "buy",
                  "quantity": 10,
                  "confidence": 78,
                  "reasoning": "Strong momentum + earnings beat"
                }
              }
   ↓
🔒 10:05:35 - Risk Manager validates (checks position limits)
   ↓
📈 10:05:40 - Execute paper trade via Alpaca API:
              POST https://paper-api.alpaca.markets/v2/orders
              {
                "symbol": "AAPL",
                "qty": 10,
                "side": "buy",
                "type": "market"
              }
   ↓
💾 10:05:45 - Save to Cosmos DB:
              • analyst-signals (all 18 agent outputs)
              • decisions (portfolio manager decision)
              • portfolios (updated portfolio)
              • broker-orders (Alpaca order confirmation)
              • hedgeFundResults (performance metrics)
   ↓
✅ 10:05:50 - Worker completes, deletes message from queue
   ↓
😴 10:06:00 - Worker scales back to 0 (no cost until next trigger)



Estimated Monthly Costs
Component                    Cost/Month    Why?
═══════════════════════════════════════════════════════════════
Function App                 $2-5          Consumption plan, ~78 hrs/month
Container Apps Job           $5-15         Runs ~10-20 times/day, 2-5 min each
Container Apps API           $0            Scales to 0 (placeholder)
Storage Account              $1            Queues + logs
Cosmos DB                    $0            Serverless, free tier (1M RUs/month)
Log Analytics                $2            30-day retention
Application Insights         $2            Basic monitoring
───────────────────────────────────────────────────────────────
Infrastructure Total:        $12-25/month  💚 Very cheap!

External API Costs (bigger cost!)
───────────────────────────────────────────────────────────────
OpenAI GPT-4                 $50-200       18 LLM calls per analysis!
Financial Datasets           $0-50         Price data
Alpaca                       $0            Paper trading is free
───────────────────────────────────────────────────────────────
TOTAL:                       $62-275/month (mostly LLM costs!)
