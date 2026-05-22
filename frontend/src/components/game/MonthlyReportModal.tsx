/**
 * 月度报告Modal
 * 监听TURN_COMPLETE WebSocket事件，以"收据"风格展示月度总结
 */

import { useState, useEffect } from 'react';
import { MonthlyReport } from '../../types';
import { getLatestMonthlyReport } from '../../services/reportService';
import { useGame } from '../../contexts/GameContext';
import clsx from 'clsx';

// ============================================================
// 主组件
// ============================================================

interface MonthlyReportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MonthlyReportModal({ isOpen, onClose }: MonthlyReportModalProps) {
  const { gameState } = useGame();
  const [report, setReport] = useState<MonthlyReport | null>(null);
  const [loading, setLoading] = useState(false);

  // 监听游戏状态变化，加载最新报告
  useEffect(() => {
    if (isOpen && gameState) {
      loadReport();
    }
  }, [isOpen, gameState]);

  const loadReport = async () => {
    setLoading(true);
    try {
      // TODO: 从gameState获取game_id
      const data = await getLatestMonthlyReport(1);
      if (data) {
        setReport(data);
      } else {
        // API端点不存在或返回null，使用mock数据
        console.log('[MonthlyReportModal] Report endpoint not available, using mock data');
        setReport(getMockReport());
      }
    } catch (error) {
      console.error('[MonthlyReportModal] Failed to load report:', error);
      // Fallback: 如果API不可用，使用mock数据
      setReport(getMockReport());
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 border-2 border-slate-600 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
        {/* Header */}
        <div className="bg-slate-900 px-6 py-4 border-b border-slate-600">
          <h2 className="text-2xl font-bold text-center text-cyan-400 tracking-wider">
            月度财务报告
          </h2>
          {report && (
            <div className="text-center text-sm text-slate-400 mt-1">
              {report.year}年 {report.month}月 | 回合 #{report.turn_number}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {loading && (
            <div className="text-center py-12 text-slate-400">加载中...</div>
          )}

          {!loading && report && (
            <div className="space-y-6 font-mono">
              {/* Section 1: Financials */}
              <section className="receipt-section">
                <h3 className="receipt-section-title">财务概况</h3>
                <div className="space-y-2">
                  <div className="receipt-line">
                    <span className="text-slate-400">营收</span>
                    <span className="text-green-400 font-bold">
                      ${report.financials.revenue.toLocaleString()}
                    </span>
                  </div>
                  <div className="receipt-line">
                    <span className="text-slate-400">成本</span>
                    <span className="text-red-400 font-bold">
                      -${report.financials.costs.toLocaleString()}
                    </span>
                  </div>
                  <div className="border-t-2 border-dashed border-slate-600 my-2"></div>
                  <div className="receipt-line text-lg">
                    <span className="font-bold">净利润</span>
                    <span
                      className={clsx(
                        'font-bold',
                        report.financials.net_profit >= 0 ? 'text-green-400' : 'text-red-400'
                      )}
                    >
                      ${report.financials.net_profit.toLocaleString()}
                    </span>
                  </div>
                  <div className="receipt-line">
                    <span className="text-slate-400">现金余额</span>
                    <span className="text-cyan-400 font-bold">
                      ${report.financials.cash_balance.toLocaleString()}
                    </span>
                  </div>
                </div>
              </section>

              {/* Section 2: Production */}
              <section className="receipt-section">
                <h3 className="receipt-section-title">生产统计</h3>
                <div className="space-y-2">
                  <div className="receipt-line">
                    <span className="text-slate-400">生产车辆</span>
                    <span className="font-bold">{report.production.cars_built.toLocaleString()} 辆</span>
                  </div>
                  <div className="receipt-line">
                    <span className="text-slate-400">零部件产量</span>
                    <span className="font-bold">{report.production.components_produced.toLocaleString()} 件</span>
                  </div>
                  <div className="receipt-line">
                    <span className="text-slate-400">产能利用率</span>
                    <span className="font-bold">
                      {(report.production.utilization_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </section>

              {/* Section 3: Alerts */}
              {report.alerts.length > 0 && (
                <section className="receipt-section">
                  <h3 className="receipt-section-title">重要通知</h3>
                  <div className="space-y-2">
                    {report.alerts.map((alert, index) => (
                      <AlertItem key={index} alert={alert} />
                    ))}
                  </div>
                </section>
              )}

              {/* Receipt Footer */}
              <div className="border-t-2 border-slate-600 pt-4 text-center text-xs text-slate-500">
                <div>AutoMogul Simulation Engine v1.4</div>
                <div className="mt-1">感谢您的经营！</div>
              </div>
            </div>
          )}
        </div>

        {/* Footer - Next Month Button */}
        <div className="px-6 py-4 border-t border-slate-600 bg-slate-900">
          <button
            onClick={onClose}
            className="w-full py-3 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg font-bold text-lg transition-colors"
          >
            继续下个月
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// 警报项组件
// ============================================================

interface AlertItemProps {
  alert: MonthlyReport['alerts'][0];
}

function AlertItem({ alert }: AlertItemProps) {
  const iconConfig = {
    info: { icon: 'ℹ️', className: 'text-accent-primary bg-accent-primary/30' },
    warning: { icon: '⚠️', className: 'text-accent-warning bg-accent-warning/30' },
    success: { icon: '✓', className: 'text-accent-success bg-accent-success/30' },
    critical: { icon: '⚠', className: 'text-accent-danger bg-accent-danger/30' }
  };

  const config = iconConfig[alert.type];

  return (
    <div className={clsx('flex items-start gap-3 p-3 rounded border', config.className)}>
      <span className="text-xl">{config.icon}</span>
      <div className="flex-1 text-sm">
        <p className="text-white">{alert.message}</p>
      </div>
    </div>
  );
}

// ============================================================
// Mock数据（用于开发测试）
// ============================================================

function getMockReport(): MonthlyReport {
  return {
    turn_number: 12,
    year: 1950,
    month: 12,
    financials: {
      revenue: 2500000,
      costs: 1800000,
      net_profit: 700000,
      cash_balance: 5000000
    },
    production: {
      cars_built: 1250,
      components_produced: 3500,
      utilization_rate: 0.85
    },
    alerts: [
      {
        type: 'success',
        message: '生产线A完成改装，现在可以生产 Model X GT'
      },
      {
        type: 'warning',
        message: '北美市场需求下降10%，建议调整定价策略'
      },
      {
        type: 'info',
        message: '竞争对手推出新车型，市场份额受到影响'
      }
    ]
  };
}

export default MonthlyReportModal;

