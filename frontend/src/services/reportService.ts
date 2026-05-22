/**
 * 报告和历史数据API服务
 */

import axios from 'axios';
import { MonthlyReport } from '../types';

const API_BASE = 'http://localhost:8000';

// ============================================================
// Monthly Report API
// ============================================================

/**
 * 获取月度报告
 */
export async function getMonthlyReport(gameId: number, turnNumber: number): Promise<MonthlyReport> {
  const response = await axios.get(`${API_BASE}/api/reports/monthly`, {
    params: { game_id: gameId, turn_number: turnNumber }
  });
  return response.data;
}

/**
 * 获取最新月度报告
 */
export async function getLatestMonthlyReport(gameId: number): Promise<MonthlyReport | null> {
  try {
    const response = await axios.get(`${API_BASE}/api/reports/latest`, {
      params: { game_id: gameId }
    });
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

