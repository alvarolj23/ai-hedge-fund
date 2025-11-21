# LangSmith Tracking Setup Guide

This guide explains how to set up LangSmith tracking for the AI Hedge Fund to monitor and trace LLM executions from different analysts.

## What is LangSmith?

LangSmith is an observability platform for LLM applications that provides:
- **Tracing**: End-to-end visibility into LLM calls and their execution
- **Monitoring**: Track token usage, costs, and performance metrics
- **Debugging**: Inspect prompts, responses, and errors
- **Analytics**: Analyze patterns across different analysts and models

## Setup Instructions

### 1. Get Your LangSmith API Key

1. Visit [https://smith.langchain.com/](https://smith.langchain.com/)
2. Sign up or log in to your account
3. Navigate to Settings → API Keys
4. Create a new API key and copy it

### 2. Configure Environment Variables

Add the following variables to your `.env` file:

```bash
# LangSmith Tracing (Optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your-langsmith-api-key
LANGCHAIN_PROJECT=ai-hedge-fund
```

**Environment Variables Explained:**
- `LANGCHAIN_TRACING_V2`: Set to `true` to enable tracing
- `LANGCHAIN_ENDPOINT`: LangSmith API endpoint (default: https://api.smith.langchain.com)
- `LANGCHAIN_API_KEY`: Your LangSmith API key from step 1
- `LANGCHAIN_PROJECT`: Project name to organize your traces (you can customize this)

### 3. Install LangSmith Package (Optional)

The langsmith package is optional. If not installed, the system will work normally but without tracing:

```bash
pip install langsmith
```

### 4. Verify Setup

Once configured, run your hedge fund analysis. You should see traces appearing in your LangSmith dashboard at [https://smith.langchain.com/](https://smith.langchain.com/).

## What Gets Tracked?

### Automatic Tracking

When LangSmith is enabled, the following information is automatically tracked for each LLM call:

1. **Agent Information**
   - Agent name (e.g., `warren_buffett_agent`, `technical_analyst_agent`)
   - Analyst type (extracted from agent name)

2. **Model Information**
   - Model name (e.g., `gpt-4`, `claude-sonnet-4-5`)
   - Model provider (e.g., `OpenAI`, `Anthropic`)
   - Pydantic model used for structured output

3. **Context Information**
   - Ticker symbols being analyzed
   - Request metadata

4. **Tags**
   - `llm_call`: All LLM calls
   - `analyst`: All analyst agents
   - Specific analyst name (e.g., `warren_buffett`, `technical_analyst`)

### Example Trace Metadata

```json
{
  "agent_name": "warren_buffett_agent",
  "model_name": "gpt-4",
  "model_provider": "OpenAI",
  "pydantic_model": "AnalysisResponse",
  "tickers": "AAPL,MSFT"
}
```

## Viewing Traces in LangSmith

### 1. Access Your Dashboard

Go to [https://smith.langchain.com/](https://smith.langchain.com/) and select your project (e.g., `ai-hedge-fund`).

### 2. Filter by Analyst

Use tags to filter traces by specific analysts:
- Click on "Tags" in the filter panel
- Select the analyst you want to view (e.g., `warren_buffett`, `technical_analyst`)

### 3. Analyze Performance

LangSmith provides various metrics:
- **Latency**: How long each LLM call takes
- **Token Usage**: Input and output tokens for cost tracking
- **Error Rates**: Failed calls and retry attempts
- **Cost Tracking**: Estimated costs based on model pricing

### 4. Inspect Individual Traces

Click on any trace to see:
- Full prompt sent to the LLM
- Complete response received
- Metadata and tags
- Timing information
- Error messages (if any)

## Advanced Usage

### Custom Tracing in Your Code

You can also use the `langsmith_tracing_context` directly in your code:

```python
from src.llm.models import langsmith_tracing_context

# Example: Add custom metadata to a specific analysis
with langsmith_tracing_context(
    agent_name="my_custom_agent",
    metadata={"ticker": "AAPL", "analysis_type": "deep_dive"},
    tags=["custom", "deep_analysis"]
):
    result = llm.invoke("Analyze this stock...")
```

### Organizing Traces by Project

You can create different projects for different purposes:

```bash
# Production analysis
LANGCHAIN_PROJECT=ai-hedge-fund-prod

# Testing and development
LANGCHAIN_PROJECT=ai-hedge-fund-dev

# Specific strategy testing
LANGCHAIN_PROJECT=ai-hedge-fund-value-investing
```

### Disabling Tracing

To disable tracing without removing the environment variables:

```bash
LANGCHAIN_TRACING_V2=false
```

Or simply remove/comment out the LangSmith variables from your `.env` file.

## Troubleshooting

### Traces Not Appearing

1. **Check Environment Variables**: Ensure all required variables are set correctly
2. **Verify API Key**: Make sure your LangSmith API key is valid
3. **Check Network**: Ensure your application can reach https://api.smith.langchain.com
4. **Review Console**: Look for warning messages about LangSmith setup

### Warning Messages

If you see warnings like "langsmith package not installed", install it:

```bash
pip install langsmith
```

If tracing setup fails, the system will continue working normally without tracing.

## Benefits for AI Hedge Fund

Using LangSmith tracking provides several benefits:

1. **Compare Analysts**: See which analysts (Warren Buffett vs. Technical Analyst) provide better insights
2. **Cost Optimization**: Track token usage to optimize costs across different models
3. **Performance Monitoring**: Identify slow LLM calls that may need optimization
4. **Debugging**: Quickly identify and fix issues with specific analysts or models
5. **Audit Trail**: Maintain a complete history of all LLM interactions for compliance

## Example Workflow

1. Enable LangSmith in your `.env` file
2. Run analysis for multiple tickers
3. Go to LangSmith dashboard
4. Filter by analyst tag (e.g., `warren_buffett`)
5. Review traces to see:
   - What prompts were sent
   - What recommendations were made
   - How long each analysis took
   - How many tokens were used
6. Compare performance across different analysts
7. Optimize based on insights

## Resources

- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [LangChain Tracing Guide](https://docs.langchain.com/langsmith/trace-with-langchain)
- [LangSmith GitHub](https://github.com/langchain-ai/langsmith-sdk)

## Support

For issues or questions:
- LangSmith: [https://docs.smith.langchain.com/](https://docs.smith.langchain.com/)
- AI Hedge Fund: Create an issue in the repository
