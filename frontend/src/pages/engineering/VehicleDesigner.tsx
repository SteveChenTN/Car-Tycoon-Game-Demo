import React, { useState, useEffect } from 'react';
import { useEngineering } from '../../contexts/EngineeringContext';
import { useGameContext } from '../../contexts/GameContext';
import { checkEngineFitment } from '../../utils/engineeringCalc';
import { Car, Settings, AlertCircle, Loader2, Factory, Wrench, Eye, AlertTriangle } from 'lucide-react';
import { getChassisList } from '@/services/researchService';
import { TechSlider, TechSelect } from '../../components/common/inputs';

/**
 * VehicleDesigner - 车辆工作室
 * 选择引擎 + 设计底盘 + 适配性检查
 */
export const VehicleDesigner: React.FC = () => {
  console.log('[VehicleDesigner] Component mounting...');
  
  const engineeringContext = useEngineering();
  console.log('[VehicleDesigner] Engineering Context:', engineeringContext);
  
  const {
    savedEngines,
    selectedEngine,
    setSelectedEngine,
    chassisDraft,
    setChassisDraft,
    vehicleDraft,
    setVehicleDraft,
    fitmentStatus,
    setFitmentStatus,
    addAIMessage,
  } = engineeringContext;

  const { gameState } = useGameContext();
  const currentYear = gameState?.current_year || 1946;
  
  const [engineSearchTerm, setEngineSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [chassisList, setChassisList] = useState<any[]>([]);
  const [selectedChassisTab, setSelectedChassisTab] = useState<'platform' | 'bespoke' | 'cloned'>('platform');
  const [selectedChassis, setSelectedChassis] = useState<any | null>(null);
  
  // 当选择底盘时，更新底盘草稿
  useEffect(() => {
    if (selectedChassis) {
      setChassisDraft({
        ...chassisDraft,
        wheelbase_mm: selectedChassis.wheelbase_mm || selectedChassis.base_wheelbase_mm || 2500,
        track_front_mm: selectedChassis.track_front_mm || 1500,
        track_rear_mm: selectedChassis.track_rear_mm || 1500,
        layout: selectedChassis.layout || 'FF',
        engine_bay_length_mm: selectedChassis.engine_bay_length_mm || 800,
        engine_bay_width_mm: selectedChassis.engine_bay_width_mm || 700,
        engine_bay_height_mm: selectedChassis.engine_bay_height_mm || 600,
      });
    }
  }, [selectedChassis]);
  
  // 时间门控状态
  const [visibleTabs, setVisibleTabs] = useState<string[]>(['Fundamentals']);
  const [fieldGating, setFieldGating] = useState<Record<string, any>>({});
  const [rustProtectionOptions, setRustProtectionOptions] = useState<string[]>(['NONE']);
  const [fuelTankLocationOptions, setFuelTankLocationOptions] = useState<string[]>(['REAR_AXLE_BEHIND']);
  
  // 反馈状态
  const [chassisFeedback, setChassisFeedback] = useState<any>(null);

  // 加载底盘列表
  useEffect(() => {
    const loadChassis = async () => {
      try {
        const companyId = 1; // TODO: 从GameContext获取
        // 获取底盘列表（默认只返回可用的，即is_available=true）
        const allChassis = await getChassisList(companyId);
        // 额外过滤：确保只显示可用的底盘（开发中的平台不可用）
        const availableChassis = allChassis.filter(c => c.is_available === true);
        setChassisList(availableChassis);
      } catch (err) {
        console.error('Failed to load chassis:', err);
      }
    };
    loadChassis();
  }, []);
  
  // 加载时间门控信息
  useEffect(() => {
    const loadTechGating = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/v1/engineering/chassis/available-tabs?year=${currentYear}`);
        const data = await response.json();
        if (data.success) {
          setVisibleTabs(data.visible_tabs);
        }
        
        const gatingResponse = await fetch(`http://localhost:8000/api/v1/engineering/chassis/field-gating?year=${currentYear}`);
        const gatingData = await gatingResponse.json();
        if (gatingData.success) {
          setFieldGating(gatingData.field_gating);
          setRustProtectionOptions(gatingData.rust_protection_options);
          setFuelTankLocationOptions(gatingData.fuel_tank_location_options);
        }
      } catch (err) {
        console.error('Failed to load tech gating:', err);
      }
    };
    loadTechGating();
  }, [currentYear]);
  
  // 生成反馈（当底盘参数变化时）
  useEffect(() => {
    const generateFeedback = async () => {
      if (!chassisDraft) return;
      
      try {
        const response = await fetch('http://localhost:8000/api/v1/engineering/chassis/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...chassisDraft,
            rigidity_rating: 50.0,
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

  // 初始化完成后设置加载状态
  useEffect(() => {
    console.log('[VehicleDesigner] Initialization check...');
    console.log('[VehicleDesigner] savedEngines:', savedEngines);
    console.log('[VehicleDesigner] chassisDraft:', chassisDraft);
    
    // 防御性检查
    if (chassisDraft && vehicleDraft) {
      setIsLoading(false);
      console.log('[VehicleDesigner] Initialization complete');
    }
  }, [chassisDraft, vehicleDraft, savedEngines]);

  // 当引擎或底盘改变时，重新计算适配性
  useEffect(() => {
    console.log('[VehicleDesigner] Checking fitment...');
    console.log('[VehicleDesigner] selectedEngine:', selectedEngine);
    console.log('[VehicleDesigner] chassisDraft:', chassisDraft);
    
    // 防御性检查
    if (!selectedEngine || !chassisDraft) {
      console.log('[VehicleDesigner] Missing data for fitment check');
      return;
    }
    
    try {
      const fitment = checkEngineFitment(
        selectedEngine.length_mm ?? 600,
        selectedEngine.width_mm ?? 500,
        selectedEngine.height_mm ?? 600,
        chassisDraft.engine_bay_length_mm ?? 800,
        chassisDraft.engine_bay_width_mm ?? 700,
        chassisDraft.engine_bay_height_mm ?? 600
      );
      
      setFitmentStatus?.(fitment);
      
      console.log('[VehicleDesigner] Fitment result:', fitment);
      
      // AI 助手响应
      if (!fitment.fits) {
        addAIMessage?.(
          `❌ 老板，这台${selectedEngine.name}装不进去！你需要：拉长引擎盖、换小一号的引擎、或者换个配置。`
        );
      } else {
        addAIMessage?.(`✅ 引擎适配成功！${selectedEngine.name} 完美装入底盘。`);
      }
    } catch (error) {
      console.error('[VehicleDesigner] Error checking fitment:', error);
    }
  }, [selectedEngine, chassisDraft, setFitmentStatus, addAIMessage]);

  const handleSaveVehicle = () => {
    console.log('[VehicleDesigner] Attempting to save vehicle...');
    
    if (!selectedEngine) {
      alert('请先选择一个引擎！');
      return;
    }
    
    if (fitmentStatus && !fitmentStatus.fits) {
      alert('引擎不适配！无法保存车辆。');
      return;
    }
    
    console.log('[VehicleDesigner] Saving vehicle:', {
      ...vehicleDraft,
      engine_id: selectedEngine.id,
      chassis: chassisDraft,
    });
    alert('车辆设计已保存！（后端集成待完成）');
  };

  // 过滤引擎列表
  const filteredEngines = savedEngines?.filter((eng) =>
    eng?.name?.toLowerCase().includes(engineSearchTerm.toLowerCase()) ||
    eng?.code?.toLowerCase().includes(engineSearchTerm.toLowerCase())
  ) ?? [];

  // 加载状态UI
  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-deep text-primary">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-accent-primary animate-spin mx-auto mb-4" />
          <p className="text-secondary font-mono text-sm">初始化车辆工作室...</p>
        </div>
      </div>
    );
  }

  // 防御性检查
  if (!chassisDraft || !vehicleDraft) {
    return (
      <div className="h-full flex items-center justify-center bg-deep text-primary">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-accent-danger mx-auto mb-4" />
          <p className="text-accent-danger font-mono text-sm">错误：无法加载车辆数据</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 bg-accent-danger hover:bg-accent-danger/80 px-4 py-2 rounded font-mono text-xs"
          >
            重新加载
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-deep text-primary">
      {/* Header */}
      <div className="bg-gradient-to-r from-surface to-deep border-b border-accent-primary/50 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold font-mono text-accent-primary flex items-center gap-3">
              <Car className="w-7 h-7" />
              VEHICLE STUDIO
            </h1>
            <p className="text-secondary text-sm font-mono mt-1">
              车辆设计工作室 - 选择引擎、设计底盘、解决适配
            </p>
          </div>
          <button
            onClick={handleSaveVehicle}
            className="bg-accent-primary hover:bg-accent-glow px-6 py-2 rounded font-mono text-sm font-bold transition-colors"
          >
            💾 保存车辆
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="grid grid-cols-12 gap-4 p-4">
          
          {/* LEFT: Engine Selector */}
          <div className="col-span-3 space-y-4">
            <EngineSelector
              engines={filteredEngines}
              selectedEngine={selectedEngine}
              setSelectedEngine={setSelectedEngine}
              searchTerm={engineSearchTerm}
              setSearchTerm={setEngineSearchTerm}
            />
          </div>

          {/* CENTER: Platform Selector & Vehicle Body */}
          <div className="col-span-9 grid grid-cols-2 gap-4">
            {/* Platform Selector */}
            <div className="space-y-4">
              <ChassisSelector
                chassisList={chassisList}
                selectedTab={selectedChassisTab}
                onTabChange={setSelectedChassisTab}
                selectedChassis={selectedChassis}
                onSelectChassis={setSelectedChassis}
              />
              
              {/* Platform Bandwidth Adjustment (if platform selected) */}
              {selectedChassis && selectedChassis.source_type === 'MODULAR_PLATFORM' && (
                <PlatformBandwidthAdjuster
                  chassis={selectedChassis}
                  onAdjust={(adjusted) => {
                    // 更新底盘草稿以反映调整
                    setChassisDraft({ ...chassisDraft, ...adjusted });
                  }}
                />
              )}
            </div>
            
            {/* Vehicle Body Settings */}
            <div className="space-y-4">
              <VehicleBodySettings vehicle={vehicleDraft} setVehicle={setVehicleDraft} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// Engine Selector (Left Panel)
// ============================================================

interface EngineSelectorProps {
  engines: any[];
  selectedEngine: any;
  setSelectedEngine: (engine: any) => void;
  searchTerm: string;
  setSearchTerm: (term: string) => void;
}

const EngineSelector: React.FC<EngineSelectorProps> = ({
  engines,
  selectedEngine,
  setSelectedEngine,
  searchTerm,
  setSearchTerm,
}) => {
  return (
    <div className="bg-deep border border-accent-primary/30 rounded p-4 h-full flex flex-col">
      <h3 className="font-mono text-accent-primary text-sm font-bold mb-3 uppercase">
        引擎库
      </h3>
      
      {/* Search */}
      <input
        type="text"
        placeholder="搜索引擎..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        className="w-full bg-surface border border-surface-hover rounded px-3 py-2 text-sm font-mono text-primary mb-3 focus:border-accent-primary focus:outline-none"
      />
      
      {/* Engine List */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {engines.length === 0 && (
          <div className="text-center text-muted text-sm font-mono mt-8">
            <AlertCircle className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>没有保存的引擎</p>
            <p className="text-xs mt-1">请先在动力实验室设计引擎</p>
          </div>
        )}
        
        {engines.map((engine) => (
          <div
            key={engine?.id ?? Math.random()}
            onClick={() => setSelectedEngine(engine)}
            className={`p-3 rounded border cursor-pointer transition-all ${
              selectedEngine?.id === engine?.id
                ? 'bg-accent-primary/20 border-accent-primary'
                : 'bg-surface border-surface-hover hover:border-accent-primary/50'
            }`}
          >
            <div className="font-mono text-xs">
              <div className="font-bold text-primary mb-1">{engine?.name ?? 'Unknown'}</div>
              <div className="text-secondary">{engine?.code ?? 'N/A'}</div>
              <div className="mt-2 grid grid-cols-2 gap-1 text-[10px]">
                <div>
                  <span className="text-muted">排量:</span>
                  <span className="text-accent-primary ml-1">{engine?.displacement_cc ?? 0}cc</span>
                </div>
                <div>
                  <span className="text-muted">功率:</span>
                  <span className="text-accent-primary ml-1">{engine?.horsepower ?? 0}HP</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================
// Chassis Selector with Tabs
// ============================================================

interface ChassisSelectorProps {
  chassisList: any[];
  selectedTab: 'platform' | 'bespoke' | 'cloned';
  onTabChange: (tab: 'platform' | 'bespoke' | 'cloned') => void;
  selectedChassis: any | null;
  onSelectChassis: (chassis: any) => void;
}

const ChassisSelector: React.FC<ChassisSelectorProps> = ({
  chassisList,
  selectedTab,
  onTabChange,
  selectedChassis,
  onSelectChassis
}) => {
  const platformChassis = chassisList.filter(c => c.source_type === 'MODULAR_PLATFORM');
  const bespokeChassis = chassisList.filter(c => c.source_type === 'BESPOKE');
  const clonedChassis = chassisList.filter(c => c.source_type === 'CLONED');

  const currentChassisList = 
    selectedTab === 'platform' ? platformChassis :
    selectedTab === 'bespoke' ? bespokeChassis :
    clonedChassis;

  return (
    <div className="bg-deep border border-accent-primary/30 rounded p-4">
      <h3 className="font-mono text-accent-primary text-sm font-bold mb-3 uppercase">
        底盘选择器
      </h3>
      
      {/* Tabs */}
      <div className="flex gap-2 mb-4 border-b border-surface-hover">
        <button
          onClick={() => onTabChange('platform')}
          className={`px-3 py-2 text-xs font-mono transition-colors ${
            selectedTab === 'platform'
              ? 'text-accent-primary border-b-2 border-accent-primary'
              : 'text-secondary hover:text-primary'
          }`}
        >
          <Factory className="w-3 h-3 inline mr-1" />
          我的平台 ({platformChassis.length})
        </button>
        <button
          onClick={() => onTabChange('bespoke')}
          className={`px-3 py-2 text-xs font-mono transition-colors ${
            selectedTab === 'bespoke'
              ? 'text-accent-primary border-b-2 border-accent-primary'
              : 'text-secondary hover:text-primary'
          }`}
        >
          <Wrench className="w-3 h-3 inline mr-1" />
          定制/一次性 ({bespokeChassis.length})
        </button>
        <button
          onClick={() => onTabChange('cloned')}
          className={`px-3 py-2 text-xs font-mono transition-colors ${
            selectedTab === 'cloned'
              ? 'text-accent-warning border-b-2 border-accent-warning'
              : 'text-secondary hover:text-primary'
          }`}
        >
          <Eye className="w-3 h-3 inline mr-1" />
          蓝图/克隆 ({clonedChassis.length})
        </button>
      </div>

      {/* Chassis List */}
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {currentChassisList.length === 0 ? (
          <div className="text-center py-8 text-muted text-xs">
            {selectedTab === 'platform' && '暂无模块化平台'}
            {selectedTab === 'bespoke' && '暂无定制底盘'}
            {selectedTab === 'cloned' && '暂无克隆底盘'}
          </div>
        ) : (
          currentChassisList.map((chassis) => (
            <div
              key={chassis.id}
              onClick={() => onSelectChassis(chassis)}
              className={`p-3 rounded border cursor-pointer transition-all ${
                selectedChassis?.id === chassis.id
                  ? 'bg-accent-primary/20 border-accent-primary'
                  : 'bg-surface border-surface-hover hover:border-accent-primary/50'
              }`}
            >
              <div className="font-mono text-xs">
                <div className="font-bold text-primary mb-1">{chassis.name}</div>
                <div className="text-secondary">{chassis.code}</div>
                <div className="mt-2 grid grid-cols-2 gap-1 text-[10px]">
                  <div>
                    <span className="text-muted">轴距:</span>
                    <span className="text-accent-primary ml-1">{chassis.wheelbase_mm}mm</span>
                  </div>
                  <div>
                    <span className="text-muted">布局:</span>
                    <span className="text-accent-primary ml-1">{chassis.layout}</span>
                  </div>
                </div>
                {chassis.source_type === 'CLONED' && chassis.legal_risk_factor > 0.3 && (
                  <div className="mt-2 flex items-center gap-1 text-accent-warning text-[10px]">
                    <AlertTriangle className="w-3 h-3" />
                    <span>法律风险: {(chassis.legal_risk_factor * 100).toFixed(0)}%</span>
                  </div>
                )}
                {chassis.source_type === 'BESPOKE' && (
                  <div className="mt-2 text-accent-danger text-[10px]">
                    ⚠️ 高单位成本
                  </div>
                )}
                {chassis.source_type === 'MODULAR_PLATFORM' && (
                  <div className="mt-2 text-accent-primary text-[10px]">
                    ✓ 可重用性: {chassis.reusability}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

// ============================================================
// Platform Bandwidth Adjuster
// ============================================================

interface PlatformBandwidthAdjusterProps {
  chassis: any;
  onAdjust: (adjusted: any) => void;
}

const PlatformBandwidthAdjuster: React.FC<PlatformBandwidthAdjusterProps> = ({ chassis, onAdjust }) => {
  const [adjustedWheelbase, setAdjustedWheelbase] = React.useState(chassis.wheelbase_mm || chassis.base_wheelbase_mm);
  const [adaptationCost, setAdaptationCost] = React.useState(0);
  
  React.useEffect(() => {
    if (!chassis.base_wheelbase_mm || !chassis.bandwidth_wheelbase_mm) return;
    
    const deviation = Math.abs(adjustedWheelbase - chassis.base_wheelbase_mm);
    const bandwidthUsage = deviation / chassis.bandwidth_wheelbase_mm;
    
    if (bandwidthUsage <= 1.0) {
      setAdaptationCost(0);
    } else {
      // 每超出10%带宽，增加$50/单位成本
      const costMultiplier = (bandwidthUsage - 1.0) * 0.5; // 超出50% = +25%成本
      setAdaptationCost(Math.round((chassis.cost || 5000) * costMultiplier * 0.1)); // 简化为每10% = $50
    }
    
    onAdjust({ wheelbase_mm: adjustedWheelbase });
  }, [adjustedWheelbase, chassis, onAdjust]);
  
  const minWheelbase = chassis.base_wheelbase_mm - (chassis.bandwidth_wheelbase_mm || 0);
  const maxWheelbase = chassis.base_wheelbase_mm + (chassis.bandwidth_wheelbase_mm || 0);
  
  return (
    <div className="bg-deep border border-accent-primary/30 rounded p-4">
      <h3 className="font-mono text-accent-primary text-sm font-bold mb-3 uppercase flex items-center gap-2">
        <Settings className="w-4 h-4" />
        平台带宽调整
      </h3>
      
      <div className="space-y-3">
        <TechSlider
          label="轴距调整"
          value={adjustedWheelbase}
          min={minWheelbase}
          max={maxWheelbase}
          step={50}
          unit="mm"
          onChange={(v) => setAdjustedWheelbase(v)}
        />
        <div className="flex justify-between text-[10px] font-mono text-muted mt-1">
          <span>{minWheelbase}mm</span>
          <span className="text-accent-primary">基础: {chassis.base_wheelbase_mm}mm</span>
          <span>{maxWheelbase}mm</span>
        </div>
        
        {adaptationCost > 0 && (
          <div className="bg-accent-warning/20 border border-accent-warning/50 rounded p-2">
            <div className="flex items-center gap-2 text-xs font-mono">
              <AlertTriangle className="w-4 h-4 text-accent-warning" />
              <span className="text-accent-warning">
                适配成本: +${adaptationCost}/单位
              </span>
            </div>
          </div>
        )}
        
        {adaptationCost === 0 && adjustedWheelbase !== chassis.base_wheelbase_mm && (
          <div className="text-xs font-mono text-accent-primary">
            ✓ 在带宽范围内，无额外成本
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================
// Vehicle Body Settings (Right Panel)
// ============================================================

interface VehicleBodySettingsProps {
  vehicle: any;
  setVehicle: (draft: any) => void;
}

const VehicleBodySettings: React.FC<VehicleBodySettingsProps> = ({ vehicle, setVehicle }) => {
  return (
    <div className="space-y-4">
      <div className="bg-deep border border-accent-primary/30 rounded p-4">
        <h3 className="font-mono text-accent-primary text-sm font-bold mb-3 uppercase">
          车身设置
        </h3>
        
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-mono text-secondary mb-1">车型名称</label>
            <input
              type="text"
              value={vehicle.model_name}
              onChange={(e) => setVehicle({ model_name: e.target.value })}
              className="w-full bg-surface border border-surface-hover rounded px-2 py-1 text-xs font-mono text-primary focus:border-accent-primary focus:outline-none"
            />
          </div>
          
          <TechSelect
            label="车身样式"
            value={vehicle.body_style}
            options={[
              { value: 'SEDAN', label: '轿车 (SEDAN)' },
              { value: 'COUPE', label: '轿跑 (COUPE)' },
              { value: 'SUV', label: 'SUV' },
              { value: 'WAGON', label: '旅行车 (WAGON)' },
              { value: 'HATCHBACK', label: '掀背 (HATCHBACK)' },
              { value: 'CONVERTIBLE', label: '敞篷 (CONVERTIBLE)' },
            ]}
            onChange={(v) => setVehicle({ body_style: v })}
          />
          
          <TechSelect
            label="细分市场"
            value={vehicle.segment}
            options={[
              { value: 'ECONOMY', label: '经济型' },
              { value: 'COMPACT', label: '紧凑型' },
              { value: 'MIDSIZE', label: '中型' },
              { value: 'FULLSIZE', label: '全尺寸' },
              { value: 'LUXURY', label: '豪华' },
              { value: 'SPORT', label: '运动' },
              { value: 'SUPERCAR', label: '超级跑车' },
            ]}
            onChange={(v) => setVehicle({ segment: v })}
          />
          
          <TechSlider
            label="车身重量"
            value={vehicle.body_weight_kg}
            min={500}
            max={2000}
            step={10}
            unit="kg"
            onChange={(v) => setVehicle({ body_weight_kg: v })}
          />
          
          <TechSlider
            label="风阻系数"
            value={vehicle.drag_coefficient}
            min={0.20}
            max={0.50}
            step={0.01}
            unit="Cd"
            onChange={(v) => setVehicle({ drag_coefficient: v })}
          />
          
          <TechSlider
            label="座位数"
            value={vehicle.seating_capacity}
            min={2}
            max={9}
            step={1}
            unit="座"
            onChange={(v) => setVehicle({ seating_capacity: v })}
          />
          
          <TechSlider
            label="后备箱容积"
            value={vehicle.cargo_volume_liters}
            min={100}
            max={1500}
            step={50}
            unit="L"
            onChange={(v) => setVehicle({ cargo_volume_liters: v })}
          />
        </div>
      </div>
      
      <div className="bg-deep border border-accent-primary/30 rounded p-4">
        <h3 className="font-mono text-accent-primary text-sm font-bold mb-3 uppercase">
          定价
        </h3>
        
        <TechSlider
          label="建议零售价"
          value={vehicle.msrp}
          min={10000}
          max={150000}
          step={1000}
          unit="$"
          onChange={(v) => setVehicle({ msrp: v })}
        />
      </div>
    </div>
  );
};


