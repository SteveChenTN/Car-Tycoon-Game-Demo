/**
 * 工厂和生产管理API服务
 */

import axios from 'axios';
import { Factory, ProductionLine, VehicleDesignSummary } from '../types';

const API_BASE = 'http://localhost:8000';

// ============================================================
// Factory API
// ============================================================

export interface FactoryListResponse {
  factories: Factory[];
  total: number;
}

/**
 * 获取玩家的所有工厂
 */
export async function getPlayerFactories(companyId: number): Promise<FactoryListResponse> {
  const response = await axios.get(`${API_BASE}/api/v1/factory/list`, {
    params: { company_id: companyId }
  });
  return response.data;
}

/**
 * 获取工厂详情（包括生产线状态）
 */
export async function getFactoryDetails(factoryId: number): Promise<Factory> {
  const response = await axios.get(`${API_BASE}/api/v1/factory/${factoryId}`);
  return response.data;
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
  return response.data.designs || [];
}

