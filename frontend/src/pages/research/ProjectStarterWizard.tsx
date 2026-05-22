/**
 * ProjectStarterWizard - 研发项目启动向导
 * 提供三种R&D路径的入口
 */
import React, { useState } from 'react';
import { Factory, Wrench, Eye, ArrowRight, AlertTriangle } from 'lucide-react';
import { startResearchProject, type ResearchProjectRequest } from '@/services/researchService';

type ProjectType = 'MODULAR_PLATFORM' | 'BESPOKE_CHASSIS' | 'REVERSE_ENGINEER' | null;

interface ProjectStarterWizardProps {
  companyId: number;
  onProjectStarted?: (result: any) => void;
}

export const ProjectStarterWizard: React.FC<ProjectStarterWizardProps> = ({
  companyId,
  onProjectStarted
}) => {
  const [selectedPath, setSelectedPath] = useState<ProjectType>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 路径A：模块化平台表单数据
  const [platformData, setPlatformData] = useState({
    name: '',
    code: '',
    supported_body_styles: ['SEDAN'] as string[],
    min_wheelbase_mm: 2400,
    max_wheelbase_mm: 2800,
    material: 'STEEL' as const,
    tech_level: 5
  });

  // 路径B：定制底盘表单数据
  const [bespokeData, setBespokeData] = useState({
    name: '',
    code: '',
    wheelbase_mm: 2500,
    layout: 'FF' as const,
    material: 'STEEL' as const,
    tech_level: 5
  });

  const handleStartProject = async () => {
    if (!selectedPath) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const request: ResearchProjectRequest = {
        company_id: companyId,
        project_type: selectedPath,
        ...(selectedPath === 'MODULAR_PLATFORM' && {
          platform_name: platformData.name,
          platform_code: platformData.code,
          supported_body_styles: platformData.supported_body_styles,
          min_wheelbase_mm: platformData.min_wheelbase_mm,
          max_wheelbase_mm: platformData.max_wheelbase_mm,
          material: platformData.material,
          tech_level: platformData.tech_level
        }),
        ...(selectedPath === 'BESPOKE_CHASSIS' && {
          chassis_name: bespokeData.name,
          chassis_code: bespokeData.code,
          wheelbase_mm: bespokeData.wheelbase_mm,
          layout: bespokeData.layout,
          material: bespokeData.material,
          tech_level: bespokeData.tech_level
        })
      };

      const result = await startResearchProject(request);
      onProjectStarted?.(result);
      setSelectedPath(null); // 重置选择
    } catch (err: any) {
      setError(err.message || '启动项目失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (selectedPath === null) {
    // 路径选择界面
    return (
      <div className="grid grid-cols-3 gap-4 p-6">
        {/* 路径A：模块化平台 */}
        <button
          onClick={() => setSelectedPath('MODULAR_PLATFORM')}
          className="bg-slate-900 border border-cyan-500/30 rounded-lg p-6 hover:border-cyan-500 transition-colors text-left"
        >
          <Factory className="w-12 h-12 text-cyan-400 mb-4" />
          <h3 className="text-lg font-bold text-cyan-400 mb-2">模块化平台开发</h3>
          <p className="text-sm text-slate-400 mb-4">
            长期战略投资：高R&D成本，低单位成本，高可重用性
          </p>
          <div className="text-xs font-mono text-slate-500 space-y-1">
            <div>成本: $5M</div>
            <div>周期: 50周</div>
            <div className="text-cyan-400 mt-2">✓ 可被多个车型使用</div>
          </div>
        </button>

        {/* 路径B：定制底盘 */}
        <button
          onClick={() => setSelectedPath('BESPOKE_CHASSIS')}
          className="bg-slate-900 border border-purple-500/30 rounded-lg p-6 hover:border-purple-500 transition-colors text-left"
        >
          <Wrench className="w-12 h-12 text-purple-400 mb-4" />
          <h3 className="text-lg font-bold text-purple-400 mb-2">定制底盘开发</h3>
          <p className="text-sm text-slate-400 mb-4">
            快速原型：低R&D成本，高单位成本，锁定单一车型
          </p>
          <div className="text-xs font-mono text-slate-500 space-y-1">
            <div>成本: $500k</div>
            <div>周期: 12周</div>
            <div className="text-rose-400 mt-2 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              高制造成本/无共享部件
            </div>
          </div>
        </button>

        {/* 路径C：逆向工程 */}
        <button
          onClick={() => setSelectedPath('REVERSE_ENGINEER')}
          className="bg-slate-900 border border-amber-500/30 rounded-lg p-6 hover:border-amber-500 transition-colors text-left"
        >
          <Eye className="w-12 h-12 text-amber-400 mb-4" />
          <h3 className="text-lg font-bold text-amber-400 mb-2">逆向工程实验室</h3>
          <p className="text-sm text-slate-400 mb-4">
            快速但高风险：拆解竞争对手车辆，生成克隆底盘
          </p>
          <div className="text-xs font-mono text-slate-500 space-y-1">
            <div>成本: $200k</div>
            <div>周期: 2周</div>
            <div className="text-amber-400 mt-2">⚠️ 法律风险</div>
          </div>
        </button>
      </div>
    );
  }

  // 表单界面
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white">
          {selectedPath === 'MODULAR_PLATFORM' && '模块化平台开发'}
          {selectedPath === 'BESPOKE_CHASSIS' && '定制底盘开发'}
          {selectedPath === 'REVERSE_ENGINEER' && '逆向工程实验室'}
        </h2>
        <button
          onClick={() => setSelectedPath(null)}
          className="text-slate-400 hover:text-white"
        >
          返回
        </button>
      </div>

      {selectedPath === 'MODULAR_PLATFORM' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-mono text-slate-400 mb-1">平台名称</label>
            <input
              type="text"
              value={platformData.name}
              onChange={(e) => setPlatformData({ ...platformData, name: e.target.value })}
              className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-mono text-slate-400 mb-1">平台代码</label>
            <input
              type="text"
              value={platformData.code}
              onChange={(e) => setPlatformData({ ...platformData, code: e.target.value })}
              className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-white font-mono"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-mono text-slate-400 mb-1">最小轴距 (mm)</label>
              <input
                type="number"
                value={platformData.min_wheelbase_mm}
                onChange={(e) => setPlatformData({ ...platformData, min_wheelbase_mm: parseInt(e.target.value) })}
                className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-mono text-slate-400 mb-1">最大轴距 (mm)</label>
              <input
                type="number"
                value={platformData.max_wheelbase_mm}
                onChange={(e) => setPlatformData({ ...platformData, max_wheelbase_mm: parseInt(e.target.value) })}
                className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-white"
              />
            </div>
          </div>
        </div>
      )}

      {selectedPath === 'BESPOKE_CHASSIS' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-mono text-slate-400 mb-1">底盘名称</label>
            <input
              type="text"
              value={bespokeData.name}
              onChange={(e) => setBespokeData({ ...bespokeData, name: e.target.value })}
              className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-mono text-slate-400 mb-1">底盘代码</label>
            <input
              type="text"
              value={bespokeData.code}
              onChange={(e) => setBespokeData({ ...bespokeData, code: e.target.value })}
              className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-white font-mono"
            />
          </div>
          <div>
            <label className="block text-sm font-mono text-slate-400 mb-1">轴距 (mm)</label>
            <input
              type="number"
              value={bespokeData.wheelbase_mm}
              onChange={(e) => setBespokeData({ ...bespokeData, wheelbase_mm: parseInt(e.target.value) })}
              className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-white"
            />
          </div>
        </div>
      )}

      {selectedPath === 'REVERSE_ENGINEER' && (
        <div className="text-center py-8">
          <p className="text-slate-400 mb-4">逆向工程功能需要选择目标车辆</p>
          <p className="text-xs text-slate-500">请使用逆向工程实验室组件</p>
        </div>
      )}

      {error && (
        <div className="mt-4 p-3 bg-rose-900/30 border border-rose-500/50 rounded text-rose-400 text-sm">
          {error}
        </div>
      )}

      {selectedPath !== 'REVERSE_ENGINEER' && (
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={() => setSelectedPath(null)}
            className="px-4 py-2 bg-slate-800 text-slate-300 rounded hover:bg-slate-700"
          >
            取消
          </button>
          <button
            onClick={handleStartProject}
            disabled={isSubmitting}
            className="px-4 py-2 bg-cyan-600 text-white rounded hover:bg-cyan-700 disabled:opacity-50 flex items-center gap-2"
          >
            {isSubmitting ? '启动中...' : '启动项目'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};


