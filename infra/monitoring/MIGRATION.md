# Azure Functions Migration to v2 Programming Model

## What Changed

We migrated from Azure Functions Python v1 programming model to v2 programming model.

### Before (v1 - folder-based with function.json)
```
monitoring/
├── market_monitor/
│   ├── __init__.py        # Function code with def main()
│   └── function.json      # Function binding configuration
├── host.json
└── requirements.txt
```

### After (v2 - decorator-based)
```
monitoring/
├── function_app.py        # All functions with @app decorators
├── host.json
└── requirements.txt
```

## Key Differences

### V1 Programming Model (OLD)
- Each function in its own folder
- Separate `function.json` for bindings
- Function named `main()` by convention
- More boilerplate, harder to maintain

### V2 Programming Model (NEW)
- All functions in `function_app.py`
- Decorators define triggers and bindings
- Functions can have any name
- More Pythonic, easier to test
- Better IntelliSense support

## Function Definition

### Old (v1)
```python
# market_monitor/__init__.py
def main(market_timer: func.TimerRequest) -> None:
    # function logic
```

```json
// market_monitor/function.json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "name": "market_timer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 */5 * * * *"
    }
  ]
}
```

### New (v2)
```python
# function_app.py
app = func.FunctionApp()

@app.timer_trigger(schedule="0 */5 * * * *", arg_name="market_timer")
def market_monitor(market_timer: func.TimerRequest) -> None:
    # function logic
```

## Benefits

1. **Single file** - All functions in one place
2. **Type safety** - Better IDE support
3. **Less boilerplate** - No separate JSON config
4. **Easier testing** - Functions are just Python functions
5. **Modern standard** - Microsoft's recommended approach

## Deployment

The deployment script now:
1. Excludes the old `market_monitor/` folder
2. Includes `function_app.py` as the main entry point
3. Still copies necessary `src/` dependencies

## References

- [Azure Functions Python v2 Programming Model](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python?tabs=get-started%2Casgi%2Capplication-level&pivots=python-mode-decorators)
