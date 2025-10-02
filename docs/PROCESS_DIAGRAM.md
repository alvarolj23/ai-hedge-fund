```mermaid
graph TB
    subgraph "PHASE 1: MARKET MONITORING"
        A[Azure Function Timer<br/>Every 5 min during market hours] -->|Fetch prices| B[Price Data API]
        B --> C{Evaluate Signals}
        C -->|Price breakout >2%<br/>OR Volume spike >1.5x| D[Check Cooldown<br/>Cosmos DB]
        D -->|Cooldown expired| E[Enqueue Message<br/>analysis-requests]
        D -->|Still in cooldown| F[Skip ticker]
        C -->|No signals| F
    end

    subgraph "PHASE 2: ANALYSIS ORCHESTRATION"
        E --> G[Container App Job<br/>Queue Worker Polls]
        G -->|Receive & Delete Message| H{Validate Payload}
        H -->|Invalid| I[Dead Letter Queue<br/>analysis-deadletter]
        H -->|Valid| J[Fetch Portfolio Snapshot<br/>Cosmos DB]
        J -->|No snapshot| K[ERROR: No Portfolio]
        J -->|Snapshot found| L[run_hedge_fund]
    end

    subgraph "PHASE 3: MULTI-AGENT ANALYSIS"
        L --> M[Start Node]
        M --> N1[Selected Analysts<br/>Run in Parallel]
        
        N1 --> A1[Warren Buffett<br/>Value Investing]
        N1 --> A2[Michael Burry<br/>Contrarian]
        N1 --> A3[Peter Lynch<br/>GARP]
        N1 --> A4[Charlie Munger<br/>Quality]
        N1 --> A5[Bill Ackman<br/>Activist]
        N1 --> A6[Cathie Wood<br/>Innovation]
        N1 --> A7[Technical Agent<br/>Charts]
        N1 --> A8[Fundamental Agent<br/>Financials]
        N1 --> A9[Sentiment Agent<br/>News/Social]
        N1 --> A10[+ 9 more analysts]
        
        A1 --> R[Risk Manager<br/>Assess Portfolio Risk]
        A2 --> R
        A3 --> R
        A4 --> R
        A5 --> R
        A6 --> R
        A7 --> R
        A8 --> R
        A9 --> R
        A10 --> R
        
        R --> P[Portfolio Manager<br/>Final Decisions]
        P --> D1{Decision Output}
    end

    subgraph "PHASE 4: PERSISTENCE & EXECUTION"
        D1 --> S1[Save Results<br/>hedgeFundResults]
        D1 --> S2[Publish Status<br/>hedgeFundStatus]
        D1 -.->|NOT YET IMPLEMENTED| T1[Dispatch Orders<br/>Alpaca Paper Trading]
        T1 -.-> T2[Update Portfolio<br/>portfolioSnapshots]
    end

    style A fill:#90EE90
    style E fill:#90EE90
    style G fill:#FFD700
    style L fill:#FFD700
    style M fill:#87CEEB
    style R fill:#87CEEB
    style P fill:#87CEEB
    style S1 fill:#90EE90
    style S2 fill:#90EE90
    style T1 fill:#FFB6C1
    style T2 fill:#FFB6C1
    style I fill:#FF6347
    style K fill:#FF6347

    classDef working fill:#90EE90,stroke:#333,stroke-width:2px
    classDef partial fill:#FFD700,stroke:#333,stroke-width:2px
    classDef planned fill:#87CEEB,stroke:#333,stroke-width:2px
    classDef missing fill:#FFB6C1,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    classDef error fill:#FF6347,stroke:#333,stroke-width:2px
```

## Legend

- 🟢 **Green (Solid)**: Working components
- 🟡 **Yellow (Solid)**: Partially working, needs testing
- 🔵 **Blue (Solid)**: Configured but not fully tested
- 🌸 **Pink (Dashed)**: Planned but not implemented
- 🔴 **Red (Solid)**: Error conditions

## Current Status Summary

| Phase | Status | Details |
|-------|--------|---------|
| **1. Market Monitoring** | ✅ **WORKING** | Function app successfully monitors prices, detects signals, enqueues messages |
| **2. Queue Worker** | ⚠️ **PARTIALLY WORKING** | Polls queue, validates messages, fetches portfolio - **NOW FIXED** after encoding issue |
| **3. Multi-Agent Analysis** | 🔵 **CONFIGURED** | All 18 analysts ready, LangGraph workflow defined - **NEEDS TESTING** |
| **4. Trading Execution** | ❌ **NOT IMPLEMENTED** | Alpaca integration exists in CLI but not in queue worker |

## Critical Path to Full Functionality

1. ✅ **Fix queue message encoding** - COMPLETED
2. 🔄 **Seed initial portfolio** in Cosmos DB
3. 🔄 **Verify multi-agent analysis** runs successfully
4. 🔄 **Integrate Alpaca trading** into queue worker
