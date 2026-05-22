import React, { createContext, useContext, useState, ReactNode } from 'react';

// ============================================================
// Type Definitions
// ============================================================

export interface EngineDesign {
  name: string;
  code: string;
  bore_mm: number;
  stroke_mm: number;
  cylinder_count: number;
  configuration: 'INLINE' | 'V' | 'BOXER' | 'VR' | 'W';
  compression_ratio: number;
  induction_type: 'NA' | 'TURBO' | 'SUPERCHARGED' | 'TWINTURBO';
  boost_pressure_bar: number;
  material: 'CAST_IRON' | 'ALUMINUM' | 'MAGNESIUM';
  valvetrain: 'OHV' | 'SOHC' | 'DOHC' | 'VARIABLE';
  fuel_type: 'GASOLINE' | 'DIESEL' | 'E85' | 'LPG';
  tech_level: number;
  redline_rpm?: number; // 用户设定的红线转速（可选）
}

export interface EngineCalculated {
  displacement_cc: number;
  horsepower: number;
  torque_nm: number;
  weight_kg: number;
  length_mm: number;
  width_mm: number;
  height_mm: number;
  reliability_score: number;
  thermal_load: number;
  manufacturing_cost: number;
}

export interface SavedEngine extends EngineDesign, EngineCalculated {
  id: number;
}

export interface ChassisDesign {
  name: string;
  code: string;
  wheelbase_mm: number;
  track_front_mm: number;
  track_rear_mm: number;
  layout: 'FF' | 'FR' | 'MR' | 'RR' | 'AWD';
  engine_bay_length_mm: number;
  engine_bay_width_mm: number;
  engine_bay_height_mm: number;
  max_cooling_capacity_kw: number;
  material: 'STEEL' | 'ALUMINUM' | 'CARBON';
  tech_level: number;
}

export interface VehicleDesign {
  name: string;
  model_name: string;
  trim_code: string;
  engine_id: number | null;
  chassis_id: number | null;
  body_style: string;
  body_weight_kg: number;
  drag_coefficient: number;
  frontal_area_sqm: number;
  seating_capacity: number;
  cargo_volume_liters: number;
  segment: string;
  msrp: number;
}

export interface FitmentCheck {
  fits: boolean;
  message: string;
  engineVolume: number;
  engineBayVolume: number;
}

// ============================================================
// Context Definition
// ============================================================

interface EngineeringContextType {
  // Engine Design State
  engineDraft: EngineDesign;
  engineCalculated: EngineCalculated | null;
  setEngineDraft: (draft: Partial<EngineDesign>) => void;
  setEngineCalculated: (calc: EngineCalculated | null) => void;
  
  // Saved Engines
  savedEngines: SavedEngine[];
  setSavedEngines: (engines: SavedEngine[]) => void;
  
  // Chassis Design State
  chassisDraft: ChassisDesign;
  setChassisDraft: (draft: Partial<ChassisDesign>) => void;
  
  // Vehicle Design State
  vehicleDraft: VehicleDesign;
  setVehicleDraft: (draft: Partial<VehicleDesign>) => void;
  
  // Fitment Check
  fitmentStatus: FitmentCheck | null;
  setFitmentStatus: (status: FitmentCheck | null) => void;
  
  // Selected Engine for Vehicle Design
  selectedEngine: SavedEngine | null;
  setSelectedEngine: (engine: SavedEngine | null) => void;
  
  // AI Assistant Messages
  aiMessages: string[];
  addAIMessage: (message: string) => void;
  clearAIMessages: () => void;
}

const EngineeringContext = createContext<EngineeringContextType | undefined>(undefined);

// ============================================================
// Default Values
// ============================================================

const DEFAULT_ENGINE: EngineDesign = {
  name: 'New Engine',
  code: 'ENG_001',
  bore_mm: 86,
  stroke_mm: 86,
  cylinder_count: 4,
  configuration: 'INLINE',
  compression_ratio: 10.5,
  induction_type: 'NA',
  boost_pressure_bar: 0,
  material: 'ALUMINUM',
  valvetrain: 'DOHC',
  fuel_type: 'GASOLINE',
  tech_level: 2,  // 默认值，会根据当前年份调整
};

const DEFAULT_CHASSIS: ChassisDesign = {
  name: 'New Chassis',
  code: 'CHS_001',
  wheelbase_mm: 2700,
  track_front_mm: 1540,
  track_rear_mm: 1540,
  layout: 'FF',
  engine_bay_length_mm: 800,
  engine_bay_width_mm: 700,
  engine_bay_height_mm: 600,
  max_cooling_capacity_kw: 100,
  material: 'STEEL',
  tech_level: 2,  // 默认值，会根据当前年份调整
};

const DEFAULT_VEHICLE: VehicleDesign = {
  name: 'New Vehicle',
  model_name: 'Model X',
  trim_code: 'TRIM_001',
  engine_id: null,
  chassis_id: null,
  body_style: 'SEDAN',
  body_weight_kg: 800,
  drag_coefficient: 0.30,
  frontal_area_sqm: 2.5,
  seating_capacity: 5,
  cargo_volume_liters: 400,
  segment: 'COMPACT',
  msrp: 25000,
};

// ============================================================
// Provider Component
// ============================================================

export const EngineeringProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [engineDraft, setEngineDraftState] = useState<EngineDesign>(DEFAULT_ENGINE);
  const [engineCalculated, setEngineCalculated] = useState<EngineCalculated | null>(null);
  const [savedEngines, setSavedEngines] = useState<SavedEngine[]>([]);
  
  const [chassisDraft, setChassisDraftState] = useState<ChassisDesign>(DEFAULT_CHASSIS);
  const [vehicleDraft, setVehicleDraftState] = useState<VehicleDesign>(DEFAULT_VEHICLE);
  
  const [fitmentStatus, setFitmentStatus] = useState<FitmentCheck | null>(null);
  const [selectedEngine, setSelectedEngine] = useState<SavedEngine | null>(null);
  
  const [aiMessages, setAIMessages] = useState<string[]>([]);

  const setEngineDraft = (draft: Partial<EngineDesign>) => {
    setEngineDraftState((prev) => ({ ...prev, ...draft }));
  };

  const setChassisDraft = (draft: Partial<ChassisDesign>) => {
    setChassisDraftState((prev) => ({ ...prev, ...draft }));
  };

  const setVehicleDraft = (draft: Partial<VehicleDesign>) => {
    setVehicleDraftState((prev) => ({ ...prev, ...draft }));
  };

  const addAIMessage = (message: string) => {
    setAIMessages((prev) => [...prev, message]);
  };

  const clearAIMessages = () => {
    setAIMessages([]);
  };

  const value: EngineeringContextType = {
    engineDraft,
    engineCalculated,
    setEngineDraft,
    setEngineCalculated,
    
    savedEngines,
    setSavedEngines,
    
    chassisDraft,
    setChassisDraft,
    
    vehicleDraft,
    setVehicleDraft,
    
    fitmentStatus,
    setFitmentStatus,
    
    selectedEngine,
    setSelectedEngine,
    
    aiMessages,
    addAIMessage,
    clearAIMessages,
  };

  return (
    <EngineeringContext.Provider value={value}>
      {children}
    </EngineeringContext.Provider>
  );
};

// ============================================================
// Hook
// ============================================================

export const useEngineering = () => {
  const context = useContext(EngineeringContext);
  if (!context) {
    throw new Error('useEngineering must be used within EngineeringProvider');
  }
  return context;
};

