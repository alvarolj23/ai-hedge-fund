import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/lib/api';
import Card, { StatCard } from '@/components/Card';
import { formatCurrency, formatPercent } from '@/lib/utils';
import { DollarSign, TrendingUp, Wallet, CreditCard } from 'lucide-react';

export default function PortfolioPage() {
  const { data: portfolio, isLoading, error } = useQuery({
    queryKey: ['portfolio'],
    queryFn: dashboardApi.getPortfolioSummary,
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading portfolio...</div>
      </div>
    );
  }

  if (error || portfolio?.error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-400">
          Error loading portfolio: {portfolio?.error || (error as Error).message}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Portfolio Overview</h1>
        <p className="text-slate-400 mt-1">
          Last updated: {portfolio?.last_updated ? new Date(portfolio.last_updated).toLocaleString() : 'Never'}
        </p>
      </div>

      {/* Account Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          label="Total Value"
          value={formatCurrency(portfolio?.total_value || 0)}
          icon={<DollarSign className="h-8 w-8" />}
        />
        <StatCard
          label="Cash Available"
          value={formatCurrency(portfolio?.cash || 0)}
          icon={<Wallet className="h-8 w-8" />}
        />
        <StatCard
          label="Positions Value"
          value={formatCurrency(portfolio?.positions_value || 0)}
          icon={<TrendingUp className="h-8 w-8" />}
        />
        <StatCard
          label="Buying Power"
          value={formatCurrency(portfolio?.buying_power || 0)}
          icon={<CreditCard className="h-8 w-8" />}
        />
      </div>

      {/* Current Positions Table */}
      <Card title="Current Positions" subtitle={`${portfolio?.positions?.length || 0} active positions`}>
        {portfolio?.positions && portfolio.positions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Ticker</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Side</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Quantity</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Avg Cost</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Current</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Market Value</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">P&L</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">P&L %</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.positions.map((position) => {
                  const isProfit = position.unrealized_pl >= 0;
                  return (
                    <tr key={position.ticker} className="border-b border-slate-700/50">
                      <td className="py-3 px-4">
                        <span className="font-semibold text-white">{position.ticker}</span>
                      </td>
                      <td className="text-right py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                            position.side === 'long'
                              ? 'bg-green-900/30 text-green-400'
                              : 'bg-red-900/30 text-red-400'
                          }`}
                        >
                          {position.side.toUpperCase()}
                        </span>
                      </td>
                      <td className="text-right py-3 px-4 text-slate-300">
                        {position.quantity.toLocaleString()}
                      </td>
                      <td className="text-right py-3 px-4 text-slate-300">
                        {formatCurrency(position.avg_cost)}
                      </td>
                      <td className="text-right py-3 px-4 text-slate-300">
                        {formatCurrency(position.current_price)}
                      </td>
                      <td className="text-right py-3 px-4 text-slate-300">
                        {formatCurrency(position.market_value)}
                      </td>
                      <td className={`text-right py-3 px-4 font-medium ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                        {isProfit && '+'}
                        {formatCurrency(position.unrealized_pl)}
                      </td>
                      <td className={`text-right py-3 px-4 font-medium ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                        {isProfit && '+'}
                        {formatPercent(position.unrealized_pl_percent)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-slate-400">
            <p>No active positions</p>
            <p className="text-sm mt-2">Your portfolio is currently 100% cash</p>
          </div>
        )}
      </Card>
    </div>
  );
}
