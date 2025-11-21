import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/lib/api';
import Card, { StatCard } from '@/components/Card';
import { formatPercent, formatCurrency } from '@/lib/utils';
import { TrendingUp, Target, DollarSign, Award } from 'lucide-react';

export default function AnalyticsPage() {
  const [period, setPeriod] = useState(30);

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['metrics', period],
    queryFn: () => dashboardApi.getPerformanceMetrics(period),
  });

  const { data: agentPerf, isLoading: agentLoading } = useQuery({
    queryKey: ['agent-performance', period],
    queryFn: () => dashboardApi.getAgentPerformance(period),
  });

  const isLoading = metricsLoading || agentLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading analytics...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Trading Analytics</h1>
          <p className="text-slate-400 mt-1">Performance metrics and insights</p>
        </div>
        <select
          value={period}
          onChange={(e) => setPeriod(Number(e.target.value))}
          className="bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last year</option>
        </select>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          label="Total Trades"
          value={metrics?.total_trades || 0}
          icon={<Target className="h-8 w-8" />}
        />
        <StatCard
          label="Win Rate"
          value={`${metrics?.win_rate?.toFixed(1) || 0}%`}
          change={metrics?.win_rate}
          icon={<Award className="h-8 w-8" />}
        />
        <StatCard
          label="Total Return"
          value={formatPercent(metrics?.total_return || 0)}
          change={metrics?.total_return}
          icon={<TrendingUp className="h-8 w-8" />}
        />
        <StatCard
          label="Profit Factor"
          value={metrics?.profit_factor?.toFixed(2) || '0.00'}
          icon={<DollarSign className="h-8 w-8" />}
        />
      </div>

      {/* Detailed Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="Win/Loss Statistics">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Winning Trades</span>
              <span className="text-green-400 font-semibold">{metrics?.wins || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Losing Trades</span>
              <span className="text-red-400 font-semibold">{metrics?.losses || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Average Win</span>
              <span className="text-green-400 font-semibold">{formatCurrency(metrics?.avg_win || 0)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Average Loss</span>
              <span className="text-red-400 font-semibold">{formatCurrency(metrics?.avg_loss || 0)}</span>
            </div>
          </div>
        </Card>

        <Card title="Risk Metrics">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Sharpe Ratio</span>
              <span className="text-white font-semibold">{metrics?.sharpe_ratio?.toFixed(2) || 'N/A'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Max Drawdown</span>
              <span className="text-red-400 font-semibold">{formatPercent(metrics?.max_drawdown || 0)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Period</span>
              <span className="text-white font-semibold">{period} days</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Agent Performance Leaderboard */}
      <Card
        title="🤖 Agent Performance Leaderboard"
        subtitle={`${agentPerf?.total_agents || 0} agents analyzed`}
      >
        {agentPerf?.agents && agentPerf.agents.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Agent</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Signals</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Avg Confidence</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Buy</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Sell</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Hold</th>
                </tr>
              </thead>
              <tbody>
                {agentPerf.agents.slice(0, 10).map((agent, index) => (
                  <tr key={agent.agent_name} className="border-b border-slate-700/50">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <span className="text-slate-400 text-sm">#{index + 1}</span>
                        <span className="font-semibold text-white">{agent.agent_name}</span>
                      </div>
                    </td>
                    <td className="text-right py-3 px-4 text-slate-300">{agent.total_signals}</td>
                    <td className="text-right py-3 px-4">
                      <span className="text-blue-400 font-medium">{agent.avg_confidence.toFixed(1)}%</span>
                    </td>
                    <td className="text-right py-3 px-4 text-green-400">{agent.buy_signals}</td>
                    <td className="text-right py-3 px-4 text-red-400">{agent.sell_signals}</td>
                    <td className="text-right py-3 px-4 text-slate-400">{agent.hold_signals}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-slate-400">
            <p>No agent data available for the selected period</p>
          </div>
        )}
      </Card>
    </div>
  );
}
