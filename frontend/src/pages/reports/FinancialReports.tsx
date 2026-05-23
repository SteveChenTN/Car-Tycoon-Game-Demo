/**
 * FinancialReports - 财务报表
 * 读取真实财务快照，展示损益、现金变化和销售趋势。
 */

import React, { useEffect, useState } from 'react';
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
import { TrendingUp, DollarSign, PieChart as PieChartIcon, FileText, Wallet } from 'lucide-react';
import {
  getFinancialReportPage,
  type CashFlowBridgeData,
  type FinancialHistoryPoint,
  type MarketShareData,
  type PLStatementData,
} from '@/services/reportService';
import { formatCurrency } from '@/utils/formatters';

export const FinancialReports: React.FC = () => {
  const { playerCompanyId, gameId } = useGameContext();
  const [activeTab, setActiveTab] = useState<'overview' | 'pl' | 'sales'>('overview');
  const [financialHistory, setFinancialHistory] = useState<FinancialHistoryPoint[]>([]);
  const [marketShare, setMarketShare] = useState<MarketShareData[]>([]);
  const [plStatement, setPlStatement] = useState<PLStatementData | null>(null);
  const [cashFlow, setCashFlow] = useState<CashFlowBridgeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!playerCompanyId || !gameId) {
      setLoading(false);
      setError('请先创建或加载游戏存档。');
      return;
    }

    void loadFinancialData(gameId, playerCompanyId);
  }, [gameId, playerCompanyId]);

  const loadFinancialData = async (currentGameId: number, companyId: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getFinancialReportPage(currentGameId, companyId);
      setFinancialHistory(data.history);
      setMarketShare(data.market_share);
      setPlStatement(data.pl_statement);
      setCashFlow(data.cash_flow);
      if (data.history.length === 0) {
        setError('尚未生成财务快照，请先推进一个回合。');
      }
    } catch (error) {
      console.error('Failed to load financial data:', error);
      setError('无法加载财务报表。');
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
      <div className="bg-slate-900 border-b border-slate-800 p-6">
        <h1 className="text-2xl font-bold text-cyan-400 font-mono flex items-center gap-3">
          <TrendingUp className="w-6 h-6" />
          财务报表 / FINANCIAL REPORTS
        </h1>
        <p className="text-slate-500 text-sm mt-2 font-mono">
          现金、利润、资产负债与经营动作的闭环记录
        </p>
      </div>

      <div className="bg-slate-900/50 border-b border-slate-800 px-6 flex gap-2">
        <TabButton active={activeTab === 'overview'} color="cyan" onClick={() => setActiveTab('overview')}>
          财务概览
        </TabButton>
        <TabButton active={activeTab === 'pl'} color="purple" onClick={() => setActiveTab('pl')}>
          损益表
        </TabButton>
        <TabButton active={activeTab === 'sales'} color="emerald" onClick={() => setActiveTab('sales')}>
          销售分析
        </TabButton>
      </div>

      <div className="flex-1 overflow-auto p-6">
        {error && <EmptyState message={error} />}
        {!error && activeTab === 'overview' && (
          <OverviewTab financialHistory={financialHistory} marketShare={marketShare} cashFlow={cashFlow} />
        )}
        {!error && activeTab === 'pl' && plStatement && <PLTab plStatement={plStatement} />}
        {!error && activeTab === 'sales' && <SalesTab financialHistory={financialHistory} />}
      </div>
    </div>
  );
};

interface TabButtonProps {
  active: boolean;
  color: 'cyan' | 'purple' | 'emerald';
  onClick: () => void;
  children: React.ReactNode;
}

const TabButton: React.FC<TabButtonProps> = ({ active, color, onClick, children }) => {
  const activeClasses = {
    cyan: 'bg-cyan-900 text-cyan-400 border-cyan-500',
    purple: 'bg-purple-900 text-purple-400 border-purple-500',
    emerald: 'bg-emerald-900 text-emerald-400 border-emerald-500',
  };
  const hoverClasses = {
    cyan: 'hover:text-cyan-400',
    purple: 'hover:text-purple-400',
    emerald: 'hover:text-emerald-400',
  };

  return (
    <button
      onClick={onClick}
      className={`px-6 py-3 font-mono text-sm font-bold transition-all border-b-2 ${
        active ? activeClasses[color] : `border-transparent text-slate-400 ${hoverClasses[color]}`
      }`}
    >
      {children}
    </button>
  );
};

interface OverviewTabProps {
  financialHistory: FinancialHistoryPoint[];
  marketShare: MarketShareData[];
  cashFlow: CashFlowBridgeData | null;
}

const OverviewTab: React.FC<OverviewTabProps> = ({ financialHistory, marketShare, cashFlow }) => {
  const latestData = financialHistory[financialHistory.length - 1];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard title="现金余额" value={formatCurrency(latestData.cash)} icon={<DollarSign className="w-5 h-5" />} color="cyan" />
        <MetricCard title="本期收入" value={formatCurrency(latestData.revenue)} icon={<TrendingUp className="w-5 h-5" />} color="emerald" />
        <MetricCard title="本期支出" value={formatCurrency(latestData.expenses)} icon={<TrendingUp className="w-5 h-5 rotate-180" />} color="rose" />
        <MetricCard title="净利润" value={formatCurrency(latestData.net_income)} icon={<PieChartIcon className="w-5 h-5" />} color={latestData.net_income >= 0 ? 'emerald' : 'rose'} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-bold text-cyan-400 font-mono mb-4">现金与损益趋势</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={financialHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="turn" stroke="#64748b" style={{ fontSize: 12 }} />
              <YAxis stroke="#64748b" style={{ fontSize: 12 }} tickFormatter={(value) => `$${Math.round(Number(value) / 1_000_000)}M`} />
              <Tooltip content={<CurrencyTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
              <Area type="monotone" dataKey="cash" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.16} name="现金" />
              <Area type="monotone" dataKey="net_income" stroke="#10b981" fill="#10b981" fillOpacity={0.14} name="净利润" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <CashFlowPanel cashFlow={cashFlow} />
      </div>

      {marketShare.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-bold text-cyan-400 font-mono mb-4">全球市场份额</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={marketShare} cx="50%" cy="50%" labelLine={false} label={({ company, share }) => `${company}: ${share}%`} outerRadius={100} fill="#8884d8" dataKey="share">
                {marketShare.map((entry) => (
                  <Cell key={entry.company} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

const CashFlowPanel: React.FC<{ cashFlow: CashFlowBridgeData | null }> = ({ cashFlow }) => {
  if (!cashFlow) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-bold text-cyan-400 font-mono mb-4">现金变化来源</h3>
        <p className="text-sm text-slate-500 font-mono">暂无现金桥数据</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h3 className="text-lg font-bold text-cyan-400 font-mono mb-4 flex items-center gap-2">
        <Wallet className="w-5 h-5" />
        现金变化来源
      </h3>
      <div className="space-y-3 font-mono text-sm">
        <CashFlowRow label="期初现金" value={cashFlow.starting_cash} muted />
        {cashFlow.lines.map((line) => (
          <CashFlowRow key={line.label} label={line.label} value={line.amount} />
        ))}
        <div className="border-t border-slate-700 pt-3">
          <CashFlowRow label="期末现金" value={cashFlow.ending_cash} strong />
        </div>
      </div>
    </div>
  );
};

interface CashFlowRowProps {
  label: string;
  value: number;
  muted?: boolean;
  strong?: boolean;
}

const CashFlowRow: React.FC<CashFlowRowProps> = ({ label, value, muted, strong }) => (
  <div className={`flex justify-between gap-4 ${strong ? 'font-bold text-base' : ''}`}>
    <span className={muted ? 'text-slate-500' : 'text-slate-400'}>{label}</span>
    <span className={value >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{formatCurrency(value)}</span>
  </div>
);

interface PLTabProps {
  plStatement: PLStatementData;
}

const PLTab: React.FC<PLTabProps> = ({ plStatement }) => (
  <div className="max-w-4xl mx-auto">
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
      <div className="bg-slate-800 p-4 border-b border-slate-700">
        <h2 className="text-xl font-bold text-cyan-400 font-mono">损益表 (P&L Statement)</h2>
        <p className="text-sm text-slate-500 mt-1">最新月度财务明细</p>
      </div>

      <div className="p-6">
        <table className="w-full">
          <tbody className="font-mono">
            <PLRow label="营业收入" value={plStatement.revenue} bold />
            <PLRow label="销售成本 (COGS)" value={plStatement.cogs} indent />
            <PLRow label="毛利润" value={plStatement.gross_profit} bold highlight="emerald" />
            <tr><td colSpan={2} className="py-2" /></tr>
            <PLRow label="研发费用" value={plStatement.rd_cost} indent />
            <PLRow label="市场营销" value={plStatement.marketing_cost} indent />
            <PLRow label="管理费用" value={plStatement.admin_cost} indent />
            <tr><td colSpan={2} className="py-2" /></tr>
            <PLRow label="营业利润" value={plStatement.operating_income} bold highlight="cyan" />
            <tr><td colSpan={2} className="py-2" /></tr>
            <PLRow label="利息支出" value={plStatement.interest} indent />
            <PLRow label="所得税" value={plStatement.tax} indent />
            <tr><td colSpan={2} className="py-4 border-t-2 border-slate-700" /></tr>
            <PLRow label="净利润" value={plStatement.net_income} bold large highlight={plStatement.net_income >= 0 ? 'emerald' : 'rose'} />
          </tbody>
        </table>
      </div>
    </div>
  </div>
);

const SalesTab: React.FC<{ financialHistory: FinancialHistoryPoint[] }> = ({ financialHistory }) => (
  <div className="space-y-6">
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h3 className="text-lg font-bold text-cyan-400 font-mono mb-4">收入与销量趋势</h3>
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={financialHistory}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="turn" stroke="#64748b" style={{ fontSize: 12 }} />
          <YAxis yAxisId="money" stroke="#64748b" style={{ fontSize: 12 }} tickFormatter={(value) => `$${Math.round(Number(value) / 1_000_000)}M`} />
          <YAxis yAxisId="units" orientation="right" stroke="#64748b" style={{ fontSize: 12 }} />
          <Tooltip content={<CurrencyTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
          <Bar yAxisId="money" dataKey="revenue" fill="#06b6d4" name="收入" />
          <Bar yAxisId="money" dataKey="net_income" fill="#10b981" name="净利润" />
          <Bar yAxisId="units" dataKey="units_sold" fill="#f59e0b" name="销量" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  </div>
);

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
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 min-w-0">
      <div className="flex items-center justify-between mb-2 gap-3">
        <span className="text-xs text-slate-500 font-mono uppercase truncate">{title}</span>
        <div className={`p-2 rounded ${colorClasses[color]}`}>{icon}</div>
      </div>
      <div className={`text-xl font-bold font-mono break-words ${colorClasses[color].split(' ')[0]}`}>
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
    return value >= 0 ? 'text-slate-300' : 'text-rose-300';
  };

  return (
    <tr className={bold ? 'font-bold' : ''}>
      <td className={`py-2 ${indent ? 'pl-8' : ''} ${large ? 'text-lg' : 'text-sm'} text-slate-400`}>
        {label}
      </td>
      <td className={`py-2 text-right ${large ? 'text-2xl' : 'text-sm'} ${getValueColor()}`}>
        {formatCurrency(value)}
      </td>
    </tr>
  );
};

const EmptyState: React.FC<{ message: string }> = ({ message }) => (
  <div className="h-full flex items-center justify-center">
    <div className="text-center text-slate-400 font-mono">
      <FileText className="w-10 h-10 mx-auto mb-3 text-slate-600" />
      {message}
    </div>
  </div>
);

const CurrencyTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number }>; label?: string | number }) => {
  if (!active || !payload?.length) return null;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-sm font-mono">
      <div className="text-slate-400 mb-2">回合 {label}</div>
      {payload.map((item) => (
        <div key={item.name} className="flex justify-between gap-4 text-slate-200">
          <span>{item.name}</span>
          <span>{item.name === '销量' ? item.value.toLocaleString() : formatCurrency(item.value)}</span>
        </div>
      ))}
    </div>
  );
};

