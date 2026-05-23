/**
 * 工厂和生产管理API服务
 */

import axios from 'axios';
import { Factory, ProductionLine, ProductionLineStatus, VehicleDesignSummary } from '../types';

const API_BASE = 'http://localhost:8000';

// ============================================================
// Factory API
// ============================================================

export interface FactoryListResponse {
  factories: Factory[];
  total: number;
}

interface BackendProductionLine {
  id: number;
  name?: string;
  status?: string;
  assigned_design_id?: number | null;
  assigned_design_name?: string | null;
  current_design_id?: number | null;
  current_design_name?: string | null;
  daily_output?: number;
  monthly_capacity?: number;
  quality_index?: number;
  retooling_months_remaining?: number;
  retooling_until_turn?: number | null;
}

interface BackendFactory {
  id: number;
  name: string;
  factory_type?: Factory['factory_type'];
  type?: Factory['factory_type'];
  level?: number;
  capacity_units_per_month?: number;
  capacity?: number;
  current_utilization_rate?: number;
  efficiency_score?: number;
  efficiency?: number;
  is_operational?: boolean;
  lines?: BackendProductionLine[];
  production_lines?: BackendProductionLine[];
}

interface BackendFactoryListResponse {
  factories?: BackendFactory[];
  total?: number;
}

interface BackendFactoryDetailsResponse {
  factory?: BackendFactory;
}

interface BackendDesignSummary {
  id: number;
  name: string;
  body_style?: string;
  estimated_cost?: number;
  manufacturing_cost?: number;
}

function normalizeLineStatus(status?: string): ProductionLineStatus {
  const normalized = (status || '').toLowerCase();
  if (normalized === 'running' || normalized === 'active') return 'active';
  if (normalized === 'retooling') return 'retooling';
  return 'idle';
}

function mapProductionLine(line: BackendProductionLine): ProductionLine {
  const monthlyCapacity = line.monthly_capacity ?? 0;
  return {
    id: line.id,
    name: line.name || `Line ${line.id}`,
    factory_id: 0,
    status: normalizeLineStatus(line.status),
    assigned_design_id: line.assigned_design_id ?? line.current_design_id ?? null,
    assigned_design_name: line.assigned_design_name ?? line.current_design_name ?? null,
    daily_output: line.daily_output ?? Math.round(monthlyCapacity / 30),
    quality_index: line.quality_index ?? 100,
    retooling_months_remaining: line.retooling_months_remaining ?? (line.retooling_until_turn ? 1 : 0),
  };
}

function mapFactory(factory: BackendFactory): Factory {
  const lines = (factory.lines ?? factory.production_lines ?? []).map((line) => ({
    ...mapProductionLine(line),
    factory_id: factory.id,
  }));

  return {
    id: factory.id,
    name: factory.name,
    factory_type: factory.factory_type ?? factory.type ?? 'ASSEMBLY',
    level: factory.level ?? 1,
    capacity_units_per_month: factory.capacity_units_per_month ?? factory.capacity ?? 0,
    current_utilization_rate: factory.current_utilization_rate ?? 0,
    efficiency_score: factory.efficiency_score ?? factory.efficiency ?? 0,
    is_operational: factory.is_operational ?? true,
    lines,
  };
}

/**
 * 获取玩家的所有工厂
 */
export async function getPlayerFactories(companyId: number): Promise<FactoryListResponse> {
  const response = await axios.get(`${API_BASE}/api/v1/factory/list`, {
    params: { company_id: companyId }
  });
  const data = response.data as BackendFactoryListResponse;
  const factories = (data.factories ?? []).map(mapFactory);
  return {
    factories,
    total: data.total ?? factories.length,
  };
}

/**
 * 获取工厂详情（包括生产线状态）
 */
export async function getFactoryDetails(factoryId: number): Promise<Factory> {
  const response = await axios.get(`${API_BASE}/api/v1/factory/${factoryId}`);
  const data = response.data as BackendFactoryDetailsResponse;
  return mapFactory(data.factory ?? (response.data as BackendFactory));
}

// ============================================================
// Production Line API
// ============================================================

export interface AssignProductionPayload {
  line_id: number;
  design_id: number;
}

export interface AssignProductionResponse {
  success: boolean;
  message: string;
  line: ProductionLine;
  retooling_duration: number; // months
}

/**
 * 分配车型到生产线
 */
export async function assignProduction(payload: AssignProductionPayload): Promise<AssignProductionResponse> {
  const response = await axios.post(`${API_BASE}/api/v1/factory/assign`, payload);
  return response.data;
}

/**
 * 停止生产线
 */
export async function stopProduction(lineId: number): Promise<{ success: boolean; message: string }> {
  const response = await axios.post(`${API_BASE}/api/v1/factory/stop`, { line_id: lineId });
  return response.data;
}

/**
 * 获取可用的车型设计列表
 */
export async function getAvailableDesigns(companyId: number): Promise<VehicleDesignSummary[]> {
  const response = await axios.get(`${API_BASE}/api/v1/engineering/designs/available`, {
    params: { company_id: companyId }
  });
  const designs = (response.data.designs || []) as BackendDesignSummary[];
  return designs.map((design) => ({
    id: design.id,
    name: design.name,
    body_style: design.body_style || 'UNKNOWN',
    estimated_cost: design.estimated_cost ?? design.manufacturing_cost ?? 0,
  }));
}
