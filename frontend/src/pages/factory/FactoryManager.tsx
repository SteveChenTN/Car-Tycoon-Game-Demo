/**
 * 工厂管理页面
 * 实现基于"生产线槽位"的生产管理
 */

import { useState, useEffect } from 'react';
import { Factory, ProductionLine, VehicleDesignSummary } from '../../types';
import { getPlayerFactories, getAvailableDesigns, assignProduction, stopProduction } from '../../services/factoryService';
import { useGame } from '../../contexts/GameContext';
import clsx from 'clsx';

// ============================================================
// 主组件
// ============================================================

export function FactoryManager() {
  const { gameState } = useGame();
  const [factories, setFactories] = useState<Factory[]>([]);
  const [selectedFactory, setSelectedFactory] = useState<Factory | null>(null);
  const [availableDesigns, setAvailableDesigns] = useState<VehicleDesignSummary[]>([]);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedLine, setSelectedLine] = useState<ProductionLine | null>(null);
  const [loading, setLoading] = useState(false);

  // 加载工厂数据
  useEffect(() => {
    loadFactories();
    loadDesigns();
  }, [gameState]);

  const loadFactories = async () => {
    try {
      const response = await getPlayerFactories(1); // TODO: 获取真实company_id
      setFactories(response.factories);
      if (response.factories.length > 0 && !selectedFactory) {
        setSelectedFactory(response.factories[0]);
      }
    } catch (error) {
      console.error('[FactoryManager] Failed to load factories:', error);
    }
  };

  const loadDesigns = async () => {
    try {
      const designs = await getAvailableDesigns(1); // TODO: 获取真实company_id
      setAvailableDesigns(designs);
    } catch (error) {
      console.error('[FactoryManager] Failed to load designs:', error);
    }
  };

  const handleAssignProduction = async (designId: number) => {
    if (!selectedLine) return;

    setLoading(true);
    try {
      const response = await assignProduction({
        line_id: selectedLine.id,
        design_id: designId
      });

      if (response.success) {
        console.log('[FactoryManager] Production assigned:', response.message);
        await loadFactories(); // 刷新数据
        setShowAssignModal(false);
        setSelectedLine(null);
      }
    } catch (error) {
      console.error('[FactoryManager] Failed to assign production:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStopProduction = async (lineId: number) => {
    setLoading(true);
    try {
      const response = await stopProduction(lineId);
      if (response.success) {
        console.log('[FactoryManager] Production stopped:', response.message);
        await loadFactories();
      }
    } catch (error) {
      console.error('[FactoryManager] Failed to stop production:', error);
    } finally {
      setLoading(false);
    }
  };

  const openAssignModal = (line: ProductionLine) => {
    setSelectedLine(line);
    setShowAssignModal(true);
  };

  return (
    <div className="h-full flex flex-col bg-slate-900 text-slate-100 p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight mb-2">工厂管理</h1>
        <p className="text-slate-400">管理生产线，分配车型生产任务</p>
      </div>

      {/* Factory Selection Tabs */}
      <div className="flex gap-2 mb-6 border-b border-slate-700">
        {factories.map((factory) => (
          <button
            key={factory.id}
            onClick={() => setSelectedFactory(factory)}
            className={clsx(
              'px-4 py-2 font-medium transition-colors border-b-2',
              selectedFactory?.id === factory.id
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            )}
          >
            {factory.name}
          </button>
        ))}
      </div>

      {/* Factory Overview */}
      {selectedFactory && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-800 border border-slate-700 p-4 rounded">
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">类型</div>
            <div className="text-lg font-semibold">
              {selectedFactory.factory_type === 'ASSEMBLY' ? '整车装配' : '零部件'}
            </div>
          </div>
          <div className="bg-slate-800 border border-slate-700 p-4 rounded">
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">月产能</div>
            <div className="text-lg font-semibold font-mono">
              {selectedFactory.capacity_units_per_month.toLocaleString()}
            </div>
          </div>
          <div className="bg-slate-800 border border-slate-700 p-4 rounded">
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">效率评分</div>
            <div className="text-lg font-semibold font-mono">
              {selectedFactory.efficiency_score.toFixed(1)}%
            </div>
          </div>
          <div className="bg-slate-800 border border-slate-700 p-4 rounded">
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">利用率</div>
            <div className="text-lg font-semibold font-mono">
              {(selectedFactory.current_utilization_rate * 100).toFixed(1)}%
            </div>
          </div>
        </div>
      )}

      {/* Production Lines */}
      <div className="flex-1 overflow-auto">
        <div className="space-y-4">
          {selectedFactory?.lines?.map((line) => (
            <ProductionLineCard
              key={line.id}
              line={line}
              onAssign={() => openAssignModal(line)}
              onStop={() => handleStopProduction(line.id)}
              disabled={loading}
            />
          ))}
          {(!selectedFactory?.lines || selectedFactory.lines.length === 0) && (
            <div className="text-center py-12 text-slate-500">
              该工厂暂无生产线数据
            </div>
          )}
        </div>
      </div>

      {/* Assign Modal */}
      {showAssignModal && selectedLine && (
        <AssignProductionModal
          line={selectedLine}
          designs={availableDesigns}
          onAssign={handleAssignProduction}
          onClose={() => {
            setShowAssignModal(false);
            setSelectedLine(null);
          }}
          loading={loading}
        />
      )}
    </div>
  );
}

// ============================================================
// 生产线卡片组件
// ============================================================

interface ProductionLineCardProps {
  line: ProductionLine;
  onAssign: () => void;
  onStop: () => void;
  disabled: boolean;
}

function ProductionLineCard({ line, onAssign, onStop, disabled }: ProductionLineCardProps) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-xl font-bold">{line.name}</h3>
          <div className="flex items-center gap-2 mt-1">
            <LineStatusBadge status={line.status} />
            {line.assigned_design_name && (
              <span className="text-sm text-slate-400">生产: {line.assigned_design_name}</span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          {line.status === 'idle' && (
            <button
              onClick={onAssign}
              disabled={disabled}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded transition-colors"
            >
              分配生产
            </button>
          )}
          {line.status === 'active' && (
            <button
              onClick={onStop}
              disabled={disabled}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded transition-colors"
            >
              停止生产
            </button>
          )}
          {line.status === 'retooling' && (
            <button
              disabled
              className="px-4 py-2 bg-slate-700 text-slate-500 rounded cursor-not-allowed"
            >
              改装中...
            </button>
          )}
        </div>
      </div>

      {/* Status-specific content */}
      {line.status === 'retooling' && (
        <div className="space-y-2">
          <div className="text-sm text-yellow-400 font-medium">
            正在改装生产线以生产 {line.assigned_design_name}
          </div>
          <div className="text-xs text-slate-400 mb-2">
            剩余 {line.retooling_months_remaining} 个月
          </div>
          {/* Hazard Stripes Progress Bar */}
          <div className="h-8 rounded overflow-hidden border border-yellow-600 relative">
            <div 
              className="h-full hazard-stripes"
              style={{ 
                width: `${((3 - line.retooling_months_remaining) / 3) * 100}%`,
                transition: 'width 0.3s ease'
              }}
            />
            <div className="absolute inset-0 flex items-center justify-center text-xs font-mono font-bold text-black mix-blend-difference">
              {Math.round(((3 - line.retooling_months_remaining) / 3) * 100)}%
            </div>
          </div>
        </div>
      )}

      {line.status === 'active' && (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">日产量</div>
            <div className="text-2xl font-mono font-bold text-green-400">
              {line.daily_output}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">质量指数</div>
            <div className="text-2xl font-mono font-bold text-cyan-400">
              {line.quality_index.toFixed(1)}
            </div>
          </div>
        </div>
      )}

      {line.status === 'idle' && (
        <div className="text-center py-6 text-slate-500">
          生产线空闲，点击"分配生产"开始生产
        </div>
      )}
    </div>
  );
}

// ============================================================
// 状态徽章
// ============================================================

function LineStatusBadge({ status }: { status: ProductionLine['status'] }) {
  const statusConfig = {
    idle: { label: '空闲', className: 'bg-slate-700 text-slate-300' },
    retooling: { label: '改装中', className: 'bg-yellow-900 text-yellow-300' },
    active: { label: '运行中', className: 'bg-green-900 text-green-300 animate-pulse' }
  };

  const config = statusConfig[status];

  return (
    <span className={clsx('px-2 py-1 text-xs font-semibold rounded', config.className)}>
      {config.label}
    </span>
  );
}

// ============================================================
// 分配生产Modal
// ============================================================

interface AssignProductionModalProps {
  line: ProductionLine;
  designs: VehicleDesignSummary[];
  onAssign: (designId: number) => void;
  onClose: () => void;
  loading: boolean;
}

function AssignProductionModal({ line, designs, onAssign, onClose, loading }: AssignProductionModalProps) {
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-slate-800 border border-slate-700 rounded-lg w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-700">
          <h2 className="text-2xl font-bold">为 {line.name} 分配生产任务</h2>
          <p className="text-sm text-slate-400 mt-1">选择一个车型设计开始生产</p>
        </div>

        {/* Design List */}
        <div className="flex-1 overflow-auto p-6">
          <div className="space-y-3">
            {designs.map((design) => (
              <button
                key={design.id}
                onClick={() => onAssign(design.id)}
                disabled={loading}
                className="w-full bg-slate-900 hover:bg-slate-700 border border-slate-600 hover:border-cyan-500 rounded-lg p-4 text-left transition-colors disabled:opacity-50"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-semibold text-white">{design.name}</h3>
                    <p className="text-sm text-slate-400">{design.body_style}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-slate-500">估算成本</div>
                    <div className="text-lg font-mono font-bold text-cyan-400">
                      ${design.estimated_cost.toLocaleString()}
                    </div>
                  </div>
                </div>
              </button>
            ))}
            {designs.length === 0 && (
              <div className="text-center py-12 text-slate-500">
                暂无可用的车型设计
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-700 flex justify-end">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors disabled:opacity-50"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  );
}

export default FactoryManager;


