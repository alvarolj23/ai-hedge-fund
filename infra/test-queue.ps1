# Test script to send a message to the Azure Storage Queue
# This will trigger the container app job if it's configured to listen to the queue

param(
    [Parameter(HelpMessage="Name of the Azure Storage Account")]
    [string]$StorageAccountName = 'hedgefundstzz4vjinf23chg',

    [Parameter(HelpMessage="Name of the resource group containing the storage account")]
    [string]$ResourceGroupName = 'rg-ai-hedge-fund',

    [Parameter(HelpMessage="Name of the queue to send the message to")]
    [string]$QueueName = 'analysis-requests',

    [Parameter(HelpMessage="Ticker symbols to analyze (comma-separated)")]
    [string]$Tickers = 'AAPL',

    [Parameter(HelpMessage="Number of days to look back for analysis")]
    [int]$LookbackDays = 30
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

# Build the message payload matching the queue_worker.py expected format
$now = (Get-Date).ToUniversalTime()
$endDate = $now.ToString("yyyy-MM-ddTHH:mm:ss+00:00")
$startDate = $now.AddDays(-$LookbackDays).ToString("yyyy-MM-ddTHH:mm:ss+00:00")

# Parse tickers into an array
$tickerArray = $Tickers -split ',' | ForEach-Object { $_.Trim() }

$messagePayload = @{
    tickers = $tickerArray
    analysis_window = @{
        start = $startDate
        end = $endDate
    }
    overrides = @{
        show_reasoning = $true
    }
    triggered_at = $now.ToString("yyyy-MM-ddTHH:mm:ss+00:00")
    source = "manual_test"
} | ConvertTo-Json -Compress

Write-Host "Message payload:"
Write-Host $messagePayload
Write-Host ""

# Base64 encode the message (required for Azure Queue Storage with TextBase64EncodePolicy)
$messageBytes = [System.Text.Encoding]::UTF8.GetBytes($messagePayload)
$base64Message = [Convert]::ToBase64String($messageBytes)

# Send the message to the queue
Write-Host "Sending message to queue '$QueueName' in storage account '$StorageAccountName'..."
az storage message put `
    --queue-name $QueueName `
    --account-name $StorageAccountName `
    --account-key $keyJson `
    --content $base64Message

if ($LASTEXITCODE -eq 0) {
    Write-Host "Message sent successfully. The container app job should trigger shortly."
} else {
    Write-Host "Failed to send message. Check your permissions and storage account details."
}