"""
Test script for AI Hedge Fund Dashboard API endpoints.

This script tests all dashboard and configuration API endpoints
without requiring external tools like jq or curl.
"""
import requests
import json
from typing import Dict, Any
from datetime import datetime


class DashboardTester:
    """Test all dashboard API endpoints."""

    def __init__(self, api_url: str):
        """Initialize tester with API URL."""
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
        self.results = []

    def test_endpoint(self, name: str, method: str, path: str, params: Dict = None) -> Dict[str, Any]:
        """Test a single endpoint and record results."""
        url = f"{self.api_url}{path}"

        print(f"\n{'='*70}")
        print(f"Testing: {name}")
        print(f"URL: {url}")
        if params:
            print(f"Params: {params}")
        print(f"{'='*70}")

        try:
            if method == "GET":
                response = self.session.get(url, params=params, timeout=10)
            elif method == "PUT":
                response = self.session.put(url, json=params, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            # Parse response
            try:
                data = response.json()
            except:
                data = {"raw_response": response.text}

            # Print results
            status_emoji = "✅" if response.status_code == 200 else "❌"
            print(f"{status_emoji} Status Code: {response.status_code}")
            print(f"\nResponse:")
            print(json.dumps(data, indent=2))

            result = {
                "name": name,
                "url": url,
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }

            self.results.append(result)
            return result

        except requests.exceptions.Timeout:
            print("❌ Request timed out (>10 seconds)")
            result = {
                "name": name,
                "url": url,
                "error": "Timeout",
                "success": False
            }
            self.results.append(result)
            return result

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            result = {
                "name": name,
                "url": url,
                "error": str(e),
                "success": False
            }
            self.results.append(result)
            return result

    def run_all_tests(self):
        """Run all dashboard API tests."""
        print(f"\n{'#'*70}")
        print("AI HEDGE FUND DASHBOARD API TESTS")
        print(f"{'#'*70}")
        print(f"Testing API: {self.api_url}")
        print(f"Started at: {datetime.utcnow().isoformat()}")

        # Test 1: Health check
        self.test_endpoint(
            "Health Check",
            "GET",
            "/"
        )

        # Test 2: Portfolio summary
        self.test_endpoint(
            "Portfolio Summary",
            "GET",
            "/dashboard/portfolio"
        )

        # Test 3: System health
        self.test_endpoint(
            "System Health",
            "GET",
            "/dashboard/system-health"
        )

        # Test 4: Performance metrics (30 days)
        self.test_endpoint(
            "Performance Metrics (30 days)",
            "GET",
            "/dashboard/metrics",
            params={"days": 30}
        )

        # Test 5: Trade history
        self.test_endpoint(
            "Trade History",
            "GET",
            "/dashboard/trades",
            params={"limit": 10}
        )

        # Test 6: Agent performance
        self.test_endpoint(
            "Agent Performance",
            "GET",
            "/dashboard/agent-performance",
            params={"days": 30}
        )

        # Test 7: Portfolio history
        self.test_endpoint(
            "Portfolio History",
            "GET",
            "/dashboard/portfolio-history",
            params={"days": 30}
        )

        # Test 8: Monitor configuration
        self.test_endpoint(
            "Monitor Configuration",
            "GET",
            "/config/monitor"
        )

        # Test 9: Trading configuration
        self.test_endpoint(
            "Trading Configuration",
            "GET",
            "/config/trading"
        )

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test results summary."""
        print(f"\n{'#'*70}")
        print("TEST SUMMARY")
        print(f"{'#'*70}")

        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("success"))
        failed = total - passed

        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"\nSuccess Rate: {(passed/total*100):.1f}%")

        if failed > 0:
            print(f"\n{'='*70}")
            print("FAILED TESTS:")
            print(f"{'='*70}")
            for result in self.results:
                if not result.get("success"):
                    print(f"\n❌ {result['name']}")
                    print(f"   URL: {result['url']}")
                    if "error" in result:
                        print(f"   Error: {result['error']}")
                    elif "data" in result and "error" in result["data"]:
                        print(f"   API Error: {result['data']['error']}")

        print(f"\n{'='*70}")
        print("RECOMMENDATIONS:")
        print(f"{'='*70}")

        # Analyze failures and provide recommendations
        for result in self.results:
            if not result.get("success"):
                if "portfolio" in result["name"].lower():
                    print("\n📌 Portfolio endpoint failed:")
                    print("   - Check that APCA_API_KEY_ID and APCA_API_SECRET_KEY are set")
                    print("   - Verify Alpaca credentials are valid")
                    print("   - Ensure the Container App has these environment variables")

                elif "cosmos" in str(result.get("data", {})):
                    print("\n📌 Cosmos DB related endpoint failed:")
                    print("   - Check that COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DATABASE are set")
                    print("   - Verify Cosmos DB is accessible from the Container App")

                elif "404" in str(result.get("status_code")):
                    print("\n📌 Endpoint not found (404):")
                    print("   - The backend API needs to be redeployed")
                    print("   - Run: az containerapp update --name aihedgefund-api ...")

        print(f"\n{'='*70}")
        print(f"Tests completed at: {datetime.utcnow().isoformat()}")
        print(f"{'='*70}\n")


def main():
    """Main entry point."""
    import sys

    # Get API URL from command line or use default
    if len(sys.argv) > 1:
        api_url = sys.argv[1]
    else:
        api_url = "https://aihedgefund-api.wittysand-2cb74b22.westeurope.azurecontainerapps.io"

    # Run tests
    tester = DashboardTester(api_url)
    tester.run_all_tests()

    # Exit with appropriate code
    total = len(tester.results)
    passed = sum(1 for r in tester.results if r.get("success"))

    if passed == total:
        sys.exit(0)  # All tests passed
    else:
        sys.exit(1)  # Some tests failed


if __name__ == "__main__":
    main()
