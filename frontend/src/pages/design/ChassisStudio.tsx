/**
 * ChassisStudio - 底盘设计工作室
 * 向导式UI，分4个步骤设计底盘平台
 */
import React, { useState, useEffect } from 'react';
import { useGameContext } from '../../contexts/GameContext';
import { ChassisBlueprint } from '../../components/engineering/ChassisBlueprint';
import { ChassisAnalysisPanel } from '../../components/engineering/ChassisAnalysisPanel';
import { useChassisCalculations } from '../../hooks/useChassisCalculations';
import { calculatePlatformStats } from '../../logic/chassisCalculations';
import { useWizard } from '../../hooks/useWizard';
import { TechSlider, TechSelect } from '../../components/common/inputs';
import { RDBaseLayout, type RDBaseLayoutStep } from '../../components/layouts';
import { 
  ChevronRight, ChevronLeft, Save, Settings, 
  Ruler, Gauge, CheckCircle2
} from 'lucide-react';

interface ChassisDraft {
  // 基础信息
  name: string;
  code: string;
  platform_strategy: 'MODULAR' | 'BESPOKE';
  
  // Step 1: 几何参数
  wheelbase_mm: number;
  track_front_mm: number;
  track_rear_mm: number;
  engine_bay_length_mm: number;
  engine_bay_width_mm: number;
  engine_bay_height_mm: number;
  
  // Step 2: 结构与物理
  material: 'STEEL' | 'ALUMINUM' | 'CARBON'; // 保留用于向后兼容
  material_grade_id: string; // 材料等级ID (如 STEEL_LOW_CARBON, ALUMINIUM_CAST)
  process_id: string; // 制造工艺ID (如 STAMPING, FORGING, CASTING_SAND)
  structure_type: 'LADDER' | 'MONOCOQUE';
  torsional_rigidity_target: number;
  
  // Step 3: 动力学与设置
  layout: 'FF' | 'FR' | 'MR' | 'RR' | 'AWD';
  suspension_front: string;
  suspension_rear: string;
  
  // 平台带宽（仅MODULAR）
  base_wheelbase_mm?: number;
  bandwidth_wheelbase_mm?: number;
  base_track_width_mm?: number;
  bandwidth_track_mm?: number;
}

const WIZARD_STEPS = ['驱动布局', '结构与物理', '几何与硬点', '总结与保存'];

const STEPS: RDBaseLayoutStep[] = [
  { id: 1, name: '驱动布局', icon: Gauge },
  { id: 2, name: '结构与物理', icon: Settings },
  { id: 3, name: '几何与硬点', icon: Ruler },
  { id: 4, name: '总结与保存', icon: CheckCircle2 },
];

export const ChassisStudio: React.FC = () => {
  const { gameState, refreshGameState } = useGameContext();
  const currentYear = gameState?.current_year || 1946;
  
  // 使用 useWizard 管理步骤导航
  const wizard = useWizard({
    steps: WIZARD_STEPS,
    initialStep: 0,
  });
  const [chassisDraft, setChassisDraft] = useState<ChassisDraft>({
    name: '',
    code: '',
    platform_strategy: 'MODULAR',
    wheelbase_mm: 2600,
    track_front_mm: 1500,
    track_rear_mm: 1500,
    engine_bay_length_mm: 800,
    engine_bay_width_mm: 700,
    engine_bay_height_mm: 600,
    material: 'STEEL',
    material_grade_id: 'STEEL_LOW_CARBON', // 默认材料等级
    process_id: 'STAMPING', // 默认制造工艺
    structure_type: 'LADDER',
    torsional_rigidity_target: 50,
    layout: 'FF',
    suspension_front: 'MACPHERSON',
    suspension_rear: 'TWIST_BEAM',
  });
  
  const [chassisFeedback, setChassisFeedback] = useState<any>(null);
  const [isSaving, setIsSaving] = useState(false);
  
  // 实时计算底盘统计数据（使用 API - 物理引擎）
  const chassisStats = useChassisCalculations({
    wheelbase_mm: chassisDraft.wheelbase_mm,
    track_front_mm: chassisDraft.track_front_mm,
    track_rear_mm: chassisDraft.track_rear_mm,
    material_grade_id: chassisDraft.material_grade_id,
    process_id: chassisDraft.process_id,
    structure_type: chassisDraft.structure_type,
    layout: chassisDraft.layout,
    torsional_rigidity_target: chassisDraft.torsional_rigidity_target,
    design_year: currentYear,
    tech_level: 1, // TODO: 从游戏状态获取技术等级
  });

  // R&D 成本和时间的计算（使用旧的游戏逻辑，不是物理引擎）
  const rdStats = calculatePlatformStats({
    wheelbase_mm: chassisDraft.wheelbase_mm,
    track_front_mm: chassisDraft.track_front_mm,
    track_rear_mm: chassisDraft.track_rear_mm,
    material: chassisDraft.material,
    structure_type: chassisDraft.structure_type,
    layout: chassisDraft.layout,
    torsional_rigidity_target: chassisDraft.torsional_rigidity_target,
    platform_strategy: chassisDraft.platform_strategy,
  });
  
  // 生成反馈
  useEffect(() => {
    const generateFeedback = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/engineering/chassis/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...chassisDraft,
            rigidity_rating: chassisDraft.torsional_rigidity_target,
            crash_test_rating: 50.0,
          }),
        });
        const data = await response.json();
        if (data.success) {
          setChassisFeedback(data.feedback);
        }
      } catch (err) {
        console.error('Failed to generate feedback:', err);
      }
    };
    
    generateFeedback();
  }, [chassisDraft]);
  
  // 计算平台带宽（仅MODULAR）
  useEffect(() => {
    if (chassisDraft.platform_strategy === 'MODULAR') {
      setChassisDraft(prev => ({
        ...prev,
        base_wheelbase_mm: prev.wheelbase_mm,
        bandwidth_wheelbase_mm: 200, // 默认±200mm
        base_track_width_mm: (prev.track_front_mm + prev.track_rear_mm) / 2,
        bandwidth_track_mm: 100, // 默认±100mm
      }));
    } else {
      setChassisDraft(prev => ({
        ...prev,
        base_wheelbase_mm: undefined,
        bandwidth_wheelbase_mm: undefined,
        base_track_width_mm: undefined,
        bandwidth_track_mm: undefined,
      }));
    }
  }, [chassisDraft.platform_strategy, chassisDraft.wheelbase_mm, chassisDraft.track_front_mm, chassisDraft.track_rear_mm]);
  
  const handleSave = async () => {
    setIsSaving(true);
    try {
      const companyId = gameState?.playerCompany?.id || 1;
      const currentCash = gameState?.playerCompany?.cash || 0;
      const programCostUSD = rdStats.programCost; // USD
      const programCostM = programCostUSD / 1_000_000; // 转换为百万游戏币
      
      // 前端资金检查（提前验证）
      if (currentCash < programCostM) {
        alert(`资金不足！需要 $${programCostM.toFixed(2)}M，当前资金 $${currentCash.toFixed(2)}M`);
        setIsSaving(false);
        return;
      }
      
      const request = {
        company_id: companyId,
        name: chassisDraft.name,
        code: chassisDraft.code,
        wheelbase_mm: chassisDraft.wheelbase_mm,
        track_front_mm: chassisDraft.track_front_mm,
        track_rear_mm: chassisDraft.track_rear_mm,
        layout: chassisDraft.layout,
        engine_bay_length_mm: chassisDraft.engine_bay_length_mm,
        engine_bay_width_mm: chassisDraft.engine_bay_width_mm,
        engine_bay_height_mm: chassisDraft.engine_bay_height_mm,
        max_cooling_capacity_kw: 150.0,
        material: chassisDraft.material,
        tech_level: 5,
        source_type: chassisDraft.platform_strategy === 'MODULAR' ? 'MODULAR_PLATFORM' : 'BESPOKE',
        is_platform: chassisDraft.platform_strategy === 'MODULAR',
        torsional_rigidity_target: chassisDraft.torsional_rigidity_target,
        rust_protection_level: 'NONE',
        nvh_insulation_mass: 0.0,
        transmission_tunnel_fitted: chassisDraft.layout !== 'FF',
        crumple_zone_length: 0.0,
        fuel_tank_location: 'REAR_AXLE_BEHIND',
        base_wheelbase_mm: chassisDraft.base_wheelbase_mm,
        bandwidth_wheelbase_mm: chassisDraft.bandwidth_wheelbase_mm,
        base_track_width_mm: chassisDraft.base_track_width_mm,
        bandwidth_track_mm: chassisDraft.bandwidth_track_mm,
        // 发送前端计算的成本和周数（已转换为百万游戏币单位）
        program_cost: programCostM, // 百万游戏币（与后端Company.cash单位一致）
        rd_weeks: rdStats.rdTime,
      };
      
      const response = await fetch('http://localhost:8000/api/v1/engineering/chassis/design', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        // 处理HTTP错误
        if (response.status === 402) {
          alert(`资金不足：${data.detail || '无法支付研发费用'}`);
          setIsSaving(false);
          return;
        }
        throw new Error(data.detail || `HTTP ${response.status}`);
      }
      
      if (data.success) {
        // 更新全局资金（乐观更新）
        if (gameState?.playerCompany) {
          // 刷新游戏状态以获取最新的资金数据
          if (refreshGameState) {
            refreshGameState();
          }
        }
        
        // 计算预计完成日期
        const completionDate = data.research_project?.estimated_completion_turn 
          ? `回合 ${data.research_project.estimated_completion_turn}`
          : `${rdStats.rdTime} 周后`;
        
        // 显示成功通知
        alert(`项目已启动！\n研发成本: $${programCostM.toFixed(2)}M\n预计完成: ${completionDate}\n\n请前往"研究"模块查看研发进度。`);
        
        // 重置表单
        setChassisDraft({
          name: '',
          code: '',
          platform_strategy: 'MODULAR',
          wheelbase_mm: 2600,
          track_front_mm: 1500,
          track_rear_mm: 1500,
          engine_bay_length_mm: 800,
          engine_bay_width_mm: 700,
          engine_bay_height_mm: 600,
          material: 'STEEL',
          material_grade_id: 'STEEL_LOW_CARBON',
          process_id: 'STAMPING',
          structure_type: 'LADDER',
          torsional_rigidity_target: 50,
          layout: 'FF',
          suspension_front: 'MACPHERSON',
          suspension_rear: 'TWIST_BEAM',
        });
        wizard.goToStep(0);
      } else {
        alert(`保存失败: ${data.detail || '未知错误'}`);
      }
    } catch (err: any) {
      console.error('Failed to save chassis:', err);
      if (err.message?.includes('资金不足') || err.message?.includes('402')) {
        alert('资金不足，无法启动项目');
      } else {
        alert('保存失败，请检查网络连接');
      }
    } finally {
      setIsSaving(false);
    }
  };
  
  const canProceed = () => {
    // Step 0 (Drivetrain): Layout, name and code must be filled
    if (wizard.currentStepIndex === 0) {
      return !!chassisDraft.layout && !!chassisDraft.name && !!chassisDraft.code;
    }
    // Step 1 (Structure): Check tech tree constraints
    if (wizard.currentStepIndex === 1) {
      // Check structure type
      if (chassisDraft.structure_type === 'MONOCOQUE' && currentYear < 1955) {
        return false;
      }
      // Check material tech requirements
      if (chassisDraft.material === 'ALUMINUM' && currentYear < 1950) {
        return false;
      }
      if (chassisDraft.material === 'CARBON' && currentYear < 1970) {
        return false;
      }
    }
    return true;
  };
  
  return (
    <RDBaseLayout
      title="Chassis Engineering"
      subtitle="底盘设计工作室 - 分步设计底盘平台"
      programCost={rdStats.programCost / 1_000_000}
      steps={STEPS}
      currentStepIndex={wizard.currentStepIndex}
    >
      <div className="p-6">
        {/* Navigation Buttons */}
        <div className="mb-6 flex items-center justify-between">
          <button
            onClick={wizard.prevStep}
            disabled={wizard.isFirst}
            className="flex items-center gap-2 px-4 py-2 rounded-sm font-mono text-sm font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-surface hover:bg-surface-hover text-primary border border-surface-hover"
          >
            <ChevronLeft className="w-4 h-4" />
            上一步
          </button>
          
          {!wizard.isLast ? (
            <button
              onClick={wizard.nextStep}
              disabled={!canProceed()}
              className="flex items-center gap-2 px-4 py-2 rounded-sm font-mono text-sm font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-accent-primary hover:bg-accent-glow text-primary"
            >
              下一步
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <div className="flex flex-col items-end gap-2">
              <button
                onClick={handleSave}
                disabled={
                  isSaving || 
                  !chassisDraft.name || 
                  !chassisDraft.code ||
                  (gameState?.playerCompany?.cash || 0) < (rdStats.programCost / 1_000_000)
                }
                className="flex items-center gap-2 px-4 py-2 rounded-sm font-mono text-sm font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-accent-success hover:bg-green-400 text-primary"
              >
                {isSaving ? (
                  <>
                    <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    提交中...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    COMMIT FUNDS (${(rdStats.programCost / 1_000_000).toFixed(1)}M)
                  </>
                )}
              </button>
              {(gameState?.playerCompany?.cash || 0) < (chassisStats.programCost / 1_000_000) && (
                <span className="text-xs font-mono text-accent-danger">
                  资金不足！需要 ${(rdStats.programCost / 1_000_000).toFixed(2)}M，当前 ${(gameState?.playerCompany?.cash || 0).toFixed(2)}M
                </span>
              )}
            </div>
          )}
        </div>

        <div className="max-w-7xl mx-auto">
          {/* Step 0: Drivetrain Layout */}
          {wizard.currentStepIndex === 0 && (
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="bg-surface border border-accent-glow/30 rounded-sm p-4">
                  <h3 className="font-mono text-accent-primary text-sm font-bold mb-4 uppercase">
                    基础信息
                  </h3>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-mono text-secondary mb-1">平台名称</label>
                      <input
                        type="text"
                        value={chassisDraft.name}
                        onChange={(e) => setChassisDraft({ ...chassisDraft, name: e.target.value })}
                        className="w-full bg-deep border border-surface-hover rounded-sm px-3 py-2 text-sm font-mono text-primary focus:border-accent-primary focus:outline-none"
                        placeholder="例如: C-Platform"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-mono text-secondary mb-1">平台代码</label>
                      <input
                        type="text"
                        value={chassisDraft.code}
                        onChange={(e) => setChassisDraft({ ...chassisDraft, code: e.target.value.toUpperCase() })}
                        className="w-full bg-deep border border-surface-hover rounded-sm px-3 py-2 text-sm font-mono text-primary focus:border-accent-primary focus:outline-none"
                        placeholder="例如: C-PLATFORM"
                      />
                    </div>
                  </div>
                </div>
                
                <div className="bg-surface border border-accent-glow/30 rounded-sm p-4">
                  <h3 className="font-mono text-accent-primary text-sm font-bold mb-4 uppercase">
                    驱动布局
                  </h3>
                  <div className="space-y-4">
                    <TechSelect
                      label="引擎位置与驱动方式"
                      value={chassisDraft.layout}
                      options={[
                        { value: 'FF', label: 'FF (前置前驱)' },
                        { value: 'FR', label: 'FR (前置后驱)' },
                        { value: 'MR', label: 'MR (中置后驱)' },
                        { value: 'RR', label: 'RR (后置后驱)' },
                        { value: 'AWD', label: 'AWD (四驱)' },
                      ]}
                      onChange={(val) => setChassisDraft({ ...chassisDraft, layout: val as any })}
                    />
                    <div className="bg-deep border border-surface-hover rounded-sm p-3 text-xs font-mono text-secondary">
                      <div className="mb-2 font-bold text-accent-primary">布局说明:</div>
                      <div className="space-y-1">
                        <div><span className="text-accent-primary">FF:</span> 前置引擎，前轮驱动 - 空间效率高，成本低</div>
                        <div><span className="text-accent-primary">FR:</span> 前置引擎，后轮驱动 - 平衡性好，需要传动轴</div>
                        <div><span className="text-accent-primary">MR:</span> 中置引擎，后轮驱动 - 最佳重量分配，空间受限</div>
                        <div><span className="text-accent-primary">RR:</span> 后置引擎，后轮驱动 - 紧凑布局，操控特性独特</div>
                        <div><span className="text-accent-primary">AWD:</span> 全轮驱动 - 牵引力最佳，复杂度高</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="space-y-4">
                <ChassisBlueprint
                  wheelbase_mm={chassisDraft.wheelbase_mm}
                  track_front_mm={chassisDraft.track_front_mm}
                  track_rear_mm={chassisDraft.track_rear_mm}
                  engine_bay_length_mm={chassisDraft.engine_bay_length_mm}
                  engine_bay_width_mm={chassisDraft.engine_bay_width_mm}
                  engine_bay_height_mm={chassisDraft.engine_bay_height_mm}
                  layout={chassisDraft.layout}
                  structure_type={chassisDraft.structure_type}
                  showSideView={true}
                />
              </div>
            </div>
          )}
          
          {/* Step 1: Structure & Physics */}
          {wizard.currentStepIndex === 1 && (
            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-1 space-y-4">
                <div className="bg-surface border border-accent-glow/30 rounded-sm p-4">
                  <h3 className="font-mono text-accent-primary text-sm font-bold mb-4 uppercase">
                    材料与结构
                  </h3>
                  <div className="space-y-4">
                    <TechSelect
                      label="材料等级"
                      value={chassisDraft.material_grade_id}
                      options={[
                        // 钢材等级
                        { value: 'STEEL_LOW_CARBON', label: '低碳钢 (Low Carbon Steel)' },
                        { value: 'STEEL_MEDIUM_CARBON', label: '中碳钢 (Medium Carbon Steel)' },
                        { 
                          value: 'STEEL_CHROMOLY', 
                          label: '铬钼钢 (Chromoly Steel)',
                          locked: currentYear < 1960,
                          unlockHint: '需要1960年后的技术解锁'
                        },
                        { 
                          value: 'STEEL_STAINLESS', 
                          label: '不锈钢 (Stainless Steel)',
                          locked: currentYear < 1970,
                          unlockHint: '需要1970年后的技术解锁'
                        },
                        // 铝合金等级
                        { 
                          value: 'ALUMINIUM_CAST', 
                          label: '铸造铝合金 (Cast Aluminum)',
                          locked: currentYear < 1950,
                          unlockHint: '需要1950年后的技术解锁'
                        },
                        { 
                          value: 'ALUMINIUM_FORGED', 
                          label: '锻造铝合金 (Forged Aluminum)',
                          locked: currentYear < 1960,
                          unlockHint: '需要1960年后的技术解锁'
                        },
                        { 
                          value: 'ALUMINIUM_7075', 
                          label: '7075航空铝 (7075 Aluminum)',
                          locked: currentYear < 1970,
                          unlockHint: '需要1970年后的技术解锁'
                        },
                        // 铸铁
                        { value: 'CAST_IRON_STANDARD', label: '标准铸铁 (Cast Iron)' },
                        // 碳纤维
                        { 
                          value: 'CARBON_FIBER_STANDARD', 
                          label: '标准碳纤维 (Carbon Fiber)',
                          locked: currentYear < 1980,
                          unlockHint: '需要1980年后的技术解锁'
                        },
                      ]}
                      onChange={(val) => {
                        const gradeId = val as string;
                        // 根据材料等级推断基础材料类型（用于向后兼容）
                        let material: 'STEEL' | 'ALUMINUM' | 'CARBON' = 'STEEL';
                        if (gradeId.startsWith('ALUMINIUM') || gradeId.startsWith('ALUMINUM')) {
                          material = 'ALUMINUM';
                        } else if (gradeId.startsWith('CARBON')) {
                          material = 'CARBON';
                        }
                        setChassisDraft({ ...chassisDraft, material_grade_id: gradeId, material });
                      }}
                    />
                    <TechSelect
                      label="制造工艺"
                      value={chassisDraft.process_id}
                      options={[
                        { value: 'CASTING_SAND', label: '砂型铸造 (Sand Casting)' },
                        { 
                          value: 'CASTING_DIE', 
                          label: '压铸 (Die Casting)',
                          locked: currentYear < 1950,
                          unlockHint: '需要1950年后的技术解锁'
                        },
                        { 
                          value: 'FORGING', 
                          label: '锻造 (Forging)',
                          locked: currentYear < 1955,
                          unlockHint: '需要1955年后的技术解锁'
                        },
                        { 
                          value: 'FORGING_CLOSED_DIE', 
                          label: '闭式模锻 (Closed Die Forging)',
                          locked: currentYear < 1965,
                          unlockHint: '需要1965年后的技术解锁'
                        },
                        { 
                          value: 'STAMPING', 
                          label: '冲压 (Stamping)',
                          locked: currentYear < 1950,
                          unlockHint: '需要1950年后的技术解锁'
                        },
                        { 
                          value: 'CNC', 
                          label: 'CNC加工 (CNC Machining)',
                          locked: currentYear < 1970,
                          unlockHint: '需要1970年后的技术解锁'
                        },
                        { 
                          value: 'CNC_PRECISION', 
                          label: '精密CNC (Precision CNC)',
                          locked: currentYear < 1980,
                          unlockHint: '需要1980年后的技术解锁'
                        },
                      ]}
                      onChange={(val) => setChassisDraft({ ...chassisDraft, process_id: val as string })}
                    />
                    <TechSelect
                      label="结构类型"
                      value={chassisDraft.structure_type}
                      options={[
                        { value: 'LADDER', label: '非承载式 (Ladder Frame)' },
                        { 
                          value: 'MONOCOQUE', 
                          label: '承载式 (Monocoque)',
                          locked: currentYear < 1955,
                          unlockHint: '需要1955年后的技术解锁'
                        },
                      ]}
                      onChange={(val) => setChassisDraft({ ...chassisDraft, structure_type: val as any })}
                    />
                    <TechSlider
                      label="扭转刚性目标"
                      value={chassisDraft.torsional_rigidity_target}
                      min={1}
                      max={100}
                      step={1}
                      unit=""
                      onChange={(v) => setChassisDraft({ ...chassisDraft, torsional_rigidity_target: v })}
                    />
                  </div>
                </div>
              </div>
              
              <div className="col-span-1 space-y-4">
                <ChassisBlueprint
                  wheelbase_mm={chassisDraft.wheelbase_mm}
                  track_front_mm={chassisDraft.track_front_mm}
                  track_rear_mm={chassisDraft.track_rear_mm}
                  engine_bay_length_mm={chassisDraft.engine_bay_length_mm}
                  engine_bay_width_mm={chassisDraft.engine_bay_width_mm}
                  engine_bay_height_mm={chassisDraft.engine_bay_height_mm}
                  layout={chassisDraft.layout}
                  structure_type={chassisDraft.structure_type}
                  showSideView={true}
                />
              </div>
              
              <div className="col-span-1 space-y-4">
                <ChassisAnalysisPanel
                  feedback={chassisFeedback}
                  estimatedCost={chassisStats.unitCost}
                  estimatedWeight={chassisStats.weight}
                  estimatedRndWeeks={rdStats.rdTime}
                  isLoading={chassisStats.isLoading}
                  error={chassisStats.error}
                  reliabilityScore={chassisStats.reliabilityScore}
                  maxLoad={chassisStats.maxLoad}
                />
              </div>
            </div>
          )}
          
          {/* Step 2: Geometry & Hardpoints */}
          {wizard.currentStepIndex === 2 && (
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="bg-surface border border-accent-glow/30 rounded-sm p-4">
                  <h3 className="font-mono text-accent-primary text-sm font-bold mb-4 uppercase">
                    平台策略
                  </h3>
                  <div className="space-y-3">
                    <label className="flex items-center gap-3 p-3 rounded-sm border cursor-pointer transition-all hover:border-accent-glow/50"
                      style={{
                        borderColor: chassisDraft.platform_strategy === 'MODULAR' ? 'rgba(34, 211, 238, 0.5)' : 'rgb(51, 65, 85)',
                        backgroundColor: chassisDraft.platform_strategy === 'MODULAR' ? 'rgba(34, 211, 238, 0.1)' : 'transparent',
                      }}
                    >
                      <input
                        type="radio"
                        name="platform_strategy"
                        value="MODULAR"
                        checked={chassisDraft.platform_strategy === 'MODULAR'}
                        onChange={(e) => setChassisDraft({ ...chassisDraft, platform_strategy: e.target.value as 'MODULAR' | 'BESPOKE' })}
                        className="w-4 h-4 text-accent-primary"
                      />
                      <div>
                        <div className="font-mono text-primary font-bold">模块化平台</div>
                        <div className="text-xs text-secondary">支持带宽调整，可重用，高R&D成本</div>
                      </div>
                    </label>
                    <label className="flex items-center gap-3 p-3 rounded-sm border cursor-pointer transition-all hover:border-accent-glow/50"
                      style={{
                        borderColor: chassisDraft.platform_strategy === 'BESPOKE' ? 'rgba(34, 211, 238, 0.5)' : 'rgb(51, 65, 85)',
                        backgroundColor: chassisDraft.platform_strategy === 'BESPOKE' ? 'rgba(34, 211, 238, 0.1)' : 'transparent',
                      }}
                    >
                      <input
                        type="radio"
                        name="platform_strategy"
                        value="BESPOKE"
                        checked={chassisDraft.platform_strategy === 'BESPOKE'}
                        onChange={(e) => setChassisDraft({ ...chassisDraft, platform_strategy: e.target.value as 'MODULAR' | 'BESPOKE' })}
                        className="w-4 h-4 text-accent-primary"
                      />
                      <div>
                        <div className="font-mono text-primary font-bold">定制底盘</div>
                        <div className="text-xs text-secondary">固定尺寸，低R&D成本，锁定单一车型</div>
                      </div>
                    </label>
                  </div>
                </div>
                
                <div className="bg-surface border border-accent-glow/30 rounded-sm p-4">
                  <h3 className="font-mono text-accent-primary text-sm font-bold mb-4 uppercase">
                    几何参数
                  </h3>
                  <div className="space-y-4">
                    <TechSlider
                      label="轴距"
                      value={chassisDraft.wheelbase_mm}
                      min={2000}
                      max={3500}
                      step={50}
                      unit="mm"
                      onChange={(v) => setChassisDraft({ ...chassisDraft, wheelbase_mm: v })}
                    />
                    <TechSlider
                      label="前轮距"
                      value={chassisDraft.track_front_mm}
                      min={1200}
                      max={1800}
                      step={10}
                      unit="mm"
                      onChange={(v) => setChassisDraft({ ...chassisDraft, track_front_mm: v })}
                    />
                    <TechSlider
                      label="后轮距"
                      value={chassisDraft.track_rear_mm}
                      min={1200}
                      max={1800}
                      step={10}
                      unit="mm"
                      onChange={(v) => setChassisDraft({ ...chassisDraft, track_rear_mm: v })}
                    />
                    <TechSlider
                      label="引擎舱长度"
                      value={chassisDraft.engine_bay_length_mm}
                      min={600}
                      max={1200}
                      step={10}
                      unit="mm"
                      onChange={(v) => setChassisDraft({ ...chassisDraft, engine_bay_length_mm: v })}
                    />
                    <TechSlider
                      label="引擎舱宽度"
                      value={chassisDraft.engine_bay_width_mm}
                      min={500}
                      max={1000}
                      step={10}
                      unit="mm"
                      onChange={(v) => setChassisDraft({ ...chassisDraft, engine_bay_width_mm: v })}
                    />
                    <TechSlider
                      label="引擎舱高度"
                      value={chassisDraft.engine_bay_height_mm}
                      min={400}
                      max={800}
                      step={10}
                      unit="mm"
                      onChange={(v) => setChassisDraft({ ...chassisDraft, engine_bay_height_mm: v })}
                    />
                  </div>
                </div>
              </div>
              
              <div className="space-y-4">
                <ChassisBlueprint
                  wheelbase_mm={chassisDraft.wheelbase_mm}
                  track_front_mm={chassisDraft.track_front_mm}
                  track_rear_mm={chassisDraft.track_rear_mm}
                  engine_bay_length_mm={chassisDraft.engine_bay_length_mm}
                  engine_bay_width_mm={chassisDraft.engine_bay_width_mm}
                  engine_bay_height_mm={chassisDraft.engine_bay_height_mm}
                  layout={chassisDraft.layout}
                  structure_type={chassisDraft.structure_type}
                  showSideView={true}
                />
                
                {chassisDraft.platform_strategy === 'MODULAR' && (
                  <div className="bg-surface border border-accent-glow/30 rounded-sm p-4">
                    <h3 className="font-mono text-accent-primary text-sm font-bold mb-3 uppercase">
                      平台带宽
                    </h3>
                    <div className="space-y-2 text-xs font-mono">
                      <div className="flex justify-between">
                        <span className="text-secondary">基础轴距:</span>
                        <span className="text-accent-primary">{chassisDraft.base_wheelbase_mm}mm</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-secondary">轴距带宽:</span>
                        <span className="text-accent-primary">±{chassisDraft.bandwidth_wheelbase_mm}mm</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-secondary">基础轮距:</span>
                        <span className="text-accent-primary">{chassisDraft.base_track_width_mm}mm</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-secondary">轮距带宽:</span>
                        <span className="text-accent-primary">±{chassisDraft.bandwidth_track_mm}mm</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Step 3: Summary & Save */}
          {wizard.currentStepIndex === 3 && (
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-surface border border-accent-glow/30 rounded-sm p-6">
                <h3 className="font-mono text-accent-primary text-lg font-bold mb-6 uppercase">
                  平台规格总结
                </h3>
                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-mono text-primary font-bold mb-2">基础信息</h4>
                      <div className="space-y-1 text-sm font-mono">
                        <div className="flex justify-between">
                          <span className="text-secondary">名称:</span>
                          <span className="text-accent-primary">{chassisDraft.name || '未设置'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-secondary">代码:</span>
                          <span className="text-accent-primary">{chassisDraft.code || '未设置'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-secondary">策略:</span>
                          <span className="text-accent-primary">
                            {chassisDraft.platform_strategy === 'MODULAR' ? '模块化平台' : '定制底盘'}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="font-mono text-primary font-bold mb-2">几何参数</h4>
                      <div className="space-y-1 text-sm font-mono">
                        <div className="flex justify-between">
                          <span className="text-secondary">轴距:</span>
                          <span className="text-accent-primary">{chassisDraft.wheelbase_mm}mm</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-secondary">前轮距:</span>
                          <span className="text-accent-primary">{chassisDraft.track_front_mm}mm</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-secondary">后轮距:</span>
                          <span className="text-accent-primary">{chassisDraft.track_rear_mm}mm</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-mono text-primary font-bold mb-2">结构与材料</h4>
                      <div className="space-y-1 text-sm font-mono">
                        <div className="flex justify-between">
                          <span className="text-secondary">材料:</span>
                          <span className="text-accent-primary">{chassisDraft.material}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-secondary">结构:</span>
                          <span className="text-accent-primary">{chassisDraft.structure_type}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-secondary">扭转刚性:</span>
                          <span className="text-accent-primary">{chassisDraft.torsional_rigidity_target}/100</span>
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="font-mono text-primary font-bold mb-2">动力学</h4>
                      <div className="space-y-1 text-sm font-mono">
                        <div className="flex justify-between">
                          <span className="text-secondary">驱动布局:</span>
                          <span className="text-accent-primary">{chassisDraft.layout}</span>
                        </div>
                      </div>
                    </div>
                    
                    {chassisDraft.platform_strategy === 'MODULAR' && (
                      <div>
                        <h4 className="font-mono text-primary font-bold mb-2">平台带宽</h4>
                        <div className="space-y-1 text-sm font-mono">
                          <div className="flex justify-between">
                            <span className="text-secondary">轴距带宽:</span>
                            <span className="text-accent-primary">
                              {chassisDraft.base_wheelbase_mm}mm ± {chassisDraft.bandwidth_wheelbase_mm}mm
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-secondary">轮距带宽:</span>
                            <span className="text-accent-primary">
                              {chassisDraft.base_track_width_mm}mm ± {chassisDraft.bandwidth_track_mm}mm
                            </span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              
              <div>
                <ChassisAnalysisPanel
                  feedback={chassisFeedback}
                  estimatedCost={chassisStats.unitCost}
                  estimatedWeight={chassisStats.weight}
                  estimatedRndWeeks={rdStats.rdTime}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </RDBaseLayout>
  );
};


