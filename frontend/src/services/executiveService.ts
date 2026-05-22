/**
 * 高管和外交 API 服务
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

// ============================================================
// Types
// ============================================================

export interface StaffMember {
  id: number;
  role: 'CEO' | 'CTO' | 'CFO' | 'COO' | 'CMO' | 'ENGINEER' | 'DESIGNER';
  name: string;
  portrait_icon: string; // emoji or icon code
  loyalty: number; // 0-100
  skill_engineering?: number; // 0-100
  skill_finance?: number;
  skill_marketing?: number;
  skill_operations?: number;
  salary_monthly: number;
  hire_date_turn: number;
  severance_cost?: number;
}

export interface CompanyRelation {
  company_id: number;
  company_name: string;
  relation_score: number; // -100 to 100
  status: 'hostile' | 'rival' | 'neutral' | 'friendly' | 'allied';
  last_interaction_turn: number;
  alliance_level?: number;
}

export interface DiplomacyAction {
  action_type: 'insult' | 'praise' | 'propose_alliance' | 'spy' | 'headhunt';
  target_company_id: number;
  description: string;
  cost: number;
  success_chance?: number;
}

// ============================================================
// Staff Management API
// ============================================================

/**
 * 获取公司所有员工
 */
export async function getCompanyStaff(companyId: number): Promise<StaffMember[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/staff/list?company_id=${companyId}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Failed to get company staff:', error);
    return getMockStaff(companyId);
  }
}

/**
 * 解雇员工
 */
export async function fireStaff(
  companyId: number,
  staffId: number
): Promise<{ success: boolean; severance_paid?: number; error?: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/staff/fire`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        company_id: companyId,
        staff_id: staffId,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to fire staff:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * 招聘候选人
 */
export async function hireCandidateStaff(
  companyId: number,
  candidateId: number
): Promise<{ success: boolean; staff_id?: number; error?: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/staff/hire`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        company_id: companyId,
        candidate_id: candidateId,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to hire candidate:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

// ============================================================
// Diplomacy API
// ============================================================

/**
 * 获取与其他公司的关系
 */
export async function getCompanyRelations(companyId: number): Promise<CompanyRelation[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/diplomacy/relations?company_id=${companyId}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Failed to get company relations:', error);
    return getMockRelations();
  }
}

/**
 * 执行外交行动
 */
export async function performDiplomacyAction(
  companyId: number,
  action: DiplomacyAction
): Promise<{ success: boolean; result?: string; relation_change?: number; error?: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/diplomacy/action`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        company_id: companyId,
        ...action,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to perform diplomacy action:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

// ============================================================
// Mock Data
// ============================================================

function getMockStaff(companyId: number): StaffMember[] {
  return [
    {
      id: 1,
      role: 'CEO',
      name: 'Player (You)',
      portrait_icon: '👤',
      loyalty: 100,
      skill_engineering: 50,
      skill_finance: 60,
      skill_marketing: 55,
      skill_operations: 65,
      salary_monthly: 0,
      hire_date_turn: 0,
    },
    {
      id: 2,
      role: 'CTO',
      name: 'Dr. Hans Mueller',
      portrait_icon: '🧑‍🔬',
      loyalty: 75,
      skill_engineering: 92,
      skill_finance: 45,
      skill_marketing: 30,
      skill_operations: 60,
      salary_monthly: 25000,
      hire_date_turn: 5,
      severance_cost: 50000,
    },
    {
      id: 3,
      role: 'CFO',
      name: 'Ms. Sarah Chen',
      portrait_icon: '👩‍💼',
      loyalty: 85,
      skill_engineering: 30,
      skill_finance: 95,
      skill_marketing: 70,
      skill_operations: 65,
      salary_monthly: 22000,
      hire_date_turn: 3,
      severance_cost: 44000,
    },
    {
      id: 4,
      role: 'COO',
      name: 'Mr. Takeshi Yamada',
      portrait_icon: '👨‍💼',
      loyalty: 60,
      skill_engineering: 55,
      skill_finance: 60,
      skill_marketing: 50,
      skill_operations: 88,
      salary_monthly: 20000,
      hire_date_turn: 12,
      severance_cost: 40000,
    },
  ];
}

function getMockRelations(): CompanyRelation[] {
  return [
    {
      company_id: 2,
      company_name: 'Nexus Motors',
      relation_score: -30,
      status: 'rival',
      last_interaction_turn: 10,
    },
    {
      company_id: 3,
      company_name: 'Apex Automotive',
      relation_score: 15,
      status: 'neutral',
      last_interaction_turn: 8,
    },
    {
      company_id: 4,
      company_name: 'Quantum Vehicles',
      relation_score: 60,
      status: 'friendly',
      last_interaction_turn: 5,
      alliance_level: 1,
    },
  ];
}


