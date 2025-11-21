import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/lib/api';
import Card from '@/components/Card';
import { formatCurrency, formatDate } from '@/lib/utils';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export default function TradesPage() {
  const [page, setPage] = useState(0);
  const [ticker, setTicker] = useState('');
  const limit = 20;

  const { data: tradesData, isLoading } = useQuery({
    queryKey: ['trades', page, ticker],
    queryFn: () =>
      dashboardApi.getTradeHistory({
        limit,
        offset: page * limit,
        ticker: ticker || undefined,
      }),
  });

  const totalPages = tradesData?.total ? Math.ceil(tradesData.total / limit) : 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Trade History</h1>
          <p className="text-slate-400 mt-1">All executed trades from Alpaca Paper Trading</p>
        </div>
        <div className="flex items-center gap-4">
          <input
            type="text"
            placeholder="Filter by ticker..."
            value={ticker}
            onChange={(e) => {
              setTicker(e.target.value.toUpperCase());
              setPage(0);
            }}
            className="bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-slate-500"
          />
        </div>
      </div>

      {/* Trade Table */}
      <Card>
        {isLoading ? (
          <div className="text-center py-12 text-slate-400">Loading trades...</div>
        ) : tradesData?.trades && tradesData.trades.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Date</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Ticker</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Action</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Quantity</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Price</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Total</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Status</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {tradesData.trades.map((trade) => {
                    const isBuy = trade.action?.toLowerCase() === 'buy';
                    const total = trade.quantity * trade.price;

                    return (
                      <tr key={trade.id} className="border-b border-slate-700/50">
                        <td className="py-3 px-4 text-slate-300 text-sm">{formatDate(trade.timestamp)}</td>
                        <td className="py-3 px-4">
                          <span className="font-semibold text-white">{trade.ticker}</span>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                              isBuy ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
                            }`}
                          >
                            {trade.action?.toUpperCase()}
                          </span>
                        </td>
                        <td className="text-right py-3 px-4 text-slate-300">{trade.quantity.toLocaleString()}</td>
                        <td className="text-right py-3 px-4 text-slate-300">{formatCurrency(trade.price)}</td>
                        <td className="text-right py-3 px-4 text-white font-medium">{formatCurrency(total)}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                              trade.status === 'filled'
                                ? 'bg-blue-900/30 text-blue-400'
                                : 'bg-yellow-900/30 text-yellow-400'
                            }`}
                          >
                            {trade.status}
                          </span>
                        </td>
                        <td className="text-right py-3 px-4 text-slate-300">
                          {trade.confidence ? `${trade.confidence}%` : 'N/A'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between mt-6 pt-6 border-t border-slate-700">
              <div className="text-sm text-slate-400">
                Showing {page * limit + 1} to {Math.min((page + 1) * limit, tradesData.total || 0)} of{' '}
                {tradesData.total || 0} trades
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="px-3 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </button>
                <span className="text-sm text-slate-400">
                  Page {page + 1} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!tradesData.has_more}
                  className="px-3 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="text-center py-12 text-slate-400">
            <p>No trades found</p>
            {ticker && <p className="text-sm mt-2">Try adjusting your filters</p>}
          </div>
        )}
      </Card>
    </div>
  );
}
