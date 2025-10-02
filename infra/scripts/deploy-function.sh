#!/bin/bash
# Deploy Azure Function App
# This script packages and deploys the market monitoring function

set -e

FUNCTION_APP_NAME="${1:-hedgefund-monitor}"
RESOURCE_GROUP="${2:-rg-ai-hedge-fund}"

echo "🚀 Deploying Azure Function: $FUNCTION_APP_NAME"

# Get workspace root (two levels up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MONITORING_DIR="$WORKSPACE_ROOT/infra/monitoring"
SRC_DIR="$WORKSPACE_ROOT/src"
TEMP_DIR=$(mktemp -d)

echo "📁 Workspace root: $WORKSPACE_ROOT"
echo "📁 Monitoring dir: $MONITORING_DIR"
echo "📁 Temp dir: $TEMP_DIR"

cleanup() {
    echo "🧹 Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
    [ -f "$ZIP_FILE" ] && rm -f "$ZIP_FILE"
}
trap cleanup EXIT

echo ""
echo "📦 Creating deployment package..."

# Copy function app files
echo "  ✓ Copying function app files..."
cp -r "$MONITORING_DIR"/* "$TEMP_DIR/"
rm -rf "$TEMP_DIR/.venv" "$TEMP_DIR/__pycache__" "$TEMP_DIR/.vscode" "$TEMP_DIR/local.settings.json" "$TEMP_DIR"/*.md 2>/dev/null || true

# Copy necessary src modules
echo "  ✓ Copying src dependencies..."
mkdir -p "$TEMP_DIR/src/data" "$TEMP_DIR/src/tools"

cp "$SRC_DIR/__init__.py" "$TEMP_DIR/src/__init__.py" 2>/dev/null || touch "$TEMP_DIR/src/__init__.py"
cp "$SRC_DIR/data/__init__.py" "$TEMP_DIR/src/data/__init__.py" 2>/dev/null || touch "$TEMP_DIR/src/data/__init__.py"
cp "$SRC_DIR/data/models.py" "$TEMP_DIR/src/data/models.py"
cp "$SRC_DIR/data/cache.py" "$TEMP_DIR/src/data/cache.py"
cp "$SRC_DIR/tools/__init__.py" "$TEMP_DIR/src/tools/__init__.py" 2>/dev/null || touch "$TEMP_DIR/src/tools/__init__.py"
cp "$SRC_DIR/tools/api.py" "$TEMP_DIR/src/tools/api.py"

# Create deployment package
ZIP_FILE=$(mktemp).zip
echo "  ✓ Creating ZIP archive..."
cd "$TEMP_DIR"
zip -r "$ZIP_FILE" . -q
cd - > /dev/null

FILE_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo "  ✓ Package created: $ZIP_FILE"
echo "    Size: $FILE_SIZE"

# Deploy to Azure
echo ""
echo "☁️  Deploying to Azure..."
echo "  Function App: $FUNCTION_APP_NAME"
echo "  Resource Group: $RESOURCE_GROUP"

az functionapp deployment source config-zip \
    --resource-group "$RESOURCE_GROUP" \
    --name "$FUNCTION_APP_NAME" \
    --src "$ZIP_FILE" \
    --build-remote true \
    --timeout 600

echo ""
echo "✅ Deployment successful!"

echo ""
echo "📊 Checking function status..."

# Get function app details
FUNCTION_STATE=$(az functionapp show \
    --name "$FUNCTION_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "state" -o tsv)

FUNCTION_HOSTNAME=$(az functionapp show \
    --name "$FUNCTION_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "defaultHostName" -o tsv)

FUNCTION_ID=$(az functionapp show \
    --name "$FUNCTION_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "id" -o tsv)

echo "  State: $FUNCTION_STATE"
echo "  Default hostname: $FUNCTION_HOSTNAME"
echo ""
echo "🔗 View in Azure Portal:"
echo "  https://portal.azure.com/#resource$FUNCTION_ID"

echo ""
echo "💡 To view logs, run:"
echo "  az functionapp log tail --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP"

echo ""
echo "✨ Done!"
