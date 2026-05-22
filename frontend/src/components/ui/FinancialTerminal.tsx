import { useMemo } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import type { FinancialSnapshot } from '@/types';
import { formatCurrency } from '@/utils/formatters';

interface FinancialTerminalProps {
  history?: FinancialSnapshot[];
  currentCash?: number;
  currentProfit?: number;
  marketShare?: number;
}

// Mock data generator
function generateMockHistory(): FinancialSnapshot[] {
  const data: FinancialSnapshot[] = [];
  let cash = 500000;
  let trend = 1;
  
  for (let i = 0; i < 12; i++) {
    trend += (Math.random() - 0.5) * 0.3;
    trend = Math.max(-1, Math.min(2, trend));
    
    const profit = (Math.random() - 0.3) * 50000 * trend;
    cash += profit;
    
    data.push({
      turn_number: i + 1,
      cash: Math.max(0, cash),
      revenue: Math.abs(profit) * (1 + Math.random() * 0.5),
      profit,
      market_share: 5 + Math.random() * 10,
    });
  }
  
  return data;
}

export function FinancialTerminal({
  history: propHistory,
  currentCash = 750000,
  currentProfit = 45000,
  marketShare = 8.5,
}: FinancialTerminalProps) {
  const history = useMemo(() => {
    return propHistory && propHistory.length > 0 ? propHistory : generateMockHistory();
  }, [propHistory]);

  const latestData = history[history.length - 1];
  const displayCash = propHistory ? currentCash : latestData.cash;
  const displayProfit = propHistory ? currentProfit : latestData.profit;
  const displayShare = propHistory ? marketShare : latestData.market_share;

  return (
    <div className="h-full flex flex-col bg-slate-950/50 rounded-lg border border-slate-800/50 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800/50">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
          <span className="text-xs font-mono text-emerald-400 uppercase tracking-wider">
            Financial Terminal
          </span>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-3 gap-4 p-4 border-b border-slate-800/50">
        <div className="flex flex-col">
          <span className="text-xs text-slate-500 uppercase tracking-wider mb-1">
            Cash
          </span>
          <span className="text-xl font-mono font-bold text-emerald-400">
            {formatCurrency(displayCash)}
          </span>
        </div>
        
        <div className="flex flex-col">
          <span className="text-xs text-slate-500 uppercase tracking-wider mb-1">
            Net Profit
          </span>
          <span
            className={`text-xl font-mono font-bold ${
              displayProfit >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {displayProfit >= 0 ? '+' : ''}
            {formatCurrency(displayProfit)}
          </span>
        </div>
        
        <div className="flex flex-col">
          <span className="text-xs text-slate-500 uppercase tracking-wider mb-1">
            Market Share
          </span>
          <span className="text-xl font-mono font-bold text-cyan-400">
            {displayShare.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Cash Flow Chart */}
      <div className="flex-1 p-4">
        <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">
          Cash Flow Trend
        </div>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={history}>
            <defs>
              <linearGradient id="profitGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity={0.8} />
                <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="lossGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.8} />
                <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="turn_number"
              stroke="#475569"
              style={{ fontSize: '10px', fontFamily: 'monospace' }}
              tickLine={false}
            />
            <YAxis
              stroke="#475569"
              style={{ fontSize: '10px', fontFamily: 'monospace' }}
              tickLine={false}
              tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '4px',
                fontSize: '12px',
                fontFamily: 'monospace',
              }}
              labelStyle={{ color: '#94a3b8' }}
              formatter={(value: number) => [formatCurrency(value), 'Profit']}
              labelFormatter={(label) => `Turn ${label}`}
            />
            <Area
              type="monotone"
              dataKey="profit"
              stroke="#10b981"
              strokeWidth={2}
              fill="url(#profitGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}


