#!/bin/bash

# Deploy AI Hedge Fund Dashboard to Azure Static Web Apps
# Usage: ./deploy.sh [resource-group] [app-name]

set -e

RESOURCE_GROUP="${1:-rg-ai-hedge-fund-prod}"
APP_NAME="${2:-aihedgefund-dashboard}"

echo "🚀 Deploying AI Hedge Fund Dashboard..."
echo "   Resource Group: $RESOURCE_GROUP"
echo "   App Name: $APP_NAME"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first:"
    echo "   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run: az login"
    exit 1
fi

# Build the dashboard
echo "📦 Building dashboard..."
npm run build

if [ ! -d "dist" ]; then
    echo "❌ Build failed - dist directory not found"
    exit 1
fi

echo "✅ Build complete"
echo ""

# Check if Static Web App exists
if az staticwebapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo "📤 Deploying to existing Static Web App..."
    az staticwebapp deploy \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --source ./dist
else
    echo "🆕 Creating new Static Web App..."
    az staticwebapp create \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location westeurope \
        --sku Free \
        --source ./dist
fi

echo ""
echo "✅ Deployment complete!"
echo ""

# Get the URL
URL=$(az staticwebapp show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "defaultHostname" -o tsv)

echo "🌐 Dashboard URL: https://$URL"
echo ""
echo "Next steps:"
echo "1. Configure environment variables in Azure Portal if needed"
echo "2. Set up custom domain (optional)"
echo "3. Configure GitHub Actions for automated deployments"
