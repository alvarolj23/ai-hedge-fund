"""
Quick test to verify Alpaca Paper Trading API connection.

This script tests:
1. API credentials are valid
2. Account information can be fetched
3. Portfolio data can be retrieved
4. Certificate setup works (corporate environments)

Usage:
    python tests/test_alpaca_connection.py
"""

import sys
import os
import tempfile

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SSL / Certificate setup for corporate environments
print("🔒 Setting up SSL certificates...")
try:
    from src.utils.ssl_utils import create_combined_cabundle
    
    # Try Windows certificate store integration first
    try:
        from windows_cert_helpers import patch_ssl_with_windows_trust_store
        patch_ssl_with_windows_trust_store()
        print("   ✅ Windows certificate store integration enabled")
    except Exception:
        print("   ⚠️  Windows certificate store not available, using CA bundle fallback")
    
    # Create combined CA bundle (certifi + corporate CA)
    CORP_CA_BUNDLE = os.getenv(
        "CORP_CA_BUNDLE",
        r"C:\Users\ama5332\OneDrive - Toyota Motor Europe\Documents\certs\TME_certificates_chain.crt"
    )
    
    combined_bundle = create_combined_cabundle(CORP_CA_BUNDLE)
    if combined_bundle:
        print(f"   ✅ Combined CA bundle created: {combined_bundle}")
    else:
        print("   ⚠️  No corporate CA bundle found, using system certificates only")
        
except Exception as e:
    print(f"   ⚠️  SSL setup warning: {e}")
    print("   Continuing with default certificate validation...")

print("\n" + "=" * 60)
print("ALPACA PAPER TRADING CONNECTION TEST")
print("=" * 60 + "\n")

# Test 1: Check credentials
print("1️⃣  Checking credentials...")
api_key = os.getenv("APCA_API_KEY_ID")
api_secret = os.getenv("APCA_API_SECRET_KEY")
api_base = os.getenv("APCA_API_BASE_URL")

if not api_key or not api_secret:
    print("❌ FAILED: Missing Alpaca credentials")
    print("   Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in .env file")
    sys.exit(1)

print(f"   API Key: {api_key[:8]}...{api_key[-4:]}")
print(f"   API Base: {api_base}")
print("   ✅ Credentials found\n")

# Test 2: Initialize client
print("2️⃣  Initializing Alpaca client...")
try:
    from src.brokers.portfolio_fetcher import AlpacaPortfolioFetcher
    
    fetcher = AlpacaPortfolioFetcher(paper=True)
    print("   ✅ Client initialized successfully\n")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    sys.exit(1)

# Test 3: Fetch account info
print("3️⃣  Fetching account information...")
try:
    account = fetcher.get_account_info()
    
    print(f"   Account Number: {account['account_number']}")
    print(f"   Cash: ${account['cash']:,.2f}")
    print(f"   Equity: ${account['equity']:,.2f}")
    print(f"   Buying Power: ${account['buying_power']:,.2f}")
    print(f"   Portfolio Value: ${account['portfolio_value']:,.2f}")
    print(f"   Pattern Day Trader: {account['pattern_day_trader']}")
    print(f"   Trading Blocked: {account['trading_blocked']}")
    print(f"   Currency: {account['currency']}")
    print("   ✅ Account info fetched successfully\n")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Fetch portfolio positions
print("4️⃣  Fetching portfolio snapshot...")
try:
    test_tickers = ["AAPL", "MSFT", "NVDA", "TSLA"]
    portfolio = fetcher.get_portfolio_snapshot(tickers=test_tickers)
    
    print(f"   Cash: ${portfolio['cash']:,.2f}")
    print(f"   Equity: ${portfolio['equity']:,.2f}")
    print(f"   Buying Power: ${portfolio['buying_power']:,.2f}")
    print(f"   Margin Used: ${portfolio['margin_used']:,.2f}")
    print(f"   Margin Requirement: {portfolio['margin_requirement']:.0%}")
    
    # Count active positions
    active_positions = [
        ticker for ticker, pos in portfolio['positions'].items()
        if pos['long'] > 0 or pos['short'] > 0
    ]
    
    print(f"   Active Positions: {len(active_positions)}")
    
    if active_positions:
        print("\n   Current Positions:")
        for ticker in active_positions:
            pos = portfolio['positions'][ticker]
            if pos['long'] > 0:
                print(f"      {ticker}: {pos['long']} shares LONG @ ${pos['long_cost_basis']:.2f}")
            if pos['short'] > 0:
                print(f"      {ticker}: {pos['short']} shares SHORT @ ${pos['short_cost_basis']:.2f}")
    else:
        print("   No open positions")
    
    print("   ✅ Portfolio snapshot fetched successfully\n")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Verify portfolio structure
print("5️⃣  Verifying portfolio data structure...")
try:
    required_keys = ["cash", "equity", "buying_power", "margin_requirement", "margin_used", "positions", "realized_gains"]
    missing_keys = [key for key in required_keys if key not in portfolio]
    
    if missing_keys:
        print(f"   ❌ FAILED: Missing keys: {missing_keys}")
        sys.exit(1)
    
    # Check positions structure
    for ticker in test_tickers:
        if ticker not in portfolio['positions']:
            print(f"   ❌ FAILED: Ticker {ticker} not in positions")
            sys.exit(1)
        
        pos = portfolio['positions'][ticker]
        required_pos_keys = ["long", "short", "long_cost_basis", "short_cost_basis", "short_margin_used"]
        missing_pos_keys = [key for key in required_pos_keys if key not in pos]
        
        if missing_pos_keys:
            print(f"   ❌ FAILED: Position {ticker} missing keys: {missing_pos_keys}")
            sys.exit(1)
    
    print("   ✅ Portfolio structure is valid\n")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    sys.exit(1)

# Summary
print("=" * 60)
print("✅ ALL TESTS PASSED")
print("=" * 60)
print("\n🎉 Your Alpaca Paper Trading API is ready to use!")
print("\nNext steps:")
print("  1. Test queue worker: python tests\\test_queue_worker.py")
print("  2. Send test message: python .\\infra\\test_queue_python.py --tickers AAPL")
print("  3. Execute paper trade: python .\\infra\\test_queue_python.py --tickers NVDA --trade-mode paper")
print()
