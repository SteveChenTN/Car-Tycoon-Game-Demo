/**
 * ReverseEngineeringLab - 逆向工程实验室
 * 显示竞争对手车辆列表并支持拆解操作
 */
import React, { useState, useEffect } from 'react';
import { Eye, AlertTriangle, Zap, Shield } from 'lucide-react';
import { getCompetitorCars, reverseEngineerCar, type CompetitorCar } from '@/services/researchService';

interface ReverseEngineeringLabProps {
  companyId: number;
  onReverseEngineerComplete?: (result: any) => void;
}

export const ReverseEngineeringLab: React.FC<ReverseEngineeringLabProps> = ({
  companyId,
  onReverseEngineerComplete
}) => {
  const [competitorCars, setCompetitorCars] = useState<CompetitorCar[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCar, setSelectedCar] = useState<CompetitorCar | null>(null);
  const [investmentMultiplier, setInvestmentMultiplier] = useState(1.0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCompetitorCars();
  }, [companyId]);

  const loadCompetitorCars = async () => {
    try {
      setLoading(true);
      const cars = await getCompetitorCars(companyId);
      setCompetitorCars(cars);
    } catch (err: any) {
      setError(err.message || '加载竞争对手车辆失败');
    } finally {
      setLoading(false);
    }
  };

  const handleReverseEngineer = async () => {
    if (!selectedCar) return;

    setIsProcessing(true);
    setError(null);

    try {
      const result = await reverseEngineerCar({
        company_id: companyId,
        target_car_id: selectedCar.id,
        investment_multiplier: investmentMultiplier
      });

      onReverseEngineerComplete?.(result);
      setSelectedCar(null);
      loadCompetitorCars(); // 刷新列表
    } catch (err: any) {
      setError(err.message || '逆向工程失败');
    } finally {
      setIsProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 font-mono">加载竞争对手车辆...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-amber-500/30 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-4">
          <Eye className="w-8 h-8 text-amber-400" />
          <h2 className="text-xl font-bold text-amber-400">逆向工程实验室</h2>
        </div>
        <p className="text-sm text-slate-400 mb-4">
          拆解竞争对手车辆以获取技术数据和生成克隆底盘
        </p>
        <div className="flex items-center gap-2 text-xs text-amber-300 bg-amber-900/20 border border-amber-500/30 rounded p-2">
          <AlertTriangle className="w-4 h-4" />
          <span>警告：克隆底盘在竞争对手所在区域销售时存在法律风险</span>
        </div>
      </div>

      {selectedCar && (
        <div className="bg-slate-900 border border-amber-500/50 rounded-lg p-6">
          <h3 className="text-lg font-bold text-white mb-4">拆解目标：{selectedCar.name}</h3>
          <div className="grid grid-cols-2 gap-4 mb-4 text-sm font-mono">
            <div>
              <span className="text-slate-400">公司：</span>
              <span className="text-white ml-2">{selectedCar.company_name}</span>
            </div>
            <div>
              <span className="text-slate-400">马力：</span>
              <span className="text-white ml-2">{selectedCar.horsepower} HP</span>
            </div>
            <div>
              <span className="text-slate-400">可靠性：</span>
              <span className="text-white ml-2">{selectedCar.reliability.toFixed(1)}</span>
            </div>
            <div>
              <span className="text-slate-400">MSRP：</span>
              <span className="text-white ml-2">${selectedCar.msrp.toLocaleString()}</span>
            </div>
          </div>
          <div className="mb-4">
            <label className="block text-sm font-mono text-slate-400 mb-1">
              投资倍数（影响精度和风险）
            </label>
            <input
              type="range"
              min="0.5"
              max="3.0"
              step="0.1"
              value={investmentMultiplier}
              onChange={(e) => setInvestmentMultiplier(parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-slate-500 mt-1">
              <span>0.5x (快速/低精度)</span>
              <span className="font-mono">{investmentMultiplier.toFixed(1)}x</span>
              <span>3.0x (慢速/高精度)</span>
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setSelectedCar(null)}
              className="px-4 py-2 bg-slate-800 text-slate-300 rounded hover:bg-slate-700"
            >
              取消
            </button>
            <button
              onClick={handleReverseEngineer}
              disabled={isProcessing}
              className="px-4 py-2 bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50 flex items-center gap-2"
            >
              {isProcessing ? '拆解中...' : '开始拆解'}
              <Zap className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="p-3 bg-rose-900/30 border border-rose-500/50 rounded text-rose-400 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        {competitorCars.map((car) => (
          <div
            key={car.id}
            onClick={() => setSelectedCar(car)}
            className={`bg-slate-900 border rounded-lg p-4 cursor-pointer transition-colors ${
              selectedCar?.id === car.id
                ? 'border-amber-500 bg-amber-900/10'
                : 'border-slate-700 hover:border-slate-600'
            }`}
          >
            <div className="flex items-start justify-between mb-2">
              <div>
                <h4 className="font-bold text-white">{car.name}</h4>
                <p className="text-xs text-slate-400">{car.company_name}</p>
              </div>
              <Eye className="w-5 h-5 text-amber-400" />
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono text-slate-400">
              <div>
                <Zap className="w-3 h-3 inline mr-1" />
                {car.horsepower} HP
              </div>
              <div>
                <Shield className="w-3 h-3 inline mr-1" />
                {car.reliability.toFixed(0)}
              </div>
            </div>
          </div>
        ))}
      </div>

      {competitorCars.length === 0 && (
        <div className="text-center py-12 text-slate-400">
          <p>暂无可逆向工程的竞争对手车辆</p>
        </div>
      )}
    </div>
  );
};


