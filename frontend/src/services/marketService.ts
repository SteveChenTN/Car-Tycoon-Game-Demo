/**
 * 市场和定价API服务
 */

import axios from 'axios';
import { RegionPricing, MarketHeatmapCell } from '../types';

const API_BASE = 'http://localhost:8000';

// ============================================================
// Market Pricing API
// ============================================================

export interface RegionPricingMap {
  [regionId: number]: number; // region_id -> price
}

export interface MarketPricingPayload {
  company_id: number;
  design_id: number;
  regional_prices: RegionPricingMap;
}

export interface MarketPricingResponse {
  success: boolean;
  message: string;
  estimated_monthly_sales: number;
  estimated_revenue: number;
}

/**
 * 提交区域定价策略
 */
export async function submitRegionalPricing(payload: MarketPricingPayload): Promise<MarketPricingResponse> {
  const response = await axios.post(`${API_BASE}/api/v1/market/pricing`, payload);
  return response.data;
}

/**
 * 获取当前市场状况（各区域需求、竞争对手价格）
 */
export async function getMarketOverview(companyId: number): Promise<RegionPricing[]> {
  const response = await axios.get(`${API_BASE}/api/v1/market/overview`, {
    params: { company_id: companyId }
  });
  return response.data.regions || [];
}

/**
 * 获取销售热力图数据
 */
export async function getSalesHeatmap(companyId: number): Promise<MarketHeatmapCell[]> {
  const response = await axios.get(`${API_BASE}/api/v1/market/heatmap`, {
    params: { company_id: companyId }
  });
  // 转换数据格式以匹配前端期望
  const cells = response.data.cells || [];
  return cells.map((cell: any) => ({
    ...cell,
    sales_intensity: cell.intensity || cell.sales_intensity || 0.1
  }));
}

/**
 * 计算估算利润（前端预览用）
 */
export function calculateEstimatedProfit(
  myPrice: number,
  cost: number,
  estimatedVolume: number
): number {
  return (myPrice - cost) * estimatedVolume;
}

