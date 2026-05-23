/**
 * 市场策略指挥中心
 * 实现混合视图：效率控制栏 + 数据表格 + 热力图
 */

import { useState, useEffect, useMemo } from 'react';
import { RegionPricing, MarketHeatmapCell } from '../../types';
import { getMarketOverview, getSalesHeatmap, submitRegionalPricing } from '../../services/marketService';
import { useGame } from '../../contexts/GameContext';
import { ErrorBoundary } from '../../components/ErrorBoundary';
import clsx from 'clsx';

// ============================================================
// 主组件
// ============================================================

export function MarketDashboard() {
  const { playerCompanyId } = useGame();
  const [regions, setRegions] = useState<RegionPricing[]>([]);
  const [heatmap, setHeatmap] = useState<MarketHeatmapCell[]>([]);
  const [globalBasePrice, setGlobalBasePrice] = useState<number>(25000);
  const [regionalPrices, setRegionalPrices] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hoveredRegion, setHoveredRegion] = useState<number | null>(null);

  // 加载市场数据
  useEffect(() => {
    if (!playerCompanyId) {
      setRegions([]);
      setHeatmap([]);
      setRegionalPrices({});
      return;
    }

    loadMarketData();
  }, [playerCompanyId]);

  // 初始化区域价格
  useEffect(() => {
    if (regions.length > 0 && Object.keys(regionalPrices).length === 0) {
      const initialPrices: Record<number, number> = {};
      regions.forEach((region) => {
        initialPrices[region.region_id] = region.my_price || globalBasePrice;
      });
      setRegionalPrices(initialPrices);
    }
  }, [regions, globalBasePrice]);

  const loadMarketData = async () => {
    if (!playerCompanyId) return;

    setError(null);
    setLoading(true);
    try {
      const [marketData, heatmapData] = await Promise.all([
        getMarketOverview(playerCompanyId),
        getSalesHeatmap(playerCompanyId)
      ]);
      
      // 转换数据格式以匹配前端期望
      const formattedRegions = marketData.map((region: any) => ({
        ...region,
        demand_tier: region.demand_tier || (region.demand_level > 0.7 ? 'HIGH' : region.demand_level > 0.4 ? 'MEDIUM' : 'LOW'),
        my_price: region.my_price || globalBasePrice,
        estimated_profit: 0 // 将在 useMemo 中计算
      }));
      
      setRegions(formattedRegions);
      setHeatmap(heatmapData || []);
    } catch (error) {
      console.error('[MarketDashboard] Failed to load market data:', error);
      setError(error instanceof Error ? error.message : '加载市场数据失败');
      setRegions([]);
      setHeatmap([]);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyToAllRegions = () => {
    const newPrices: Record<number, number> = {};
    regions.forEach((region) => {
      newPrices[region.region_id] = globalBasePrice;
    });
    setRegionalPrices(newPrices);
  };

  const handleRegionalPriceChange = (regionId: number, price: number) => {
    setRegionalPrices((prev) => ({
      ...prev,
      [regionId]: price
    }));
  };

  const handleSubmitPricing = async () => {
    if (!playerCompanyId) return;

    setLoading(true);
    try {
      const response = await submitRegionalPricing({
        company_id: playerCompanyId,
        design_id: 1, // TODO: 选择车型
        regional_prices: regionalPrices
      });

      if (response.success) {
        console.log('[MarketDashboard] Pricing submitted:', response.message);
        alert(`定价策略已提交！\n预计月销量: ${response.estimated_monthly_sales}\n预计收入: $${response.estimated_revenue.toLocaleString()}`);
        await loadMarketData();
      }
    } catch (error) {
      console.error('[MarketDashboard] Failed to submit pricing:', error);
      alert('提交失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 计算估算利润
  const enrichedRegions = useMemo(() => {
    return regions.map((region) => {
      const myPrice = regionalPrices[region.region_id] || region.my_price;
      const estimatedVolume = 1000; // TODO: 从API获取真实估算
      const cost = 20000; // TODO: 从车型数据获取
      const estimatedProfit = (myPrice - cost) * estimatedVolume;

      return {
        ...region,
        my_price: myPrice,
        estimated_profit: estimatedProfit
      };
    });
  }, [regions, regionalPrices]);

  // 如果有错误，显示错误信息
  if (error && regions.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-900 text-slate-100">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-red-400 mb-4">加载市场数据失败</h2>
          <p className="text-slate-400 mb-4">{error}</p>
          <button
            onClick={loadMarketData}
            className="px-6 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded transition-colors"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="h-full flex flex-col bg-slate-900 text-slate-100">
        {/* Top Control Bar */}
        <div className="bg-slate-800 border-b border-slate-700 p-4">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="block text-xs text-slate-400 uppercase tracking-wider mb-1">
              全局基准价格
            </label>
            <input
              type="number"
              value={globalBasePrice}
              onChange={(e) => setGlobalBasePrice(Number(e.target.value))}
              className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-white font-mono"
              step={1000}
              min={0}
            />
          </div>
          <button
            onClick={handleApplyToAllRegions}
            className="mt-5 px-6 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded transition-colors font-semibold"
          >
            应用到所有区域
          </button>
          <button
            onClick={handleSubmitPricing}
            disabled={loading}
            className="mt-5 px-8 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded transition-colors font-bold"
          >
            {loading ? '提交中...' : '确认定价策略'}
          </button>
        </div>
      </div>

      {/* Split Pane Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel: Data Grid */}
        <div className="flex-1 overflow-auto p-6">
          <h2 className="text-2xl font-bold mb-4">区域定价表</h2>
          <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-900">
                <tr className="text-xs uppercase tracking-wider text-slate-400">
                  <th className="px-4 py-3 text-left">区域</th>
                  <th className="px-4 py-3 text-left">需求层级</th>
                  <th className="px-4 py-3 text-right">市场份额</th>
                  <th className="px-4 py-3 text-right">竞品均价</th>
                  <th className="px-4 py-3 text-right">我的价格</th>
                  <th className="px-4 py-3 text-right">预估利润</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {enrichedRegions.map((region) => {
                  const myPrice = region.my_price;
                  const rivalPrice = region.rival_avg_price;
                  const priceColor = myPrice < rivalPrice ? 'text-green-400' : 'text-red-400';

                  return (
                    <tr
                      key={region.region_id}
                      className="hover:bg-slate-700/50 transition-colors"
                      onMouseEnter={() => setHoveredRegion(region.region_id)}
                      onMouseLeave={() => setHoveredRegion(null)}
                    >
                      <td className="px-4 py-3">
                        <div className="font-semibold">{region.region_name}</div>
                        <div className="text-xs text-slate-500">{region.region_code}</div>
                      </td>
                      <td className="px-4 py-3">
                        <DemandTierBadge tier={region.demand_tier} />
                      </td>
                      <td className="px-4 py-3 text-right font-mono">
                        {(region.market_share * 100).toFixed(1)}%
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-slate-400">
                        ${rivalPrice.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <input
                          type="number"
                          value={myPrice}
                          onChange={(e) => handleRegionalPriceChange(region.region_id, Number(e.target.value))}
                          className={clsx(
                            'w-32 bg-slate-900 border border-slate-600 rounded px-2 py-1 text-right font-mono font-bold',
                            priceColor
                          )}
                          step={500}
                          min={0}
                        />
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-bold text-cyan-400">
                        ${region.estimated_profit.toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Panel: War Room Heatmap */}
        <div className="w-96 bg-slate-800 border-l border-slate-700 p-6 overflow-auto">
          <h2 className="text-2xl font-bold mb-4">销售热力图</h2>
          <p className="text-sm text-slate-400 mb-6">
            颜色越亮，销售强度越高
          </p>
          {heatmap.length === 0 ? (
            <div className="text-center text-slate-400 py-8">
              暂无热力图数据
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              {heatmap.map((cell) => {
                const isHovered = hoveredRegion === cell.region_id;
                const region = regions.find((r) => r.region_id === cell.region_id);

                return (
                  <div
                    key={cell.region_id}
                    className={clsx(
                      'relative aspect-square rounded border-2 transition-all cursor-pointer group',
                      isHovered ? 'border-white scale-110 z-10' : 'border-transparent'
                    )}
                    style={{ backgroundColor: cell.color || '#1e293b' }}
                    onMouseEnter={() => setHoveredRegion(cell.region_id)}
                    onMouseLeave={() => setHoveredRegion(null)}
                  >
                    <div className="absolute inset-0 flex items-center justify-center text-xs font-bold text-black mix-blend-difference">
                      {cell.region_code}
                    </div>
                    {/* Tooltip */}
                    {isHovered && region && (
                      <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 bg-black border border-slate-600 rounded p-2 text-xs whitespace-nowrap z-20 pointer-events-none">
                        <div className="font-semibold">{region.region_name}</div>
                        <div className="text-slate-400 mt-1">
                          {region.customer_feedback || '暂无反馈'}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Legend */}
          <div className="mt-6">
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">销售强度</div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">低</span>
              <div className="flex-1 h-4 rounded overflow-hidden flex">
                <div className="flex-1 bg-red-900"></div>
                <div className="flex-1 bg-orange-700"></div>
                <div className="flex-1 bg-yellow-500"></div>
                <div className="flex-1 bg-green-500"></div>
                <div className="flex-1 bg-cyan-400"></div>
              </div>
              <span className="text-xs text-slate-400">高</span>
            </div>
          </div>
        </div>
      </div>
      </div>
    </ErrorBoundary>
  );
}

// ============================================================
// 需求层级徽章
// ============================================================

function DemandTierBadge({ tier }: { tier: string }) {
  const tierConfig: Record<string, { label: string; className: string }> = {
    HIGH: { label: '高', className: 'bg-green-900 text-green-300' },
    MEDIUM: { label: '中', className: 'bg-yellow-900 text-yellow-300' },
    LOW: { label: '低', className: 'bg-red-900 text-red-300' }
  };

  const config = tierConfig[tier.toUpperCase()] || { label: tier, className: 'bg-slate-700 text-slate-300' };

  return (
    <span className={clsx('px-2 py-1 text-xs font-semibold rounded', config.className)}>
      {config.label}
    </span>
  );
}

export default MarketDashboard;

