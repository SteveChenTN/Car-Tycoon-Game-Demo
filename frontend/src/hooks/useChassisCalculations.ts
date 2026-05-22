/**
 * useChassisCalculations - 底盘计算Hook
 * 使用 API 调用后端 EngineeringCore 进行硬核物理计算
 */
import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export interface ChassisCalculationParams {
  /** 轴距 (mm) */
  wheelbase_mm: number;
  /** 前轮距 (mm) */
  track_front_mm: number;
  /** 后轮距 (mm) */
  track_rear_mm: number;
  /** 材料等级ID (如 STEEL_LOW_CARBON, ALUMINIUM_CAST) */
  material_grade_id: string;
  /** 制造工艺ID (如 STAMPING, FORGING, CASTING_SAND) */
  process_id: string;
  /** 结构类型 */
  structure_type: 'LADDER' | 'MONOCOQUE';
  /** 驱动布局 */
  layout: 'FF' | 'FR' | 'MR' | 'RR' | 'AWD';
  /** 扭转刚性目标 (1-100) */
  torsional_rigidity_target: number;
  /** 设计年份 */
  design_year: number;
  /** 技术等级 */
  tech_level?: number;
}

export interface ChassisStats {
  /** 重量 (kg) */
  weight: number;
  /** 单位成本 (USD) */
  unitCost: number;
  /** 最大载荷 (N) */
  maxLoad?: number;
  /** 可靠性评分 (0-100) */
  reliabilityScore?: number;
  /** 安全系数 */
  safetyFactor?: number;
}

export interface UseChassisCalculationsParams extends ChassisCalculationParams {}

/**
 * 底盘计算Hook
 * 当底盘参数变化时，自动调用 API 计算统计数据
 * 使用防抖（500ms）避免频繁请求
 */
export function useChassisCalculations(params: UseChassisCalculationsParams): ChassisStats & { isLoading: boolean; error: string | null } {
  const [stats, setStats] = useState<ChassisStats>({
    weight: 0,
    unitCost: 0,
    maxLoad: 0,
    reliabilityScore: 0,
    safetyFactor: 0,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  const calculateStats = useCallback(async (calculationParams: UseChassisCalculationsParams) => {
    // 验证参数有效性
    if (
      !calculationParams.wheelbase_mm ||
      !calculationParams.track_front_mm ||
      !calculationParams.track_rear_mm ||
      !calculationParams.material_grade_id ||
      !calculationParams.process_id ||
      !calculationParams.structure_type ||
      !calculationParams.layout
    ) {
      // 返回默认值
      setStats({
        weight: 0,
        unitCost: 0,
        maxLoad: 0,
        reliabilityScore: 0,
        safetyFactor: 0,
      });
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/engineering/calculate-chassis`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          wheelbase_mm: calculationParams.wheelbase_mm,
          track_front_mm: calculationParams.track_front_mm,
          track_rear_mm: calculationParams.track_rear_mm,
          structure_type: calculationParams.structure_type,
          material_id: calculationParams.material_grade_id,
          process_id: calculationParams.process_id,
          design_year: calculationParams.design_year,
          tech_level: calculationParams.tech_level || 1,
          torsional_rigidity_target: calculationParams.torsional_rigidity_target,
          layout: calculationParams.layout,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.success) {
        setStats({
          weight: data.weight_kg || 0,
          unitCost: data.cost || 0,
          maxLoad: data.max_load_n || 0,
          reliabilityScore: data.reliability_score || 0,
          safetyFactor: data.safety_factor || 0,
        });
        setError(null);
      } else {
        throw new Error(data.detail || '计算失败');
      }
    } catch (err) {
      console.error('底盘计算失败:', err);
      setError(err instanceof Error ? err.message : '未知错误');
      // 发生错误时保持旧值，不重置为0
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 使用防抖：等待500ms后用户停止输入再发送请求
  useEffect(() => {
    // 清除之前的定时器
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // 设置新的定时器
    debounceTimerRef.current = setTimeout(() => {
      calculateStats(params);
    }, 500);

    // 清理函数
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [
    params.wheelbase_mm,
    params.track_front_mm,
    params.track_rear_mm,
    params.material_grade_id,
    params.process_id,
    params.structure_type,
    params.layout,
    params.torsional_rigidity_target,
    params.design_year,
    params.tech_level,
    calculateStats,
  ]);

  return {
    ...stats,
    isLoading,
    error,
  };
}
