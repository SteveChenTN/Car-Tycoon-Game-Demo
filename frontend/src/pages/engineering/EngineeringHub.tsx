import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Wrench, Car, Factory } from 'lucide-react';
import { EngineeringProvider, useEngineering, type SavedEngine } from '../../contexts/EngineeringContext';
import { ChiefEngineer } from '../../components/engineering/ChiefEngineer';
import { ErrorBoundary } from '../../components/ErrorBoundary';
import { listEngines, handleEngineeringError, type EngineListItem } from '../../services/engineeringService';
import { ChassisStudio } from '../design/ChassisStudio';
import { EngineDesigner } from './EngineDesigner';
import { VehicleDesigner } from './VehicleDesigner';

type Studio = 'engine' | 'chassis' | 'vehicle';

function toSavedEngine(engine: EngineListItem): SavedEngine {
  return {
    id: engine.id,
    name: engine.name,
    code: engine.code,
    bore_mm: 86,
    stroke_mm: 86,
    cylinder_count: engine.cylinder_count,
    configuration: engine.configuration,
    compression_ratio: 10,
    induction_type: 'NA',
    boost_pressure_bar: 0,
    material: 'ALUMINUM',
    valvetrain: 'DOHC',
    fuel_type: 'GASOLINE',
    tech_level: 2,
    displacement_cc: engine.displacement_cc,
    horsepower: engine.horsepower,
    torque_nm: engine.torque_nm,
    weight_kg: 150,
    length_mm: 600,
    width_mm: 500,
    height_mm: 600,
    reliability_score: engine.reliability_score,
    thermal_load: 0,
    manufacturing_cost: engine.cost,
  };
}

export function EngineeringHub() {
  return (
    <ErrorBoundary>
      <EngineeringProvider>
        <EngineeringHubContent />
      </EngineeringProvider>
    </ErrorBoundary>
  );
}

function EngineeringHubContent() {
  const [activeStudio, setActiveStudio] = useState<Studio>('engine');
  const { setSavedEngines } = useEngineering();

  const loadEngines = useCallback(async () => {
    try {
      const engines = await listEngines(1, true);
      setSavedEngines(engines.map(toSavedEngine));
    } catch (error) {
      console.error('[EngineeringHub] Failed to load engines:', handleEngineeringError(error));
    }
  }, [setSavedEngines]);

  useEffect(() => {
    void loadEngines();
  }, [loadEngines]);

  return (
    <div className="h-full flex flex-col bg-slate-950 relative">
      <div className="bg-slate-900 border-b border-slate-700 px-4 flex items-center gap-2">
        <StudioTab
          active={activeStudio === 'engine'}
          icon={<Wrench className="w-4 h-4" />}
          label="Engine Lab"
          onClick={() => setActiveStudio('engine')}
        />
        <StudioTab
          active={activeStudio === 'chassis'}
          icon={<Factory className="w-4 h-4" />}
          label="Chassis Studio"
          onClick={() => setActiveStudio('chassis')}
        />
        <StudioTab
          active={activeStudio === 'vehicle'}
          icon={<Car className="w-4 h-4" />}
          label="Vehicle Studio"
          tone="purple"
          onClick={() => setActiveStudio('vehicle')}
        />
      </div>

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
        <ErrorBoundary>
          <ChiefEngineer />
        </ErrorBoundary>
      </div>
    </div>
  );
}

interface StudioTabProps {
  active: boolean;
  icon: ReactNode;
  label: string;
  onClick: () => void;
  tone?: 'cyan' | 'purple';
}

function StudioTab({ active, icon, label, onClick, tone = 'cyan' }: StudioTabProps) {
  const activeClass = tone === 'purple'
    ? 'bg-purple-900 text-purple-400 border-b-2 border-purple-500'
    : 'bg-cyan-900 text-cyan-400 border-b-2 border-cyan-500';
  const idleClass = tone === 'purple'
    ? 'text-slate-400 hover:text-purple-400'
    : 'text-slate-400 hover:text-cyan-400';

  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-6 py-3 font-mono text-sm font-bold transition-all ${
        active ? activeClass : idleClass
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
