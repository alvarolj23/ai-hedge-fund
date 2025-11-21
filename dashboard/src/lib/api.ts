/**
 * API client for communicating with the AI Hedge Fund backend.
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export interface PortfolioPosition {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pl: number;
  unrealized_pl_percent: number;
  side: 'long' | 'short';
}

export interface PortfolioSummary {
  total_value: number;
  cash: number;
  positions_value: number;
  buying_power: number;
  positions: PortfolioPosition[];
  last_updated: string;
  error?: string;
}

export interface PerformanceMetrics {
  period_days: number;
  total_trades: number;
  win_rate: number;
  wins: number;
  losses: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  last_updated?: string;
  error?: string;
}

export interface Trade {
  id: string;
  timestamp: string;
  ticker: string;
  action: string;
  quantity: number;
  price: number;
  status: string;
  confidence?: number;
}

export interface TradeHistoryResponse {
  trades: Trade[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  error?: string;
}

export interface AgentPerformance {
  agent_name: string;
  total_signals: number;
  avg_confidence: number;
  buy_signals: number;
  sell_signals: number;
  hold_signals: number;
  win_rate: number;
}

export interface AgentPerformanceResponse {
  agents: AgentPerformance[];
  period_days: number;
  total_agents: number;
  last_updated?: string;
  error?: string;
}

export interface SystemHealth {
  status: string;
  timestamp: string;
  components: {
    alpaca?: { status: string; last_updated?: string; error?: string };
    cosmos_db?: { status: string; error?: string };
    queue?: { status: string; depth?: number; error?: string };
  };
}

export interface PortfolioHistoryPoint {
  date: string;
  value: number;
  cash: number;
  positions_value: number;
}

export interface PortfolioHistoryResponse {
  history: PortfolioHistoryPoint[];
  period_days: number;
  data_points: number;
  last_updated?: string;
  error?: string;
}

export interface MarketMonitorConfig {
  watchlist: string[];
  price_breakout_threshold: number;
  volume_spike_multiplier: number;
  cooldown_seconds: number;
  volume_lookback_days: number;
}

export interface TradingConfig {
  confidence_threshold: number;
  trade_mode: string;
  dry_run: boolean;
  enabled_agents?: string[] | null;
}

// Dashboard API endpoints
export const dashboardApi = {
  // Get portfolio summary from Alpaca
  getPortfolioSummary: async (): Promise<PortfolioSummary> => {
    const response = await api.get('/dashboard/portfolio');
    return response.data;
  },

  // Get performance metrics
  getPerformanceMetrics: async (days: number = 30): Promise<PerformanceMetrics> => {
    const response = await api.get('/dashboard/metrics', { params: { days } });
    return response.data;
  },

  // Get trade history
  getTradeHistory: async (params?: {
    limit?: number;
    offset?: number;
    ticker?: string;
    action?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<TradeHistoryResponse> => {
    const response = await api.get('/dashboard/trades', { params });
    return response.data;
  },

  // Get agent performance leaderboard
  getAgentPerformance: async (days: number = 30): Promise<AgentPerformanceResponse> => {
    const response = await api.get('/dashboard/agent-performance', { params: { days } });
    return response.data;
  },

  // Get system health
  getSystemHealth: async (): Promise<SystemHealth> => {
    const response = await api.get('/dashboard/system-health');
    return response.data;
  },

  // Get portfolio history for charts
  getPortfolioHistory: async (days: number = 30): Promise<PortfolioHistoryResponse> => {
    const response = await api.get('/dashboard/portfolio-history', { params: { days } });
    return response.data;
  },
};

// Configuration API endpoints
export const configApi = {
  // Get market monitor configuration
  getMonitorConfig: async (): Promise<MarketMonitorConfig> => {
    const response = await api.get('/config/monitor');
    return response.data;
  },

  // Update market monitor configuration
  updateMonitorConfig: async (config: MarketMonitorConfig): Promise<any> => {
    const response = await api.put('/config/monitor', config);
    return response.data;
  },

  // Get trading configuration
  getTradingConfig: async (): Promise<TradingConfig> => {
    const response = await api.get('/config/trading');
    return response.data;
  },

  // Update trading configuration
  updateTradingConfig: async (config: TradingConfig): Promise<any> => {
    const response = await api.put('/config/trading', config);
    return response.data;
  },
};

export default api;
