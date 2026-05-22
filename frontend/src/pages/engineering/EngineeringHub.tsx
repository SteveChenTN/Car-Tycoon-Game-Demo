import React, { useState, useEffect } from 'react';
import { EngineeringProvider, useEngineering } from '../../contexts/EngineeringContext';
import { EngineDesigner } from './EngineDesigner';
import { VehicleDesigner } from './VehicleDesigner';
import { ChassisStudio } from '../design/ChassisStudio';
import { ChiefEngineer } from '../../components/engineering/ChiefEngineer';
import { ErrorBoundary } from '../../components/ErrorBoundary';
import { listEngines, handleEngineeringError } from '../../services/engineeringService';
import { Wrench, Car, Factory } from 'lucide-react';

/**
 * EngineeringHub - 工程模块主入口
 * 包含两个工作室的切换和AI助手
 */
export const EngineeringHub: React.FC = () => {
  console.log('[EngineeringHub] Component mounting...');
  
  return (
    <ErrorBoundary>
      <EngineeringProvider>
        <EngineeringHubContent />
      </EngineeringProvider>
    </ErrorBoundary>
  );
};

const EngineeringHubContent: React.FC = () => {
  console.log('[EngineeringHubContent] Component mounting...');
  
  const [activeStudio, setActiveStudio] = useState<'engine' | 'chassis' | 'vehicle'>('engine');
  const { setSavedEngines } = useEngineering();

  // 加载已保存的引擎列表
  useEffect(() => {
    console.log('[EngineeringHubContent] Loading engines...');
    loadEngines();
  }, []);

  const loadEngines = async () => {
    try {
      console.log('[EngineeringHubContent] Fetching engines from API...');
      // TODO: 从GameContext获取当前玩家公司ID
      const companyId = 1; // 临时硬编码
      const engines = await listEngines(companyId, true);
      
      console.log('[EngineeringHubContent] Engines loaded:', engines);
      
      // 转换为SavedEngine格式
      const savedEngines = engines.map((e: any) => ({
        id: e.id,
        name: e.name,
        code: e.code,
        bore_mm: 86, // 这些字段在列表API中不返回，需要从详情API获取
        stroke_mm: 86,
        cylinder_count: e.cylinder_count,
        configuration: e.configuration,
        compression_ratio: 10,
        induction_type: 'NA',
        boost_pressure_bar: 0,
        material: 'ALUMINUM',
        valvetrain: 'DOHC',
        fuel_type: 'GASOLINE',
        tech_level: 2,  // 1946年默认值（符合历史限制）
        displacement_cc: e.displacement_cc,
        horsepower: e.horsepower,
        torque_nm: e.torque_nm,
        weight_kg: 150,
        length_mm: 600,
        width_mm: 500,
        height_mm: 600,
        reliability_score: e.reliability_score,
        thermal_load: 0,
        manufacturing_cost: e.cost,
      }));
      
      console.log('[EngineeringHubContent] Saved engines formatted:', savedEngines);
      setSavedEngines(savedEngines);
    } catch (error) {
      console.error('[EngineeringHubContent] Failed to load engines:', handleEngineeringError(error));
    }
  };

  return (
    <div className="h-full flex flex-col bg-slate-950 relative">
      {/* Tab Bar */}
      <div className="bg-slate-900 border-b border-slate-700 px-4 flex items-center gap-2">
        <button
          onClick={() => {
            console.log('[EngineeringHubContent] Switching to Engine Lab');
            setActiveStudio('engine');
          }}
          className={`flex items-center gap-2 px-6 py-3 font-mono text-sm font-bold transition-all ${
            activeStudio === 'engine'
              ? 'bg-cyan-900 text-cyan-400 border-b-2 border-cyan-500'
              : 'text-slate-400 hover:text-cyan-400'
          }`}
        >
          <Wrench className="w-4 h-4" />
          动力实验室
        </button>
        
        <button
          onClick={() => {
            console.log('[EngineeringHubContent] Switching to Chassis Studio');
            setActiveStudio('chassis');
          }}
          className={`flex items-center gap-2 px-6 py-3 font-mono text-sm font-bold transition-all ${
            activeStudio === 'chassis'
              ? 'bg-cyan-900 text-cyan-400 border-b-2 border-cyan-500'
              : 'text-slate-400 hover:text-cyan-400'
          }`}
        >
          <Factory className="w-4 h-4" />
          底盘工作室
        </button>
        
        <button
          onClick={() => {
            console.log('[EngineeringHubContent] Switching to Vehicle Studio');
            setActiveStudio('vehicle');
          }}
          className={`flex items-center gap-2 px-6 py-3 font-mono text-sm font-bold transition-all ${
            activeStudio === 'vehicle'
              ? 'bg-purple-900 text-purple-400 border-b-2 border-purple-500'
              : 'text-slate-400 hover:text-purple-400'
          }`}
        >
          <Car className="w-4 h-4" />
          车辆工作室
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 relative">
        <ErrorBoundary>
          {activeStudio === 'engine' && <EngineDesigner />}
        </ErrorBoundary>
        
        <ErrorBoundary>
          {activeStudio === 'chassis' && <ChassisStudio />}
        </ErrorBoundary>
        
        <ErrorBoundary>
          {activeStudio === 'vehicle' && <VehicleDesigner />}
        </ErrorBoundary>
        
        {/* AI Assistant (Always Visible) */}
        <ErrorBoundary>
          <ChiefEngineer />
        </ErrorBoundary>
      </div>
    </div>
  );
};

