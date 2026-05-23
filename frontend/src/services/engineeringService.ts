/**
 * 工程模块API服务
 * 处理与后端的所有工程设计相关请求
 */

import axios from 'axios';
import { EngineDesign, ChassisDesign, VehicleDesign } from '../contexts/EngineeringContext';

const API_BASE = 'http://localhost:8000';

// ============================================================
// Engine API
// ============================================================

export interface EngineDesignPayload extends EngineDesign {
  company_id: number;
}

export interface EngineResponse {
  success: boolean;
  engine: {
    id: number;
    name: string;
    code: string;
    displacement_cc: number;
    horsepower: number;
    torque_nm: number;
    weight_kg: number;
    dimensions: {
      length_mm: number;
      width_mm: number;
      height_mm: number;
    };
    reliability_score: number;
    thermal_load: number;
    manufacturing_cost: number;
  };
  warnings?: string[];
}

/**
 * 模拟引擎设计（不保存）
 * 返回动力曲线和统计信息
 */
export interface EngineSimulationRequest {
  company_id: number;
  bore_mm: number;
  stroke_mm: number;
  cylinder_count: number;
  configuration: string;
  compression_ratio: number;
  induction_type: string;
  boost_pressure_bar: number;
  material: string;
  valvetrain: string;
  fuel_type: string;
  tech_level: number;
  manufacturing_tolerance?: number; // 0.0-1.0, default 0.5
  redline_rpm?: number; // 用户设定的红线转速（可选，如果不提供则使用MPS计算的上限）
}

export interface EngineSimulationResponse {
  success: boolean;
  torque_curve: Array<{ rpm: number; torque: number }>;
  hp_curve: Array<{ rpm: number; hp: number }>;
  stats: {
    displacement_cc: number;
    max_horsepower: number;
    max_torque_nm: number;
    redline_rpm: number;
    max_safe_rpm?: number; // 最大安全转速（MPS上限）
    thermal_efficiency?: number; // 热效率
    weight_kg: number;
    length_mm: number;
    width_mm: number;
    height_mm: number;
    reliability: number;
    thermal_load: number;
    cost: number;
  };
  warnings?: string[];
}

export async function simulateEngine(
  payload: EngineSimulationRequest
): Promise<EngineSimulationResponse> {
  const response = await axios.post(
    `${API_BASE}/api/v1/engineering/engine/simulate`,
    payload
  );
  return response.data;
}

/**
 * 组件信息（包含熟悉度）
 */
export interface ComponentInfo {
  value: string;
  familiarity_level?: number; // 1-10
  cost_modifier?: number; // 成本修正（负数表示降低成本）
  reliability_modifier?: number; // 可靠性修正（正数表示提升）
}

/**
 * 获取解锁的组件列表
 */
export type ComponentEntry = ComponentInfo | string;

export interface UnlockedComponentsResponse {
  success: boolean;
  components: {
    fuel_systems: ComponentEntry[];
    materials: ComponentEntry[];
    valvetrains: ComponentEntry[];
    induction_types: ComponentEntry[];
    configurations: ComponentEntry[];
  };
  current_year: number;
}

export async function getUnlockedComponents(
  companyId: number
): Promise<UnlockedComponentsResponse> {
  const response = await axios.get(
    `${API_BASE}/api/v1/engineering/components/unlocked`,
    { params: { company_id: companyId } }
  );
  return response.data;
}

/**
 * 设计并保存新引擎
 */
export async function createEngine(payload: EngineDesignPayload): Promise<EngineResponse> {
  const response = await axios.post(`${API_BASE}/api/v1/engineering/engine/design`, payload);
  return response.data;
}

/**
 * 获取引擎详情
 */
export interface EngineListItem {
  id: number;
  name: string;
  code: string;
  displacement_cc: number;
  horsepower: number;
  torque_nm: number;
  configuration: EngineDesign['configuration'];
  cylinder_count: number;
  reliability_score: number;
  cost: number;
}

type RequestParams = Record<string, string | number | boolean>;

export async function getEngine(engineId: number): Promise<EngineResponse> {
  const response = await axios.get(`${API_BASE}/api/v1/engineering/engine/${engineId}`);
  return response.data;
}

/**
 * 列出所有引擎
 */
export async function listEngines(companyId?: number, availableOnly: boolean = false): Promise<EngineListItem[]> {
  const params: RequestParams = {};
  if (companyId) params.company_id = companyId;
  if (availableOnly) params.available_only = true;
  
  const response = await axios.get(`${API_BASE}/api/v1/engineering/engines`, { params });
  return response.data;
}

// ============================================================
// Chassis API
// ============================================================

export interface ChassisDesignPayload extends ChassisDesign {
  company_id: number;
}

export interface ChassisResponse {
  success: boolean;
  chassis: {
    id: number;
    name: string;
    code: string;
    wheelbase_mm: number;
    layout: string;
    material: string;
    weight_kg: number;
    rigidity_rating: number;
    crash_test_rating: number;
    manufacturing_cost: number;
    is_platform: boolean;
    platform_family?: string;
  };
}

/**
 * 设计并保存新底盘
 */
export async function createChassis(payload: ChassisDesignPayload): Promise<ChassisResponse> {
  const response = await axios.post(`${API_BASE}/api/v1/engineering/chassis/design`, payload);
  return response.data;
}

/**
 * 列出所有底盘
 */
export interface ChassisListItem {
  id: number;
  name: string;
  code: string;
  wheelbase_mm: number;
  track_front_mm?: number;
  track_rear_mm?: number;
  layout: ChassisDesign['layout'];
  material: ChassisDesign['material'];
  is_platform: boolean;
  platform_family?: string | null;
  cost: number;
  source_type: 'MODULAR_PLATFORM' | 'BESPOKE' | 'CLONED';
  is_available: boolean;
  development_turn?: number | null;
  reusability?: string | number | null;
  legal_risk_factor?: number | null;
  quality_cap?: number | null;
  original_competitor_id?: number | null;
  manufacturing_efficiency?: number;
  reliability_penalty?: number;
}

export async function listChassis(companyId?: number, availableOnly: boolean = false): Promise<ChassisListItem[]> {
  const params: RequestParams = {};
  if (companyId) params.company_id = companyId;
  if (availableOnly) params.available_only = true;
  
  const response = await axios.get(`${API_BASE}/api/v1/engineering/chassis`, { params });
  return response.data;
}

// ============================================================
// Vehicle API
// ============================================================

export interface VehicleDesignPayload extends VehicleDesign {
  company_id: number;
}

export interface VehicleResponse {
  success: boolean;
  car: {
    id: number;
    name: string;
    model_name: string;
    trim_code: string;
    body_style: string;
    segment: string;
    performance: {
      zero_to_hundred_kph_sec: number;
      top_speed_kph: number;
      quarter_mile_sec: number;
      fuel_economy_l_100km: number;
      power_to_weight_ratio: number;
    };
    weight: {
      total_kg: number;
      engine_kg: number;
      chassis_kg: number;
      body_kg: number;
    };
    reliability_score: number;
    manufacturing_cost: number;
    msrp: number;
    compatibility: {
      status: string;
      notes: string;
    };
  };
  message: string;
  warnings: string[];
}

/**
 * 设计并保存新车辆
 */
export async function createVehicle(payload: VehicleDesignPayload): Promise<VehicleResponse> {
  const response = await axios.post(`${API_BASE}/api/v1/engineering/car/design`, payload);
  return response.data;
}

/**
 * 检查引擎与底盘的兼容性
 */
export async function checkCompatibility(
  engineId: number,
  chassisId: number
): Promise<{
  compatible: boolean;
  message: string;
  details: Record<string, unknown>;
}> {
  const response = await axios.post(`${API_BASE}/api/v1/engineering/compatibility/check`, null, {
    params: { engine_id: engineId, chassis_id: chassisId },
  });
  return response.data;
}

/**
 * 列出所有车辆
 */
export interface VehicleListItem {
  id: number;
  name: string;
  model_name?: string;
  trim_code?: string;
  body_style: string;
  segment?: string;
  msrp?: number;
  manufacturing_cost?: number;
  in_production?: boolean;
}

export async function listVehicles(companyId?: number, inProduction: boolean = false): Promise<VehicleListItem[]> {
  const params: RequestParams = {};
  if (companyId) params.company_id = companyId;
  if (inProduction) params.in_production = true;
  
  const response = await axios.get(`${API_BASE}/api/v1/engineering/cars`, { params });
  return response.data;
}

// ============================================================
// Error Handling
// ============================================================

/**
 * 统一错误处理
 */
export function handleEngineeringError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.response) {
      // 服务器返回错误
      const detail = error.response.data?.detail;
      if (typeof detail === 'string') {
        return detail;
      } else if (detail?.message) {
        return detail.message;
      }
      return `服务器错误: ${error.response.status}`;
    } else if (error.request) {
      return '无法连接到服务器，请检查后端是否运行';
    }
  }
  return error instanceof Error ? error.message : '未知错误';
}
