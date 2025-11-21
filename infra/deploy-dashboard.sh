#!/bin/bash

###############################################################################
# Deploy AI Hedge Fund Dashboard to Azure Static Web Apps
#
# This script deploys the React dashboard to Azure Static Web Apps (FREE tier).
# It handles building, creating/updating the Static Web App, and configuration.
#
# Usage:
#   ./deploy-dashboard.sh [resource-group] [app-name] [location] [api-url]
#
# Examples:
#   ./deploy-dashboard.sh
#   ./deploy-dashboard.sh my-rg my-dashboard westeurope https://my-api.azurecontainerapps.io
###############################################################################

set -e

# Default configuration
RESOURCE_GROUP="${1:-rg-ai-hedge-fund-prod}"
APP_NAME="${2:-aihedgefund-dashboard}"
LOCATION="${3:-westeurope}"
API_URL="${4:-https://aihedgefund-api.wittysand-2cb74b22.westeurope.azurecontainerapps.io}"

echo ""
echo "================================================================"
echo "AI HEDGE FUND - Dashboard Deployment"
echo "================================================================"
echo ""
echo "Configuration:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  App Name:       $APP_NAME"
echo "  Location:       $LOCATION"
echo "  API URL:        $API_URL"
echo ""

# Check Azure CLI
echo "Checking Azure CLI..."
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Please install it from:"
    echo "   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi
echo "✅ Azure CLI found"

# Check if logged in
echo "Checking Azure login..."
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run: az login"
    exit 1
fi
echo "✅ Logged in to Azure"

# Navigate to dashboard folder
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD_PATH="$SCRIPT_DIR/../dashboard"

if [ ! -d "$DASHBOARD_PATH" ]; then
    echo "❌ Dashboard folder not found at: $DASHBOARD_PATH"
    exit 1
fi

cd "$DASHBOARD_PATH"

# Check Node.js
echo ""
echo "Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install it from https://nodejs.org"
    exit 1
fi
NODE_VERSION=$(node --version)
echo "✅ Node.js found: $NODE_VERSION"

# Install dependencies
echo ""
echo "Installing dependencies..."
npm install
echo "✅ Dependencies installed"

# Create .env file
echo ""
echo "Creating .env file..."
echo "VITE_API_URL=$API_URL" > .env
echo "✅ .env file created"

# Build dashboard
echo ""
echo "Building dashboard..."
npm run build
echo "✅ Build complete"

# Check if build output exists
if [ ! -d "dist" ]; then
    echo "❌ Build failed - dist directory not found"
    exit 1
fi

# Check if Static Web App exists
echo ""
echo "Checking if Static Web App exists..."
if az staticwebapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo "✅ Static Web App already exists"
    echo ""
    echo "================================================================"
    echo "DEPLOYMENT INSTRUCTIONS"
    echo "================================================================"
    echo ""
    echo "The dashboard has been built successfully!"
    echo "Build output is in: ./dist"
    echo ""
    echo "To deploy, choose one of these options:"
    echo ""
    echo "OPTION 1: GitHub Actions (Recommended)"
    echo "  1. Commit and push your changes to GitHub"
    echo "  2. GitHub Actions will automatically deploy"
    echo ""
    echo "OPTION 2: Azure Portal"
    echo "  1. Go to Azure Portal"
    echo "  2. Navigate to: $RESOURCE_GROUP -> $APP_NAME"
    echo "  3. Download deployment token"
    echo "  4. Install SWA CLI: npm install -g @azure/static-web-apps-cli"
    echo "  5. Run: swa deploy ./dist --deployment-token <token>"
    echo ""
    echo "OPTION 3: Azure CLI with SWA Extension"
    echo "  az extension add --name staticwebapp"
    echo "  az staticwebapp deploy \\"
    echo "    --name $APP_NAME \\"
    echo "    --resource-group $RESOURCE_GROUP \\"
    echo "    --source ./dist"
    echo ""
else
    echo "Creating new Static Web App..."

    az staticwebapp create \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --sku Free \
        --source ./dist

    echo "✅ Static Web App created"
fi

# Configure environment variables
echo ""
echo "Configuring environment variables..."

if az staticwebapp appsettings set \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --setting-names VITE_API_URL="$API_URL" &> /dev/null; then
    echo "✅ Environment variables configured"
else
    echo "⚠️  Could not set environment variables automatically"
    echo "   Please set manually in Azure Portal:"
    echo "   Configuration -> Application settings -> VITE_API_URL = $API_URL"
fi

# Get dashboard URL
echo ""
echo "Getting dashboard URL..."
DASHBOARD_URL=$(az staticwebapp show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "defaultHostname" \
    -o tsv)

if [ -n "$DASHBOARD_URL" ]; then
    echo ""
    echo "================================================================"
    echo "✅ DEPLOYMENT COMPLETE!"
    echo "================================================================"
    echo ""
    echo "🌐 Dashboard URL: https://$DASHBOARD_URL"
    echo ""
    echo "Next steps:"
    echo "  1. Visit the dashboard URL above"
    echo "  2. Test all pages (Portfolio, Analytics, Trades, Monitoring, Config)"
    echo "  3. If using GitHub Actions, push your changes to auto-deploy"
    echo ""
fi

echo ""
echo "Script completed at: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
