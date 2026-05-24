/**
 * 技术树和研发 API 服务
 */

import { apiPaths, apiUrl } from './apiClient';

// ============================================================
// Types
// ============================================================

export interface TechNodeEffects {
  unlock_configurations?: string[];
  unlock_materials?: string[];
  unlock_induction?: string[];
  unlock_components?: string[];
  unlock_valvetrain?: string[];
  unlock_powertrain?: string[];
  tech_level_bonus?: number;
  weight_reduction_percent?: number;
  fuel_efficiency_bonus?: number;
  power_bonus_percent?: number;
  volumetric_efficiency_bonus?: number;
  drag_reduction_percent?: number;
  top_speed_bonus_percent?: number;
  handling_bonus?: number;
  chassis_weight_reduction?: number;
  rigidity_bonus?: number;
  crash_rating_bonus?: number;
  prestige_bonus?: number;
}

export interface TechNode {
  id: string;
  name: string;
  description: string;
  cost: number;
  research_time_turns: number;
  unlock_requirements: string[];
  category: string;
  effects: TechNodeEffects;
  // UI 状态（前端维护）
  status?: 'locked' | 'available' | 'researching' | 'completed';
  progress?: number; // 0-100
  researchedAt?: number; // turn number
}

export interface TechCategory {
  name: string;
  color: string;
}

export interface TechTree {
  nodes: TechNode[];
  categories: Record<string, TechCategory>;
}

export interface ResearchProgress {
  tech_id: string;
  company_id: number;
  started_at_turn: number;
  completed_at_turn?: number;
  progress_percent: number;
  status: 'in_progress' | 'completed';
}

// ============================================================
// Tech Tree API
// ============================================================

/**
 * 获取技术树结构（从 assets/data/tech_tree.json）
 */
export async function getTechTree(): Promise<TechTree> {
  try {
    // 直接从静态资源加载
    const response = await fetch('/assets/data/tech_tree.json');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Failed to load tech tree:', error);
    // 返回 mock 数据作为降级
    return getMockTechTree();
  }
}

/**
 * 获取公司的研发进度
 */
export async function getResearchProgress(companyId: number): Promise<ResearchProgress[]> {
  try {
    const response = await fetch(apiUrl(apiPaths.legacy.v1('research', '/progress'), { company_id: companyId }));
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Failed to get research progress:', error);
    return [];
  }
}

/**
 * 开始研发某个技术
 */
export async function startResearch(
  companyId: number,
  techId: string
): Promise<{ success: boolean; message?: string; error?: string }> {
  try {
    const response = await fetch(apiUrl(apiPaths.legacy.v1('research', '/start')), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        company_id: companyId,
        tech_id: techId,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to start research:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

// ============================================================
// Mock Data (Fallback)
// ============================================================

function getMockTechTree(): TechTree {
  return {
    nodes: [
      {
        id: 'basic_engine_design',
        name: '基础引擎设计',
        description: '掌握基本的四冲程引擎设计原理',
        cost: 5000,
        research_time_turns: 2,
        unlock_requirements: [],
        category: 'engine',
        effects: {
          unlock_configurations: ['INLINE'],
          unlock_materials: ['CAST_IRON'],
          tech_level_bonus: 0,
        },
        status: 'completed',
      },
      {
        id: 'aluminum_casting',
        name: '铝合金铸造',
        description: '解锁铝合金引擎制造技术',
        cost: 15000,
        research_time_turns: 4,
        unlock_requirements: ['basic_engine_design'],
        category: 'materials',
        effects: {
          unlock_materials: ['ALUMINUM'],
          weight_reduction_percent: 5,
        },
        status: 'available',
      },
      {
        id: 'turbocharging_tech',
        name: '涡轮增压技术',
        description: '研发涡轮增压系统',
        cost: 25000,
        research_time_turns: 6,
        unlock_requirements: ['basic_engine_design'],
        category: 'engine',
        effects: {
          unlock_induction: ['TURBO'],
          unlock_components: ['turbocharger_small'],
        },
        status: 'available',
      },
      {
        id: 'v_configuration',
        name: 'V型引擎布局',
        description: '掌握V型引擎设计，更紧凑',
        cost: 20000,
        research_time_turns: 5,
        unlock_requirements: ['basic_engine_design'],
        category: 'engine',
        effects: {
          unlock_configurations: ['V'],
        },
        status: 'available',
      },
      {
        id: 'dohc_valvetrain',
        name: '双顶置凸轮轴',
        description: 'DOHC配气机构，提升高转速性能',
        cost: 18000,
        research_time_turns: 4,
        unlock_requirements: ['basic_engine_design'],
        category: 'engine',
        effects: {
          unlock_valvetrain: ['DOHC'],
          volumetric_efficiency_bonus: 5,
        },
        status: 'available',
      },
      {
        id: 'variable_valve_timing',
        name: '可变气门正时',
        description: 'VVT技术，兼顾低转扭矩和高转功率',
        cost: 35000,
        research_time_turns: 8,
        unlock_requirements: ['dohc_valvetrain'],
        category: 'engine',
        effects: {
          unlock_valvetrain: ['VARIABLE'],
          fuel_efficiency_bonus: 8,
          power_bonus_percent: 3,
        },
        status: 'locked',
      },
    ],
    categories: {
      engine: {
        name: '引擎技术',
        color: '#FF6B6B',
      },
      materials: {
        name: '材料科学',
        color: '#4ECDC4',
      },
      chassis: {
        name: '底盘技术',
        color: '#45B7D1',
      },
    },
  };
}


