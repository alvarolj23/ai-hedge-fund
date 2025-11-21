import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { configApi, MarketMonitorConfig, TradingConfig } from '@/lib/api';
import Card from '@/components/Card';
import { Save, AlertCircle, CheckCircle, Copy } from 'lucide-react';

export default function ConfigPage() {
  const queryClient = useQueryClient();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [azureCommand, setAzureCommand] = useState<string | null>(null);

  // Market Monitor Config
  const { data: monitorConfig, isLoading: monitorLoading } = useQuery({
    queryKey: ['monitor-config'],
    queryFn: configApi.getMonitorConfig,
  });

  const [watchlist, setWatchlist] = useState('');
  const [priceThreshold, setPriceThreshold] = useState(2.0);
  const [volumeMultiplier, setVolumeMultiplier] = useState(1.5);
  const [cooldown, setCooldown] = useState(1800);

  // Set initial values when data loads
  useState(() => {
    if (monitorConfig) {
      setWatchlist(monitorConfig.watchlist.join(', '));
      setPriceThreshold(monitorConfig.price_breakout_threshold * 100);
      setVolumeMultiplier(monitorConfig.volume_spike_multiplier);
      setCooldown(monitorConfig.cooldown_seconds);
    }
  });

  // Trading Config
  const { data: tradingConfig, isLoading: tradingLoading } = useQuery({
    queryKey: ['trading-config'],
    queryFn: configApi.getTradingConfig,
  });

  const [confidenceThreshold, setConfidenceThreshold] = useState(70);
  const [tradeMode, setTradeMode] = useState('paper');
  const [dryRun, setDryRun] = useState(false);

  useState(() => {
    if (tradingConfig) {
      setConfidenceThreshold(tradingConfig.confidence_threshold);
      setTradeMode(tradingConfig.trade_mode);
      setDryRun(tradingConfig.dry_run);
    }
  });

  // Update monitor config mutation
  const updateMonitorMutation = useMutation({
    mutationFn: (config: MarketMonitorConfig) => configApi.updateMonitorConfig(config),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['monitor-config'] });
      setSuccessMessage('Configuration validated successfully!');
      setAzureCommand(data.azure_cli_command);
      setTimeout(() => setSuccessMessage(null), 5000);
    },
  });

  // Update trading config mutation
  const updateTradingMutation = useMutation({
    mutationFn: (config: TradingConfig) => configApi.updateTradingConfig(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trading-config'] });
      setSuccessMessage('Trading configuration validated!');
      setTimeout(() => setSuccessMessage(null), 5000);
    },
  });

  const handleSaveMonitorConfig = () => {
    const tickers = watchlist.split(',').map((t) => t.trim().toUpperCase()).filter(Boolean);
    updateMonitorMutation.mutate({
      watchlist: tickers,
      price_breakout_threshold: priceThreshold / 100,
      volume_spike_multiplier: volumeMultiplier,
      cooldown_seconds: cooldown,
      volume_lookback_days: 10,
    });
  };

  const handleSaveTradingConfig = () => {
    updateTradingMutation.mutate({
      confidence_threshold: confidenceThreshold,
      trade_mode: tradeMode,
      dry_run: dryRun,
    });
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setSuccessMessage('Command copied to clipboard!');
    setTimeout(() => setSuccessMessage(null), 3000);
  };

  if (monitorLoading || tradingLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading configuration...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Configuration</h1>
        <p className="text-slate-400 mt-1">Manage system settings and parameters</p>
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className="flex items-center gap-3 p-4 bg-green-900/20 border border-green-900/30 rounded-lg">
          <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0" />
          <span className="text-green-400">{successMessage}</span>
        </div>
      )}

      {/* Market Monitor Configuration */}
      <Card title="⚙️ Market Monitor Settings" subtitle="Configure the Function App market monitoring parameters">
        <div className="space-y-6">
          {/* Watchlist */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Watchlist Tickers
              <span className="text-slate-500 ml-2">(comma-separated)</span>
            </label>
            <input
              type="text"
              value={watchlist}
              onChange={(e) => setWatchlist(e.target.value)}
              placeholder="AAPL, MSFT, NVDA, GOOGL, TSLA"
              className="w-full bg-slate-700 border border-slate-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Price Breakout Threshold */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Price Breakout Threshold: {priceThreshold.toFixed(1)}%
            </label>
            <input
              type="range"
              min="1"
              max="10"
              step="0.1"
              value={priceThreshold}
              onChange={(e) => setPriceThreshold(Number(e.target.value))}
              className="w-full"
            />
            <p className="text-xs text-slate-500 mt-1">
              Trigger analysis when price changes by this percentage
            </p>
          </div>

          {/* Volume Spike Multiplier */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Volume Spike Multiplier: {volumeMultiplier.toFixed(1)}x
            </label>
            <input
              type="range"
              min="1"
              max="5"
              step="0.1"
              value={volumeMultiplier}
              onChange={(e) => setVolumeMultiplier(Number(e.target.value))}
              className="w-full"
            />
            <p className="text-xs text-slate-500 mt-1">
              Trigger when volume exceeds average by this multiplier
            </p>
          </div>

          {/* Cooldown Period */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Cooldown Period: {Math.floor(cooldown / 60)} minutes
            </label>
            <input
              type="range"
              min="300"
              max="7200"
              step="300"
              value={cooldown}
              onChange={(e) => setCooldown(Number(e.target.value))}
              className="w-full"
            />
            <p className="text-xs text-slate-500 mt-1">
              Minimum time between analyses for the same ticker
            </p>
          </div>

          {/* Save Button */}
          <button
            onClick={handleSaveMonitorConfig}
            disabled={updateMonitorMutation.isPending}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white rounded-lg px-4 py-3 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            <Save className="h-5 w-5" />
            {updateMonitorMutation.isPending ? 'Validating...' : 'Validate Configuration'}
          </button>

          {/* Azure CLI Command */}
          {azureCommand && (
            <div className="mt-4 p-4 bg-slate-900 border border-slate-700 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-slate-300">Azure CLI Command</h4>
                <button
                  onClick={() => copyToClipboard(azureCommand)}
                  className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300"
                >
                  <Copy className="h-4 w-4" />
                  Copy
                </button>
              </div>
              <pre className="text-xs text-slate-400 overflow-x-auto whitespace-pre-wrap">
                {azureCommand}
              </pre>
              <p className="text-xs text-yellow-400 mt-3 flex items-start gap-2">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                Run this command in Azure CLI to apply the configuration to your Function App
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Trading Configuration */}
      <Card title="📊 Trading Settings" subtitle="Configure trading execution parameters">
        <div className="space-y-6">
          {/* Confidence Threshold */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Confidence Threshold: {confidenceThreshold}%
            </label>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
              className="w-full"
            />
            <p className="text-xs text-slate-500 mt-1">
              Minimum confidence required to execute trades
            </p>
          </div>

          {/* Trade Mode */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Trade Mode</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="paper"
                  checked={tradeMode === 'paper'}
                  onChange={(e) => setTradeMode(e.target.value)}
                  className="text-blue-600"
                />
                <span className="text-white">Paper Trading</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="analysis"
                  checked={tradeMode === 'analysis'}
                  onChange={(e) => setTradeMode(e.target.value)}
                  className="text-blue-600"
                />
                <span className="text-white">Analysis Only</span>
              </label>
            </div>
          </div>

          {/* Dry Run */}
          <div>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
                className="w-5 h-5 text-blue-600 rounded"
              />
              <div>
                <span className="text-white font-medium">Dry Run Mode</span>
                <p className="text-xs text-slate-500 mt-0.5">
                  Simulate trades without executing them in Alpaca
                </p>
              </div>
            </label>
          </div>

          {/* Save Button */}
          <button
            onClick={handleSaveTradingConfig}
            disabled={updateTradingMutation.isPending}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white rounded-lg px-4 py-3 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            <Save className="h-5 w-5" />
            {updateTradingMutation.isPending ? 'Validating...' : 'Validate Configuration'}
          </button>
        </div>
      </Card>

      {/* Info Box */}
      <div className="flex items-start gap-3 p-4 bg-blue-900/20 border border-blue-900/30 rounded-lg">
        <AlertCircle className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-blue-300">
          <p className="font-medium">Note about configuration changes:</p>
          <p className="mt-1">
            This dashboard validates your configuration settings but does not directly update Azure resources.
            To apply changes to your Function App or Container App Job, use the Azure CLI commands provided above
            or update the environment variables in the Azure Portal.
          </p>
        </div>
      </div>
    </div>
  );
}
