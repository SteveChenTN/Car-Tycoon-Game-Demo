import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useEngineering } from '../../contexts/EngineeringContext';
import { useGameContext } from '../../contexts/GameContext';
import { DynoGraph } from '../../components/engineering/DynoGraph';
import { ComponentRichSelect } from '../../components/engineering/ComponentRichSelect';
import { TechSelect, TechSlider } from '../../components/common/inputs';
import type { ComponentInfo } from '../../services/engineeringService';
import {
  simulateEngine,
  getUnlockedComponents,
  createEngine,
  handleEngineeringError,
  type EngineSimulationRequest,
  type EngineSimulationResponse,
  type UnlockedComponentsResponse,
} from '../../services/engineeringService';
import { getFuelOctaneLimit, getMaxTechLevelForYear, validateComponentAvailability } from '../../utils/engineeringCalc';
import { Gauge, Wrench, DollarSign, AlertTriangle, Loader2, Save, AlertCircle } from 'lucide-react';

/**
 * EngineDesigner - 引擎设计器
 * 2列布局：左（控制面板）| 右（测功机室：图表+统计）
 */
export const EngineDesigner: React.FC = () => {
  const engineeringContext = useEngineering();
  const { gameState } = useGameContext();
  const { engineDraft, setEngineDraft } = engineeringContext;

  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingComponents, setIsLoadingComponents] = useState(true);
  const [simulationData, setSimulationData] = useState<EngineSimulationResponse | null>(null);
  const [unlockedComponents, setUnlockedComponents] = useState<UnlockedComponentsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [manufacturingTolerance, setManufacturingTolerance] = useState(0.5);

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const companyIdRef = useRef<number | null>(null);

  // 获取公司ID（从游戏状态）
  useEffect(() => {
    companyIdRef.current = gameState?.playerCompanyId ?? gameState?.player_company_id ?? gameState?.playerCompany?.id ?? null;
  }, [gameState]);

  // 加载解锁的组件
  useEffect(() => {
    const loadComponents = async () => {
      if (!companyIdRef.current) {
        setUnlockedComponents(null);
        setIsLoadingComponents(false);
        return;
      }

      try {
        setIsLoadingComponents(true);
        const data = await getUnlockedComponents(companyIdRef.current);
        console.log('Loaded unlocked components:', data);
        console.log('Components data:', data.components);
        setUnlockedComponents(data);
      } catch (err) {
        console.error('Failed to load unlocked components:', err);
        setError('无法加载解锁的组件列表');
      } finally {
        setIsLoadingComponents(false);
      }
    };

    loadComponents();
  }, [gameState]);

  // 防抖模拟函数
  const debouncedSimulate = useCallback(
    (params: EngineSimulationRequest) => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      debounceTimerRef.current = setTimeout(async () => {
        try {
          setIsLoading(true);
          setError(null);
          const result = await simulateEngine(params);
          setSimulationData(result);
          setWarnings(result.warnings || []);
        } catch (err) {
          const errorMsg = handleEngineeringError(err);
          setError(errorMsg);
          setSimulationData(null);
          setWarnings([]);
        } finally {
          setIsLoading(false);
        }
      }, 500); // 500ms 防抖
    },
    []
  );

  // 当引擎参数改变时，触发模拟
  useEffect(() => {
    if (!companyIdRef.current || !engineDraft) return;

    const params: EngineSimulationRequest = {
      company_id: companyIdRef.current,
      bore_mm: engineDraft.bore_mm,
      stroke_mm: engineDraft.stroke_mm,
      cylinder_count: engineDraft.cylinder_count,
      configuration: engineDraft.configuration,
      compression_ratio: engineDraft.compression_ratio,
      induction_type: engineDraft.induction_type,
      boost_pressure_bar: engineDraft.boost_pressure_bar,
      material: engineDraft.material,
      valvetrain: engineDraft.valvetrain,
      fuel_type: engineDraft.fuel_type,
      tech_level: engineDraft.tech_level,
      manufacturing_tolerance: manufacturingTolerance,
      redline_rpm: engineDraft.redline_rpm, // 传递用户设定的redline
    };

    debouncedSimulate(params);
  }, [engineDraft, manufacturingTolerance, debouncedSimulate]);

  // 保存引擎
  const handleSave = async () => {
    if (!companyIdRef.current || !engineDraft || !simulationData) {
      setError('请先完成引擎设计并等待模拟结果');
      return;
    }

    try {
      setIsSaving(true);
      setError(null);

      const result = await createEngine({
        company_id: companyIdRef.current,
        ...engineDraft,
        name: engineDraft.name || '未命名引擎',
        code: engineDraft.code || `ENG_${Date.now()}`,
      });

      if (result.success) {
        alert(`引擎 "${result.engine.name}" 已成功保存！`);
        // TODO: 刷新引擎列表
      }
    } catch (err) {
      const errorMsg = handleEngineeringError(err);
      setError(errorMsg);
    } finally {
      setIsSaving(false);
    }
  };

  // 计算排量（客户端实时计算）
  const calculateDisplacement = (bore: number, stroke: number, cylinders: number): number => {
    const radius_cm = (bore / 10) / 2;
    const stroke_cm = stroke / 10;
    const volume_cc = Math.PI * radius_cm * radius_cm * stroke_cm * cylinders;
    return Math.round(volume_cc);
  };

  const displacement = calculateDisplacement(
    engineDraft?.bore_mm || 80,
    engineDraft?.stroke_mm || 80,
    engineDraft?.cylinder_count || 4
  );

  // 准备图表数据
  const chartData = simulationData
    ? simulationData.torque_curve.map((t, idx) => ({
        rpm: t.rpm,
        torque: t.torque,
        power: simulationData.hp_curve[idx]?.hp || 0,
      }))
    : [];

  // 防御性检查
  if (!engineDraft) {
    return (
      <div className="h-full flex items-center justify-center bg-deep text-primary">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-accent-danger mx-auto mb-4" />
          <p className="text-accent-danger font-mono text-sm">错误：无法加载引擎数据</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-deep text-primary overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-surface to-deep border-b border-accent-primary/30 px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl md:text-2xl font-bold font-mono text-accent-primary flex items-center gap-3">
              <Wrench className="w-6 h-6 md:w-7 md:h-7" />
              ENGINE DESIGNER
            </h1>
            <p className="text-secondary text-xs md:text-sm font-mono mt-1">
              引擎设计实验室 - 调整参数观察动力曲线
            </p>
          </div>
          <button
            onClick={handleSave}
            disabled={!simulationData || isSaving || isLoading}
            className="bg-accent-primary hover:bg-accent-glow disabled:bg-surface-hover disabled:cursor-not-allowed px-4 md:px-6 py-2 rounded font-mono text-xs md:text-sm font-bold transition-colors flex items-center gap-2"
          >
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                开始开发
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error/Warning Toast */}
      {(error || warnings.length > 0) && (
        <div className="px-6 py-2 flex-shrink-0">
          {error && (
            <div className="bg-accent-danger/20 border border-accent-danger/50 rounded px-4 py-2 mb-2">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-accent-danger" />
                <p className="text-accent-danger/90 font-mono text-xs">{error}</p>
              </div>
            </div>
          )}
          {warnings.map((warning, idx) => (
            <div
              key={idx}
              className="bg-accent-warning/20 border border-accent-warning/50 rounded px-4 py-2 mb-2"
            >
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-accent-warning" />
                <p className="text-accent-warning/90 font-mono text-xs">{warning}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Main Content - 2 Columns (Desktop) / Stacked (Mobile) */}
      <div className="flex-1 flex flex-col md:flex-row gap-4 p-4 overflow-auto min-h-0">
        {/* LEFT: Engineering Controls */}
        <div className="w-full md:w-1/2 lg:w-2/5 space-y-4 overflow-y-auto">
          <ControlPanel
            engineDraft={engineDraft}
            setEngineDraft={setEngineDraft}
            unlockedComponents={unlockedComponents}
            isLoadingComponents={isLoadingComponents}
            displacement={displacement}
            manufacturingTolerance={manufacturingTolerance}
            setManufacturingTolerance={setManufacturingTolerance}
            currentYear={gameState?.current_year || 1946}
            maxSafeRPM={simulationData?.stats.max_safe_rpm}
          />
        </div>

        {/* RIGHT: Dyno Room (Visualization) */}
        <div className="w-full md:w-1/2 lg:w-3/5 space-y-4 overflow-y-auto">
          {/* Chart */}
          <div className="bg-surface border border-accent-primary/20 rounded p-4">
            {isLoading ? (
              <div className="flex items-center justify-center h-[350px]">
                <div className="text-center">
                  <Loader2 className="w-8 h-8 text-accent-primary animate-spin mx-auto mb-2" />
                  <p className="text-secondary font-mono text-xs">模拟中...</p>
                </div>
              </div>
            ) : simulationData ? (
              <DynoGraph data={chartData} maxRpm={simulationData.stats.redline_rpm} />
            ) : (
              <div className="flex items-center justify-center h-[350px]">
                <div className="text-center text-muted">
                  <div className="text-5xl mb-4">📊</div>
                  <p className="font-mono text-sm">调整参数以查看动力曲线</p>
                </div>
              </div>
            )}
          </div>

          {/* Stats Panel */}
          {simulationData && (
            <StatsPanel stats={simulationData.stats} />
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================================
// Control Panel Component
// ============================================================

interface ControlPanelProps {
  engineDraft: any;
  setEngineDraft: (draft: Partial<any>) => void;
  unlockedComponents: UnlockedComponentsResponse | null;
  isLoadingComponents: boolean;
  displacement: number;
  manufacturingTolerance: number;
  setManufacturingTolerance: (value: number) => void;
  currentYear: number;
  maxSafeRPM?: number; // MPS计算的最大安全转速上限
}

const ControlPanel: React.FC<ControlPanelProps> = ({
  engineDraft,
  setEngineDraft,
  unlockedComponents,
  isLoadingComponents,
  displacement,
  manufacturingTolerance,
  setManufacturingTolerance,
  currentYear,
  maxSafeRPM,
}) => {
  const getComponentOptions = (category: string): ComponentInfo[] => {
    if (!unlockedComponents) {
      console.log(`[getComponentOptions] No unlockedComponents for category: ${category}`);
      return [];
    }
    
    const components = unlockedComponents.components[category as keyof typeof unlockedComponents.components] || [];
    console.log(`[getComponentOptions] Category: ${category}, Components:`, components);
    
    return components.map((component) =>
      typeof component === 'string' ? { value: component } : component
    );
  };
  
  const getOptions = (category: string): Array<{ value: string; label: string; locked?: boolean }> => {
    if (!unlockedComponents) return [];

    const components = unlockedComponents.components[category as keyof typeof unlockedComponents.components] || [];
    const labels: Record<string, string> = {
      // Fuel Systems
      GASOLINE: '汽油 (GASOLINE)',
      DIESEL: '柴油 (DIESEL)',
      E85: 'E85 乙醇',
      LPG: 'LPG 液化气',
      // Materials
      CAST_IRON: '铸铁 (便宜/重)',
      ALUMINUM: '铝合金 (平衡)',
      MAGNESIUM: '镁合金 (轻/贵)',
      // Valvetrains
      OHV: 'OHV (顶置气门)',
      SOHC: 'SOHC (单顶凸)',
      DOHC: 'DOHC (双顶凸)',
      VARIABLE: 'VARIABLE (可变)',
      // Induction Types
      NA: '自然吸气 (NA)',
      TURBO: '涡轮增压 (TURBO)',
      TWINTURBO: '双涡轮 (TWIN)',
      SUPERCHARGED: '机械增压 (SC)',
      // Configurations
      INLINE: '直列 (INLINE)',
      V: 'V型 (V)',
      BOXER: '水平对置 (BOXER)',
      VR: 'VR型',
      W: 'W型',
    };

    return components.map((component) => {
      const value = typeof component === 'string' ? component : component.value;
      return {
        value,
        label: labels[value] || value,
        locked: false,
      };
    });
  };

  return (
    <div className="space-y-4">
      {/* Basic Parameters */}
      <div className="bg-surface border border-accent-primary/20 rounded p-4">
        <h3 className="font-mono text-accent-primary text-sm font-bold mb-3 uppercase">基础参数</h3>

        <TechSlider
          label="缸径 (Bore)"
          value={engineDraft.bore_mm}
          min={60}
          max={120}
          step={1}
          unit="mm"
          onChange={(v) => setEngineDraft({ bore_mm: v })}
        />

        <TechSlider
          label="行程 (Stroke)"
          value={engineDraft.stroke_mm}
          min={60}
          max={120}
          step={1}
          unit="mm"
          onChange={(v) => setEngineDraft({ stroke_mm: v })}
        />

        {/* Displacement Display */}
        <div className="mb-3 p-2 bg-surface-hover/50 rounded border border-accent-primary/10">
          <div className="flex justify-between text-xs font-mono">
            <span className="text-secondary">排量 (Displacement):</span>
            <span className="text-accent-primary font-bold">{displacement} cc</span>
          </div>
        </div>

        <TechSelect
          label="缸数"
          value={engineDraft.cylinder_count}
          options={[
            { value: 3, label: 'I3' },
            { value: 4, label: 'I4' },
            { value: 6, label: 'I6/V6' },
            { value: 8, label: 'V8' },
            { value: 10, label: 'V10' },
            { value: 12, label: 'V12' },
          ]}
          onChange={(v) => setEngineDraft({ cylinder_count: Number(v) })}
        />

        <TechSelect
          label="配置"
          value={engineDraft.configuration}
          options={getOptions('configurations').map(opt => ({ value: opt.value, label: opt.label, locked: opt.locked }))}
          onChange={(v) => setEngineDraft({ configuration: v })}
        />
      </div>

      {/* Performance Tuning */}
      <div className="bg-surface border border-accent-primary/20 rounded p-4">
        <h3 className="font-mono text-accent-primary text-sm font-bold mb-3 uppercase">性能调校</h3>

        <TechSlider
          label="压缩比"
          value={engineDraft.compression_ratio}
          min={7}
          max={14}
          step={0.1}
          unit=":1"
          onChange={(v) => setEngineDraft({ compression_ratio: v })}
        />
        
        {/* 压缩比限制警告 */}
        {(() => {
          const maxCR = getFuelOctaneLimit(currentYear, engineDraft.fuel_type);
          const exceedsLimit = engineDraft.compression_ratio > maxCR;
          
          if (exceedsLimit) {
            return (
              <div className="mb-3 p-2 bg-accent-danger/20 border border-accent-danger/50 rounded">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-accent-danger mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-xs font-mono text-accent-danger font-bold">
                      警告：压缩比过高！
                    </p>
                    <p className="text-xs font-mono text-accent-danger/80 mt-1">
                      CR {engineDraft.compression_ratio.toFixed(1)}:1 超过 {currentYear}年燃料限制（最大 ~{maxCR.toFixed(1)}:1）
                    </p>
                    <p className="text-xs font-mono text-accent-danger/60 mt-1">
                      可能导致爆震，大幅降低可靠性和效率
                    </p>
                  </div>
                </div>
              </div>
            );
          }
          return null;
        })()}

        <ComponentRichSelect
          label="进气方式"
          value={engineDraft.induction_type}
          options={getComponentOptions('induction_types')}
          isLoading={isLoadingComponents}
          onChange={(v) => setEngineDraft({ induction_type: v })}
        />
        
        {/* 进气方式验证警告 */}
        {(() => {
          const maxTechLevel = getMaxTechLevelForYear(currentYear);
          const effectiveTechLevel = Math.min(engineDraft.tech_level, maxTechLevel);
          const validation = validateComponentAvailability(
            'induction', engineDraft.induction_type, currentYear, effectiveTechLevel
          );
          
          if (!validation.isValid) {
            return (
              <div className="mb-3 p-2 bg-accent-danger/20 border border-accent-danger/50 rounded">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-accent-danger mt-0.5 flex-shrink-0" />
                  <p className="text-xs font-mono text-accent-danger/80">{validation.errorMessage}</p>
                </div>
              </div>
            );
          }
          return null;
        })()}

        {engineDraft.induction_type !== 'NA' && (
          <TechSlider
            label="增压压力"
            value={engineDraft.boost_pressure_bar}
            min={0.5}
            max={2.5}
            step={0.1}
            unit="bar"
            onChange={(v) => setEngineDraft({ boost_pressure_bar: v })}
          />
        )}

        <ComponentRichSelect
          label="配气机构"
          value={engineDraft.valvetrain}
          options={getComponentOptions('valvetrains')}
          isLoading={isLoadingComponents}
          onChange={(v) => setEngineDraft({ valvetrain: v })}
        />
        
        {/* 配气机构验证警告 */}
        {(() => {
          const maxTechLevel = getMaxTechLevelForYear(currentYear);
          const effectiveTechLevel = Math.min(engineDraft.tech_level, maxTechLevel);
          const validation = validateComponentAvailability(
            'valvetrain', engineDraft.valvetrain, currentYear, effectiveTechLevel
          );
          
          if (!validation.isValid) {
            return (
              <div className="mb-3 p-2 bg-accent-danger/20 border border-accent-danger/50 rounded">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-accent-danger mt-0.5 flex-shrink-0" />
                  <p className="text-xs font-mono text-accent-danger/80">{validation.errorMessage}</p>
                </div>
              </div>
            );
          }
          return null;
        })()}
        
        {/* 红线转速控制 */}
        {maxSafeRPM && (
          <>
            <TechSlider
              label="红线转速 (Redline RPM)"
              value={engineDraft.redline_rpm || maxSafeRPM}
              min={2000}
              max={maxSafeRPM}
              step={100}
              unit=" RPM"
              onChange={(v) => setEngineDraft({ redline_rpm: v })}
            />
            <div className="mb-3 p-2 bg-surface-hover/50 rounded border border-accent-primary/10">
              <div className="text-xs font-mono space-y-1">
                <div className="flex justify-between">
                  <span className="text-secondary">MPS上限:</span>
                  <span className="text-accent-primary font-bold">{maxSafeRPM} RPM</span>
                </div>
                <div className="text-muted text-[10px]">
                  基于活塞平均速度限制，可设置更低转速以优化特定RPM性能
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Materials & Tech */}
      <div className="bg-surface border border-accent-primary/20 rounded p-4">
        <h3 className="font-mono text-accent-primary text-sm font-bold mb-3 uppercase">材料与技术</h3>

        <ComponentRichSelect
          label="材料"
          value={engineDraft.material}
          options={getComponentOptions('materials')}
          isLoading={isLoadingComponents}
          onChange={(v) => setEngineDraft({ material: v })}
        />
        
        {/* 材料验证警告 */}
        {(() => {
          const maxTechLevel = getMaxTechLevelForYear(currentYear);
          const effectiveTechLevel = Math.min(engineDraft.tech_level, maxTechLevel);
          const validation = validateComponentAvailability(
            'material', engineDraft.material, currentYear, effectiveTechLevel
          );
          
          if (!validation.isValid) {
            return (
              <div className="mb-3 p-2 bg-accent-danger/20 border border-accent-danger/50 rounded">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-accent-danger mt-0.5 flex-shrink-0" />
                  <p className="text-xs font-mono text-accent-danger/80">{validation.errorMessage}</p>
                </div>
              </div>
            );
          }
          return null;
        })()}

        <ComponentRichSelect
          label="燃料"
          value={engineDraft.fuel_type}
          options={getComponentOptions('fuel_systems')}
          isLoading={isLoadingComponents}
          onChange={(v) => setEngineDraft({ fuel_type: v })}
        />
        
        {/* 燃料验证警告（暂时不强制验证） */}
        {(() => {
          const maxTechLevel = getMaxTechLevelForYear(currentYear);
          const effectiveTechLevel = Math.min(engineDraft.tech_level, maxTechLevel);
          const validation = validateComponentAvailability(
            'fuel', engineDraft.fuel_type, currentYear, effectiveTechLevel
          );
          
          if (!validation.isValid) {
            return (
              <div className="mb-3 p-2 bg-accent-warning/20 border border-accent-warning/50 rounded">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-accent-warning mt-0.5 flex-shrink-0" />
                  <p className="text-xs font-mono text-accent-warning/80">{validation.errorMessage}</p>
                </div>
              </div>
            );
          }
          return null;
        })()}

        <TechSlider
          label="技术等级 (Tech Level)"
          value={engineDraft.tech_level}
          min={1}
          max={10}
          step={1}
          unit=""
          onChange={(v) => setEngineDraft({ tech_level: v })}
        />
        {/* 技术等级限制警告 */}
        {(() => {
          const maxTechLevel = getMaxTechLevelForYear(currentYear);
          const exceedsLimit = engineDraft.tech_level > maxTechLevel;
          
          if (exceedsLimit) {
            return (
              <div className="mb-3 p-2 bg-accent-danger/20 border border-accent-danger/50 rounded">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-accent-danger mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-xs font-mono text-accent-danger font-bold">
                      警告：技术等级超过年份限制！
                    </p>
                    <p className="text-xs font-mono text-accent-danger/80 mt-1">
                      技术等级 {engineDraft.tech_level} 超过 {currentYear} 年的限制（最大 {maxTechLevel}）
                    </p>
                    <p className="text-xs font-mono text-accent-danger/60 mt-1">
                      引擎将使用有效技术等级 {maxTechLevel} 进行计算，保存时将被拒绝
                    </p>
                  </div>
                </div>
              </div>
            );
          }
          
          return (
            <div className="mb-3 p-2 bg-surface-hover/50 rounded border border-accent-primary/10">
              <div className="text-xs font-mono text-secondary">
                影响材料质量、制造精度和热管理能力（1=基础，10=顶级）
              </div>
              <div className="text-xs font-mono text-muted mt-1">
                {currentYear}年最大允许等级: {maxTechLevel}
              </div>
            </div>
          );
        })()}
        
        <TechSlider
          label="制造公差 (Manufacturing Tolerances)"
          value={manufacturingTolerance}
          min={0}
          max={1}
          step={0.05}
          unit=""
          onChange={(v) => setManufacturingTolerance(v)}
        />
        
        {/* 制造公差影响预览 */}
        <div className="mb-3 p-2 bg-surface-hover/50 rounded border border-accent-primary/10">
          <div className="text-xs font-mono space-y-1">
            <div className="flex justify-between">
              <span className="text-secondary">工程时间:</span>
              <span className={manufacturingTolerance >= 0.8 ? 'text-accent-warning' : manufacturingTolerance <= 0.3 ? 'text-accent-success' : 'text-primary'}>
                {manufacturingTolerance >= 0.8 ? '+50%' : manufacturingTolerance <= 0.3 ? '-20%' : '正常'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-secondary">单位成本:</span>
              <span className={manufacturingTolerance >= 0.8 ? 'text-accent-warning' : manufacturingTolerance <= 0.3 ? 'text-accent-success' : 'text-primary'}>
                {manufacturingTolerance >= 0.8 ? '+30%' : manufacturingTolerance <= 0.3 ? '-15%' : '正常'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-secondary">可靠性:</span>
              <span className={manufacturingTolerance >= 0.8 ? 'text-accent-success' : manufacturingTolerance <= 0.3 ? 'text-accent-danger' : 'text-primary'}>
                {manufacturingTolerance >= 0.8 ? '+5%' : manufacturingTolerance <= 0.3 ? '-3%' : '正常'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-secondary">性能:</span>
              <span className={manufacturingTolerance >= 0.8 ? 'text-accent-success' : manufacturingTolerance <= 0.3 ? 'text-accent-danger' : 'text-primary'}>
                {manufacturingTolerance >= 0.8 ? '+2%' : manufacturingTolerance <= 0.3 ? '-1%' : '正常'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// Stats Panel Component
// ============================================================

interface StatsPanelProps {
  stats: EngineSimulationResponse['stats'];
}

const StatsPanel: React.FC<StatsPanelProps> = ({ stats }) => {
  return (
    <div className="space-y-4">
      {/* Performance */}
      <div className="bg-deep border border-accent-primary/30 rounded p-4">
        <h3 className="font-mono text-accent-primary text-sm font-bold mb-3 uppercase flex items-center gap-2">
          <Gauge className="w-4 h-4" />
          性能输出
        </h3>
        <div className="space-y-2 text-sm font-mono">
          <StatRow label="排量" value={`${stats.displacement_cc} cc`} />
          <StatRow label="最大功率" value={`${stats.max_horsepower} HP`} highlight="accent-primary" />
          <StatRow label="最大扭矩" value={`${stats.max_torque_nm} Nm`} highlight="accent-warning" />
          <StatRow label="红线转速" value={`${stats.redline_rpm} RPM`} />
        </div>
      </div>

      {/* Physical */}
      <div className="bg-deep border border-accent-primary/30 rounded p-4">
        <h3 className="font-mono text-accent-primary text-sm font-bold mb-3 uppercase">物理尺寸</h3>
        <div className="space-y-2 text-sm font-mono">
          <StatRow label="重量" value={`${stats.weight_kg} kg`} />
          <StatRow label="长度" value={`${stats.length_mm} mm`} />
          <StatRow label="宽度" value={`${stats.width_mm} mm`} />
          <StatRow label="高度" value={`${stats.height_mm} mm`} />
        </div>
      </div>

      {/* Quality */}
      <div className="bg-deep border border-accent-primary/30 rounded p-4">
        <h3 className="font-mono text-accent-primary text-sm font-bold mb-3 uppercase flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          质量评估
        </h3>
        <div className="space-y-2 text-sm font-mono">
          <div className="flex justify-between items-center">
            <span className="text-secondary">可靠性</span>
            <div className="flex items-center gap-2">
              <div className="w-32 h-2 bg-surface-hover rounded overflow-hidden">
                <div
                  className={`h-full ${
                    stats.reliability > 70
                      ? 'bg-accent-success'
                      : stats.reliability > 40
                      ? 'bg-accent-warning'
                      : 'bg-accent-danger'
                  }`}
                  style={{ width: `${Math.min(100, stats.reliability)}%` }}
                />
              </div>
              <span
                className={`font-bold ${
                  stats.reliability > 70
                    ? 'text-accent-success'
                    : stats.reliability > 40
                    ? 'text-accent-warning'
                    : 'text-accent-danger'
                }`}
              >
                {stats.reliability.toFixed(1)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Economics */}
      <div className="bg-deep border border-accent-primary/30 rounded p-4">
        <h3 className="font-mono text-accent-primary text-sm font-bold mb-3 uppercase flex items-center gap-2">
          <DollarSign className="w-4 h-4" />
          成本分析
        </h3>
        <div className="space-y-2 text-sm font-mono">
          <StatRow label="制造成本" value={`$${stats.cost.toLocaleString()}`} highlight="accent-success" />
        </div>
      </div>
    </div>
  );
};

// ============================================================
// Reusable Components
// ============================================================

interface StatRowProps {
  label: string;
  value: string;
  highlight?: 'accent-primary' | 'accent-warning' | 'accent-success';
}

const StatRow: React.FC<StatRowProps> = ({ label, value, highlight }) => {
  const colorClass = highlight
    ? {
        'accent-primary': 'text-accent-primary',
        'accent-warning': 'text-accent-warning',
        'accent-success': 'text-accent-success',
      }[highlight]
    : 'text-primary';

  return (
    <div className="flex justify-between">
      <span className="text-secondary">{label}</span>
      <span className={`${colorClass} font-bold`}>{value}</span>
    </div>
  );
};
