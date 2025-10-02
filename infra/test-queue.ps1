# Test script to send a message to the Azure Storage Queue
# This will trigger the container app job if it's configured to listen to the queue

param(
    [Parameter(HelpMessage="Name of the Azure Storage Account")]
    [string]$StorageAccountName = 'hedgefundstzz4vjinf23chg',

    [Parameter(HelpMessage="Name of the resource group containing the storage account")]
    [string]$ResourceGroupName = 'rg-ai-hedge-fund',

    [Parameter(HelpMessage="Name of the queue to send the message to")]
    [string]$QueueName = 'analysis-requests',

    [Parameter(HelpMessage="JSON message content to send to the queue")]
    [string]$Message = '{"action": "analyze", "symbol": "AAPL", "timestamp": "' + (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ") + '"}'
)

# Ensure Azure CLI is logged in
Write-Host "Ensuring Azure CLI is logged in..."
az account show --output none
if ($LASTEXITCODE -ne 0) {
    Write-Host "Please log in to Azure CLI first using 'az login'"
    exit 1
}

# Get the storage account key
Write-Host "Retrieving storage account key..."
$keyJson = az storage account keys list --account-name $StorageAccountName --resource-group $ResourceGroupName --query "[0].value" -o tsv
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to retrieve storage account key. Check your permissions."
    exit 1
}

# Send the message to the queue
Write-Host "Sending message to queue '$QueueName' in storage account '$StorageAccountName'..."
az storage message put `
    --queue-name $QueueName `
    --account-name $StorageAccountName `
    --account-key $keyJson `
    --content $Message

if ($LASTEXITCODE -eq 0) {
    Write-Host "Message sent successfully. The container app job should trigger shortly."
} else {
    Write-Host "Failed to send message. Check your permissions and storage account details."
}