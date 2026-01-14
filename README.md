# AI Hedge Fund

AI-powered, event-driven trading system that monitors markets, runs multi-agent analysis, and can execute paper trades via Alpaca.

Status: Deployed on Azure; automated runs are active. Trade execution is paper-only by default.

<img width="1042" alt="AI Hedge Fund system diagram" src="https://github.com/user-attachments/assets/cbae3dcf-b571-490d-b0ad-3f0f035ac0d4" />

## What it does
- Monitors market data and triggers analysis during market hours.
- Orchestrates multi-agent analysis (18 analysts plus risk and portfolio managers) with LangGraph.
- Applies risk checks and aggregates signals into a single decision.
- Executes paper trades via Alpaca and can optionally persist results in Cosmos DB.
- Provides CLI and web app interfaces for interactive runs.

## Documentation
- docs/overview.md
- docs/architecture.md
- docs/operations.md

## Quickstart (local)
1. Create `.env` from `.env.example` and set at least one LLM API key.
2. Install dependencies:

```bash
poetry install
```

3. Run the CLI:

```bash
poetry run python src/main.py --tickers AAPL,MSFT --trade-mode analysis
```

For the web app, see `app/README.md`.

## Disclaimer
This project is for educational and research purposes only.
- Not investment advice.
- Use paper trading unless you are prepared to accept the risks of live trading.
- The authors assume no liability for financial losses.
