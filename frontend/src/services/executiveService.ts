/**
 * Executive and diplomacy API service.
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

export type StaffPosition = 'CEO' | 'CTO' | 'CFO' | 'COO' | 'CMO' | 'ENGINEER' | 'DESIGNER';

export interface StaffMember {
  id: number;
  full_name: string;
  position: StaffPosition;
  current_loyalty: number;
  current_morale: number;
  annual_salary: number;
  market_value: number;
  hire_turn: number | null;
  fire_turn: number | null;
  skill_engineering: number;
  skill_finance: number;
  skill_marketing: number;
  skill_operations: number;
  skill_leadership: number;
  effectiveness: number;
  severance_cost: number;
}

export type StaffCandidate = StaffMember;

export interface StaffMutationResult {
  success: boolean;
  staff_id?: number;
  staff?: StaffMember;
  message?: string;
  severance_paid?: number;
  error?: string;
}

export interface CompanyRelation {
  company_id: number;
  company_name: string;
  relation_score: number;
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

async function errorFromResponse(response: Response): Promise<Error> {
  try {
    const data = await response.json();
    const detail = data.detail ?? data.message ?? data.error;
    if (detail) {
      return new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
  } catch {
    // Fall through to the HTTP status message.
  }

  return new Error(`HTTP ${response.status}: ${response.statusText}`);
}

export async function getCompanyStaff(companyId: number): Promise<StaffMember[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/staff/list?company_id=${companyId}`);
    if (!response.ok) {
      throw await errorFromResponse(response);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to get company staff:', error);
    return [];
  }
}

export async function getStaffCandidates(
  companyId: number,
  position?: StaffPosition
): Promise<StaffCandidate[]> {
  try {
    const params = new URLSearchParams({ company_id: companyId.toString() });
    if (position) {
      params.set('position', position);
    }

    const response = await fetch(`${API_BASE_URL}/staff/candidates?${params.toString()}`);
    if (!response.ok) {
      throw await errorFromResponse(response);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to get staff candidates:', error);
    return [];
  }
}

export async function fireStaff(
  companyId: number,
  staffId: number,
  severanceMultiplier = 1
): Promise<StaffMutationResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/staff/fire`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        company_id: companyId,
        staff_id: staffId,
        severance_multiplier: severanceMultiplier,
      }),
    });

    if (!response.ok) {
      throw await errorFromResponse(response);
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

export async function hireCandidateStaff(
  companyId: number,
  candidateId: number,
  offeredSalary?: number
): Promise<StaffMutationResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/staff/hire`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        company_id: companyId,
        candidate_id: candidateId,
        offered_salary: offeredSalary,
      }),
    });

    if (!response.ok) {
      throw await errorFromResponse(response);
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

export async function getCompanyRelations(companyId: number): Promise<CompanyRelation[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/diplomacy/relations?company_id=${companyId}`);
    if (!response.ok) {
      throw await errorFromResponse(response);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to get company relations:', error);
    return getMockRelations();
  }
}

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
      throw await errorFromResponse(response);
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
