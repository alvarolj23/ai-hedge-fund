import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/lib/api';
import Card, { StatCard } from '@/components/Card';
import { CheckCircle, XCircle, AlertCircle, Activity } from 'lucide-react';

export default function MonitoringPage() {
  const { data: health, isLoading } = useQuery({
    queryKey: ['system-health'],
    queryFn: dashboardApi.getSystemHealth,
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-5 w-5 text-green-400" />;
      case 'degraded':
        return <AlertCircle className="h-5 w-5 text-yellow-400" />;
      case 'unhealthy':
        return <XCircle className="h-5 w-5 text-red-400" />;
      default:
        return <AlertCircle className="h-5 w-5 text-slate-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-400';
      case 'degraded':
        return 'text-yellow-400';
      case 'unhealthy':
        return 'text-red-400';
      default:
        return 'text-slate-400';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading system health...</div>
      </div>
    );
  }

  const overallStatus = health?.status || 'unknown';
  const components = health?.components || {};

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">System Monitoring</h1>
        <p className="text-slate-400 mt-1">Real-time system health and operational metrics</p>
      </div>

      {/* Overall Status */}
      <StatCard
        label="System Status"
        value={overallStatus.charAt(0).toUpperCase() + overallStatus.slice(1)}
        icon={<Activity className="h-8 w-8" />}
        className="bg-gradient-to-r from-slate-800 to-slate-700"
      />

      {/* Component Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Alpaca Status */}
        <Card title="Alpaca Paper Trading">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Status</span>
              <div className="flex items-center gap-2">
                {getStatusIcon(components.alpaca?.status || 'not_configured')}
                <span className={getStatusColor(components.alpaca?.status || 'not_configured')}>
                  {(components.alpaca?.status || 'not_configured').replace('_', ' ')}
                </span>
              </div>
            </div>
            {components.alpaca?.last_updated && (
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Last Updated</span>
                <span className="text-white text-sm">{new Date(components.alpaca.last_updated).toLocaleString()}</span>
              </div>
            )}
            {components.alpaca?.error && (
              <div className="mt-2 p-3 bg-red-900/20 border border-red-900/30 rounded-lg">
                <p className="text-red-400 text-sm">{components.alpaca.error}</p>
              </div>
            )}
          </div>
        </Card>

        {/* Cosmos DB Status */}
        <Card title="Cosmos DB">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Status</span>
              <div className="flex items-center gap-2">
                {getStatusIcon(components.cosmos_db?.status || 'not_configured')}
                <span className={getStatusColor(components.cosmos_db?.status || 'not_configured')}>
                  {(components.cosmos_db?.status || 'not_configured').replace('_', ' ')}
                </span>
              </div>
            </div>
            {components.cosmos_db?.error && (
              <div className="mt-2 p-3 bg-red-900/20 border border-red-900/30 rounded-lg">
                <p className="text-red-400 text-sm">{components.cosmos_db.error}</p>
              </div>
            )}
          </div>
        </Card>

        {/* Queue Status */}
        <Card title="Azure Storage Queue">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Status</span>
              <div className="flex items-center gap-2">
                {getStatusIcon(components.queue?.status || 'not_configured')}
                <span className={getStatusColor(components.queue?.status || 'not_configured')}>
                  {(components.queue?.status || 'not_configured').replace('_', ' ')}
                </span>
              </div>
            </div>
            {components.queue?.depth !== undefined && (
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Queue Depth</span>
                <span className="text-white font-semibold">{components.queue.depth} messages</span>
              </div>
            )}
            {components.queue?.error && (
              <div className="mt-2 p-3 bg-red-900/20 border border-red-900/30 rounded-lg">
                <p className="text-red-400 text-sm">{components.queue.error}</p>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* System Info */}
      <Card title="System Information">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-sm font-medium text-slate-400 mb-3">Deployed Components</h4>
            <ul className="space-y-2">
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-400" />
                <span className="text-white">Function App (Market Monitor)</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-400" />
                <span className="text-white">Container App Job (Queue Worker)</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-400" />
                <span className="text-white">Container App (API)</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-400" />
                <span className="text-white">Azure Storage Queue</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-400" />
                <span className="text-white">Cosmos DB</span>
              </li>
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-medium text-slate-400 mb-3">Integrations</h4>
            <ul className="space-y-2">
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-400" />
                <span className="text-white">Alpaca Paper Trading API</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-400" />
                <span className="text-white">LangSmith (LLM Tracking)</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-400" />
                <span className="text-white">Application Insights</span>
              </li>
            </ul>
          </div>
        </div>
      </Card>

      {/* Last Update Time */}
      <div className="text-center text-sm text-slate-500">
        Last checked: {health?.timestamp ? new Date(health.timestamp).toLocaleString() : 'Never'}
      </div>
    </div>
  );
}
