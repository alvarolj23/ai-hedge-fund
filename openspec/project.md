# Project Context
## Purpose
AI Hedge Fund is a multi-agent, event-driven trading system. It monitors markets, runs AI analysis, and can execute paper trades via Alpaca. Production deployment uses Azure Functions, Storage Queues, and Container Apps to scale to zero when idle.

## Tech Stack
- Python 3.11 with Poetry
- LangChain and LangGraph for multi-agent orchestration
- FastAPI backend and React/Vite frontend
- Azure Functions, Storage Queues, Container Apps Jobs, Cosmos DB
- Application Insights and Log Analytics
- Docker and Bicep infrastructure
- Alpaca (paper trading) and Financial Datasets API
- LangSmith tracing (optional)

## Project Conventions
### Code Style
- Python formatted with Black (line length 420) and isort (black profile).
- Prefer standard library logging and small, focused modules.
- Use python-dotenv for local configuration.

### Architecture Patterns
- Event-driven pipeline: monitor -> queue -> worker.
- Scale-to-zero serverless components.
- Multi-agent analysis with risk and portfolio manager nodes.
- Broker execution isolated in `src/brokers`.

### Testing Strategy
- pytest for unit and integration tests.
- Integration tests live under tests/backtesting/integration with fixtures.
- End-to-end validation uses paper trading; avoid live trading in tests.

### Git Workflow
- Keep changes small and focused.
- Use OpenSpec for new features, breaking changes, and architecture shifts.
- Update docs when behavior changes.

## Domain Context
- Market monitoring uses configurable thresholds for price and volume signals.
- Analysis runs 18 analysts plus risk and portfolio managers.
- Alpaca paper trading is the default execution path.
- Cosmos DB persistence is optional and can be disabled.

## Important Constraints
- Educational and research use only; no investment advice.
- Paper trading by default; enable live trading only with explicit owner intent.
- LLM costs, quotas, and API rate limits can dominate runtime.
- Corporate networks may require custom certificate bundles (CORP_CA_BUNDLE).

## External Dependencies
- LLM providers: OpenAI, Anthropic, Groq, DeepSeek, Gemini, xAI, GigaChat, OpenRouter, Azure OpenAI.
- Financial data: Financial Datasets API (plus optional multi-API sources in the monitor).
- Broker: Alpaca paper trading API.
- Azure: Functions, Storage Queues, Cosmos DB, Container Apps, Application Insights.
- Observability: LangSmith (optional).
