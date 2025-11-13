"""
Test script to verify Azure OpenAI configuration and connectivity.

This script tests:
1. Required environment variables are set (API key, endpoint, deployment name)
2. Azure OpenAI endpoint is accessible
3. Model can generate responses
4. API credentials are valid

Usage:
    python tests/test_azure_openai.py
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.llm.models import get_model, ModelProvider


def test_environment_variables():
    """Test that all required Azure OpenAI environment variables are set."""
    print("\n" + "=" * 60)
    print("🔍 Testing Environment Variables")
    print("=" * 60)
    
    required_vars = {
        "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY"),
        "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "AZURE_OPENAI_DEPLOYMENT_NAME": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    }
    
    all_set = True
    for var_name, var_value in required_vars.items():
        if var_value:
            # Show partial value for security
            masked_value = var_value[:8] + "..." if len(var_value) > 8 else "***"
            print(f"✅ {var_name}: {masked_value}")
        else:
            print(f"❌ {var_name}: Not set")
            all_set = False
    
    if not all_set:
        print("\n❌ Some environment variables are missing!")
        print("\nPlease add the following to your .env file:")
        print("AZURE_OPENAI_API_KEY=your_api_key_here")
        print("AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/")
        print("AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name")
        return False
    
    print("\n✅ All required environment variables are set!")
    return True


def test_azure_openai_connection():
    """Test Azure OpenAI connection and model response."""
    print("\n" + "=" * 60)
    print("🤖 Testing Azure OpenAI Connection")
    print("=" * 60)
    
    try:
        # Get the model
        print("\n📡 Initializing Azure OpenAI client...")
        model = get_model(
            model_name="",  # Not used for Azure, deployment name is in env
            model_provider=ModelProvider.AZURE_OPENAI
        )
        print("✅ Client initialized successfully!")
        
        # Test with a simple prompt
        print("\n💬 Sending test message to Azure OpenAI...")
        test_prompt = "Reply with just the word 'SUCCESS' if you can read this message."
        
        response = model.invoke(test_prompt)
        response_text = response.content
        
        print(f"\n📨 Response received:")
        print(f"   {response_text}")
        
        # Validate response
        if response_text and len(response_text) > 0:
            print("\n✅ Azure OpenAI is working correctly!")
            print(f"   Model: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')}")
            print(f"   Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
            return True
        else:
            print("\n⚠️  Received empty response from Azure OpenAI")
            return False
            
    except Exception as e:
        print(f"\n❌ Error connecting to Azure OpenAI:")
        print(f"   {type(e).__name__}: {str(e)}")
        print("\nPossible issues:")
        print("- Check that your API key is valid")
        print("- Verify the endpoint URL is correct")
        print("- Ensure the deployment name matches your Azure OpenAI deployment")
        print("- Check that your Azure OpenAI resource is active")
        return False


def test_azure_openai_structured_output():
    """Test Azure OpenAI with a more complex prompt."""
    print("\n" + "=" * 60)
    print("🧪 Testing Azure OpenAI with Complex Prompt")
    print("=" * 60)
    
    try:
        model = get_model(
            model_name="",
            model_provider=ModelProvider.AZURE_OPENAI
        )
        
        print("\n💬 Sending complex prompt...")
        test_prompt = """Analyze the following statement and respond with a brief sentiment analysis:
        
"The stock market showed strong performance today with major indices reaching new highs."

Provide a one-sentence analysis."""
        
        response = model.invoke(test_prompt)
        response_text = response.content
        
        print(f"\n📨 Response:")
        print(f"   {response_text}")
        
        if response_text and len(response_text) > 10:
            print("\n✅ Complex prompt handling works correctly!")
            return True
        else:
            print("\n⚠️  Response seems incomplete")
            return False
            
    except Exception as e:
        print(f"\n❌ Error with complex prompt:")
        print(f"   {type(e).__name__}: {str(e)}")
        return False


def main():
    """Run all Azure OpenAI tests."""
    print("\n" + "=" * 60)
    print("🧪 AZURE OPENAI CONNECTION TEST")
    print("=" * 60)
    
    # Test environment variables
    if not test_environment_variables():
        print("\n" + "=" * 60)
        print("❌ TEST FAILED: Environment variables not configured")
        print("=" * 60)
        sys.exit(1)
    
    # Test basic connection
    connection_success = test_azure_openai_connection()
    
    if not connection_success:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED: Could not connect to Azure OpenAI")
        print("=" * 60)
        sys.exit(1)
    
    # Test complex prompt
    complex_success = test_azure_openai_structured_output()
    
    # Final summary
    print("\n" + "=" * 60)
    if connection_success and complex_success:
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n🎉 Azure OpenAI is configured correctly and working!")
        print("   You can now use Azure OpenAI models in your application.")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("=" * 60)
        print("\n   Basic connection works, but complex prompts may have issues.")
    print()
    

if __name__ == "__main__":
    main()
