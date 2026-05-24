/**
 * 报告和历史数据API服务
 */

import axios from 'axios';
import { MonthlyReport } from '../types';
import { api, apiPaths } from './apiClient';

export interface FinancialHistoryPoint {
  turn: number;
  year: number;
  month: number;
  revenue: number;
  expenses: number;
  net_income: number;
  cash: number;
  cash_change: number;
  units_sold: number;
}

export interface PLStatementData {
  revenue: number;
  cogs: number;
  gross_profit: number;
  rd_cost: number;
  marketing_cost: number;
  admin_cost: number;
  operating_income: number;
  interest: number;
  tax: number;
  net_income: number;
}

export interface CashFlowBridgeData {
  starting_cash: number;
  ending_cash: number;
  cash_change: number;
  net_income: number;
  debt_principal_change: number;
  other_cash_flow: number;
  lines: Array<{
    label: string;
    amount: number;
    kind: string;
  }>;
}

export interface MarketShareData {
  company: string;
  share: number;
  color: string;
}

export interface FinancialReportPageData {
  success: boolean;
  unit: string;
  history: FinancialHistoryPoint[];
  pl_statement: PLStatementData | null;
  cash_flow: CashFlowBridgeData | null;
  balance_sheet: {
    cash: number;
    inventory: number;
    total_assets: number;
    total_liabilities: number;
    shareholder_equity: number;
  } | null;
  cost_breakdown: MonthlyReport['financials']['cost_breakdown'] | null;
  market_share: MarketShareData[];
}

// ============================================================
// Monthly Report API
// ============================================================

/**
 * 获取月度报告
 */
export async function getMonthlyReport(gameId: number, turnNumber: number): Promise<MonthlyReport> {
  const response = await api.get(apiPaths.games.scoped(gameId, '/reports/monthly'), {
    params: { turn_number: turnNumber }
  });
  return response.data;
}

/**
 * 获取最新月度报告
 */
export async function getLatestMonthlyReport(gameId: number): Promise<MonthlyReport | null> {
  try {
    const response = await api.get(apiPaths.games.scoped(gameId, '/reports/latest'));
    return response.data;
  } catch (error) {
    // 如果端点不存在（404），返回null而不是抛出错误
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      console.log('[reportService] Reports endpoint not available yet');
      return null;
    }
    console.error('[reportService] Failed to get latest report:', error);
    throw error;
  }
}

/**
 * 获取报表页所需的真实财务数据
 */
export async function getFinancialReportPage(
  gameId: number,
  companyId: number
): Promise<FinancialReportPageData> {
  const response = await api.get(apiPaths.games.scoped(gameId, '/reports/financial'), {
    params: { company_id: companyId }
  });
  return response.data;
}
