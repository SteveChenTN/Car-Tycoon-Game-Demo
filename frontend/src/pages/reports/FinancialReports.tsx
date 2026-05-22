/**
 * FinancialReports - 财务报表
 * 提供财务概览、损益表、销售分析等图表和表格
 */

import React, { useState, useEffect } from 'react';
import { useGameContext } from '@/contexts/GameContext';
import {
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { TrendingUp, DollarSign, PieChart as PieChartIcon, FileText } from 'lucide-react';

// ============================================================
// Types
// ============================================================

interface FinancialData {
  turn: number;
  revenue: number;
  expenses: number;
  net_income: number;
  cash: number;
}

interface MarketShareData {
  company: string;
  share: number;
  color: string;
}

interface PLStatement {
  revenue: number;
  cogs: number; // Cost of Goods Sold
  gross_profit: number;
  rd_cost: number;
  marketing_cost: number;
  admin_cost: number;
  operating_income: number;
  interest: number;
  tax: number;
  net_income: number;
}

// ============================================================
// Main Component
// ============================================================

export const FinancialReports: React.FC = () => {
  const { gameState } = useGameContext();
  const [activeTab, setActiveTab] = useState<'overview' | 'pl' | 'sales'>('overview');
  const [financialHistory, setFinancialHistory] = useState<FinancialData[]>([]);
  const [marketShare, setMarketShare] = useState<MarketShareData[]>([]);
  const [plStatement, setPlStatement] = useState<PLStatement | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadFinancialData();
  }, []);

  const loadFinancialData = async () => {
    setLoading(true);
    try {
      // TODO: 调用真实 API
      // Mock data for demonstration
      setFinancialHistory(getMockFinancialHistory());
      setMarketShare(getMockMarketShare());
      setPlStatement(getMockPLStatement());
    } catch (error) {
      console.error('Failed to load financial data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-950">
        <div className="text-center">
          <FileText className="w-12 h-12 text-cyan-400 animate-pulse mx-auto mb-4" />
          <p className="text-slate-400 font-mono text-sm">加载财务数据...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-slate-950">
      {/* Header */}
      <div className="bg-slate-900 border-b border-slate-800 p-6">
        <h1 className="text-2xl font-bold text-cyan-400 font-mono flex items-center gap-3">
          <TrendingUp className="w-6 h-6" />
          财务报表 / FINANCIAL REPORTS
        </h1>
        <p className="text-slate-500 text-sm mt-2 font-mono">
          分析公司财务状况和市场表现
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="bg-slate-900/50 border-b border-slate-800 px-6 flex gap-2">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-6 py-3 font-mono text-sm font-bold transition-all ${
            activeTab === 'overview'
              ? 'bg-cyan-900 text-cyan-400 border-b-2 border-cyan-500'
              : 'text-slate-400 hover:text-cyan-400'
          }`}
        >
          财务概览
        </button>
        <button
          onClick={() => setActiveTab('pl')}
          className={`px-6 py-3 font-mono text-sm font-bold transition-all ${
            activeTab === 'pl'
              ? 'bg-purple-900 text-purple-400 border-b-2 border-purple-500'
              : 'text-slate-400 hover:text-purple-400'
          }`}
        >
          损益表
        </button>
        <button
          onClick={() => setActiveTab('sales')}
          className={`px-6 py-3 font-mono text-sm font-bold transition-all ${
            activeTab === 'sales'
              ? 'bg-emerald-900 text-emerald-400 border-b-2 border-emerald-500'
              : 'text-slate-400 hover:text-emerald-400'
          }`}
        >
          销售分析
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {activeTab === 'overview' && (
          <OverviewTab financialHistory={financialHistory} marketShare={marketShare} />
        )}
        {activeTab === 'pl' && plStatement && <PLTab plStatement={plStatement} />}
        {activeTab === 'sales' && <SalesTab financialHistory={financialHistory} />}
      </div>
    </div>
  );
};

// ============================================================
// Overview Tab Component
// ============================================================

interface OverviewTabProps {
  financialHistory: FinancialData[];
  marketShare: MarketShareData[];
}

const OverviewTab: React.FC<OverviewTabProps> = ({ financialHistory, marketShare }) => {
  const latestData = financialHistory[financialHistory.length - 1];

  return (
    <div className="space-y-6">
      {/* Key Metrics Cards */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard
          title="现金余额"
          value={`$${latestData.cash.toLocaleString()}`}
          icon={<DollarSign className="w-5 h-5" />}
          color="cyan"
        />
        <MetricCard
          title="本月收入"
          value={`$${latestData.revenue.toLocaleString()}`}
          icon={<TrendingUp className="w-5 h-5" />}
          color="emerald"
        />
        <MetricCard
          title="本月支出"
          value={`$${latestData.expenses.toLocaleString()}`}
          icon={<TrendingUp className="w-5 h-5 rotate-180" />}
          color="rose"
        />
        <MetricCard
          title="净利润"
          value={`$${latestData.net_income.toLocaleString()}`}
          icon={<PieChartIcon className="w-5 h-5" />}
          color={latestData.net_income >= 0 ? 'emerald' : 'rose'}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-2 gap-6">
        {/* Cash Flow Chart */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-bold text-cyan-400 font-mono mb-4">现金流趋势</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={financialHistory}>
              <defs>
                <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorExpenses" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="turn" stroke="#64748b" style={{ fontSize: 12 }} />
              <YAxis stroke="#64748b" style={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                }}
                labelStyle={{ color: '#cbd5e1' }}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
              <Area
                type="monotone"
                dataKey="revenue"
                stroke="#10b981"
                fillOpacity={1}
                fill="url(#colorRevenue)"
                name="收入"
              />
              <Area
                type="monotone"
                dataKey="expenses"
                stroke="#ef4444"
                fillOpacity={1}
                fill="url(#colorExpenses)"
                name="支出"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Market Share Pie Chart */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-bold text-cyan-400 font-mono mb-4">全球市场份额</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={marketShare}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ company, share }) => `${company}: ${share}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="share"
              >
                {marketShare.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// P&L Tab Component
// ============================================================

interface PLTabProps {
  plStatement: PLStatement;
}

const PLTab: React.FC<PLTabProps> = ({ plStatement }) => {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        <div className="bg-slate-800 p-4 border-b border-slate-700">
          <h2 className="text-xl font-bold text-cyan-400 font-mono">损益表 (P&L Statement)</h2>
          <p className="text-sm text-slate-500 mt-1">本年度财务明细</p>
        </div>

        <div className="p-6">
          <table className="w-full">
            <tbody className="font-mono">
              {/* Revenue */}
              <PLRow label="营业收入" value={plStatement.revenue} bold />
              
              {/* COGS */}
              <PLRow label="销售成本 (COGS)" value={plStatement.cogs} indent />
              
              {/* Gross Profit */}
              <PLRow
                label="毛利润"
                value={plStatement.gross_profit}
                bold
                highlight="emerald"
              />

              <tr><td colSpan={2} className="py-2" /></tr>

              {/* Operating Expenses */}
              <PLRow label="研发费用" value={plStatement.rd_cost} indent />
              <PLRow label="市场营销" value={plStatement.marketing_cost} indent />
              <PLRow label="管理费用" value={plStatement.admin_cost} indent />

              <tr><td colSpan={2} className="py-2" /></tr>

              {/* Operating Income */}
              <PLRow
                label="营业利润"
                value={plStatement.operating_income}
                bold
                highlight="cyan"
              />

              <tr><td colSpan={2} className="py-2" /></tr>

              {/* Other */}
              <PLRow label="利息支出" value={plStatement.interest} indent />
              <PLRow label="所得税" value={plStatement.tax} indent />

              <tr><td colSpan={2} className="py-4 border-t-2 border-slate-700" /></tr>

              {/* Net Income */}
              <PLRow
                label="净利润"
                value={plStatement.net_income}
                bold
                large
                highlight={plStatement.net_income >= 0 ? 'emerald' : 'rose'}
              />
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// Sales Tab Component
// ============================================================

interface SalesTabProps {
  financialHistory: FinancialData[];
}

const SalesTab: React.FC<SalesTabProps> = ({ financialHistory }) => {
  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-bold text-cyan-400 font-mono mb-4">收入趋势</h3>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={financialHistory}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="turn" stroke="#64748b" style={{ fontSize: 12 }} />
            <YAxis stroke="#64748b" style={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#cbd5e1' }}
            />
            <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
            <Bar dataKey="revenue" fill="#06b6d4" name="收入" />
            <Bar dataKey="net_income" fill="#10b981" name="净利润" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top Selling Models (Placeholder) */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-bold text-cyan-400 font-mono mb-4">畅销车型 Top 5</h3>
        <div className="space-y-3">
          {['Model S-Line', 'Urban Compact X', 'Luxury GT', 'Sport Coupe', 'Family SUV'].map(
            (model, idx) => (
              <div
                key={model}
                className="flex items-center justify-between p-3 bg-slate-800/50 rounded"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl font-bold text-slate-600">#{idx + 1}</span>
                  <span className="text-slate-300 font-mono">{model}</span>
                </div>
                <span className="text-cyan-400 font-mono font-bold">
                  {Math.floor(Math.random() * 5000 + 1000)} 辆
                </span>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================================
// Helper Components
// ============================================================

interface MetricCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  color: 'cyan' | 'emerald' | 'rose' | 'amber';
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, icon, color }) => {
  const colorClasses = {
    cyan: 'text-cyan-400 bg-cyan-900/20',
    emerald: 'text-emerald-400 bg-emerald-900/20',
    rose: 'text-rose-400 bg-rose-900/20',
    amber: 'text-amber-400 bg-amber-900/20',
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-500 font-mono uppercase">{title}</span>
        <div className={`p-2 rounded ${colorClasses[color]}`}>{icon}</div>
      </div>
      <div className={`text-2xl font-bold font-mono ${colorClasses[color].split(' ')[0]}`}>
        {value}
      </div>
    </div>
  );
};

interface PLRowProps {
  label: string;
  value: number;
  indent?: boolean;
  bold?: boolean;
  large?: boolean;
  highlight?: 'cyan' | 'emerald' | 'rose';
}

const PLRow: React.FC<PLRowProps> = ({ label, value, indent, bold, large, highlight }) => {
  const getValueColor = () => {
    if (highlight === 'cyan') return 'text-cyan-400';
    if (highlight === 'emerald') return 'text-emerald-400';
    if (highlight === 'rose') return 'text-rose-400';
    return 'text-slate-300';
  };

  return (
    <tr className={bold ? 'font-bold' : ''}>
      <td className={`py-2 ${indent ? 'pl-8' : ''} ${large ? 'text-lg' : 'text-sm'} text-slate-400`}>
        {label}
      </td>
      <td className={`py-2 text-right ${large ? 'text-2xl' : 'text-sm'} ${getValueColor()}`}>
        {value >= 0 ? '' : '-'}${Math.abs(value).toLocaleString()}
      </td>
    </tr>
  );
};

// ============================================================
// Mock Data Functions
// ============================================================

function getMockFinancialHistory(): FinancialData[] {
  const data: FinancialData[] = [];
  let cash = 1000000;

  for (let turn = 1; turn <= 12; turn++) {
    const revenue = Math.floor(Math.random() * 500000 + 200000);
    const expenses = Math.floor(Math.random() * 400000 + 150000);
    const net_income = revenue - expenses;
    cash += net_income;

    data.push({
      turn,
      revenue,
      expenses,
      net_income,
      cash,
    });
  }

  return data;
}

function getMockMarketShare(): MarketShareData[] {
  return [
    { company: '玩家公司', share: 18, color: '#06b6d4' },
    { company: 'Nexus Motors', share: 25, color: '#8b5cf6' },
    { company: 'Apex Auto', share: 22, color: '#f59e0b' },
    { company: 'Quantum Vehicles', share: 15, color: '#10b981' },
    { company: '其他', share: 20, color: '#64748b' },
  ];
}

function getMockPLStatement(): PLStatement {
  const revenue = 5000000;
  const cogs = 3000000;
  const gross_profit = revenue - cogs;
  const rd_cost = 500000;
  const marketing_cost = 300000;
  const admin_cost = 200000;
  const operating_income = gross_profit - rd_cost - marketing_cost - admin_cost;
  const interest = 50000;
  const tax = Math.floor(operating_income * 0.2);
  const net_income = operating_income - interest - tax;

  return {
    revenue,
    cogs,
    gross_profit,
    rd_cost,
    marketing_cost,
    admin_cost,
    operating_income,
    interest,
    tax,
    net_income,
  };
}


