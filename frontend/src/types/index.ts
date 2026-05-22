// ============================================================
// API Response Types
// ============================================================

export interface GameState {
  current_year: number;
  current_month: number;
  current_week: number;
  turn_number: number;
  scenario_id?: string;
  difficulty?: string;
  playerCompany?: {
    id: number;
    name: string;
    cash: number;
    prestige?: number;
    credit_rating?: string;
  };
}

export interface Region {
  code: string;
  name: string;
  gdp_per_capita: number;
  population: number;
  unemployment_rate: number;
  tax_rate: number;
  infrastructure_quality: number;
  // Add more fields as needed
}

export interface Company {
  id: number;
  name: string;
  cash: number;
  region_code: string;
  prestige: number;
  is_player: boolean;
  tech_level?: number;
  brand_strength?: number;
  quality_rating?: number;
  market_share?: number;
}

export interface FinancialSnapshot {
  turn_number: number;
  cash: number;
  revenue: number;
  profit: number;
  market_share: number;
}

export interface EventLog {
  id: number;
  turn_number: number;
  event_type: string;
  title: string;
  description: string;
  severity: 'info' | 'warning' | 'critical';
  created_at: string;
  // 添加游戏时间字段用于更新StatusBar
  current_year?: number;
  current_month?: number;
  current_week?: number;
}

// ============================================================
// WebSocket Message Types
// ============================================================

export interface WSMessage {
  type: 'game_state' | 'event' | 'notification' | 'error';
  payload: unknown;
}

export interface WSGameStateMessage extends WSMessage {
  type: 'game_state';
  payload: GameState;
}

export interface WSEventMessage extends WSMessage {
  type: 'event';
  payload: EventLog;
}

// ============================================================
// UI State Types
// ============================================================

export type NavigationModule = 
  | 'dashboard'
  | 'design'
  | 'engineering'
  | 'factory'
  | 'market'
  | 'executive'
  | 'research'
  | 'reports';

export interface UIState {
  activeModule: NavigationModule;
  sidebarCollapsed: boolean;
  isPaused: boolean;
}

// ============================================================
// Factory & Production Types
// ============================================================

export type ProductionLineStatus = 'idle' | 'retooling' | 'active';

export interface ProductionLine {
  id: number;
  name: string;
  factory_id: number;
  status: ProductionLineStatus;
  assigned_design_id: number | null;
  assigned_design_name: string | null;
  daily_output: number;
  quality_index: number;
  retooling_months_remaining: number;
}

export interface Factory {
  id: number;
  name: string;
  factory_type: 'COMPONENT' | 'ASSEMBLY';
  level: number;
  capacity_units_per_month: number;
  current_utilization_rate: number;
  efficiency_score: number;
  is_operational: boolean;
  lines?: ProductionLine[];
}

export interface VehicleDesignSummary {
  id: number;
  name: string;
  body_style: string;
  estimated_cost: number;
}

// ============================================================
// Market & Sales Types
// ============================================================

export interface RegionPricing {
  region_id: number;
  region_code: string;
  region_name: string;
  demand_tier: string;
  market_share: number;
  rival_avg_price: number;
  my_price: number;
  estimated_profit: number;
  customer_feedback?: string;
}

export interface MarketHeatmapCell {
  region_id: number;
  region_code: string;
  sales_intensity: number; // 0-1 scale
  color: string;
}

// ============================================================
// Monthly Report Types
// ============================================================

export interface MonthlyFinancials {
  revenue: number;
  costs: number;
  net_profit: number;
  cash_balance: number;
}

export interface MonthlyProduction {
  cars_built: number;
  components_produced: number;
  utilization_rate: number;
}

export interface MonthlyAlert {
  type: 'info' | 'warning' | 'success' | 'critical';
  message: string;
}

export interface MonthlyReport {
  turn_number: number;
  year: number;
  month: number;
  financials: MonthlyFinancials;
  production: MonthlyProduction;
  alerts: MonthlyAlert[];
}

// ============================================================
// Tech Tree & Research Types
// ============================================================

export interface TechNode {
  id: string;
  name: string;
  description: string;
  cost: number;
  research_time_turns: number;
  unlock_requirements: string[];
  category: string;
  status?: 'locked' | 'available' | 'researching' | 'completed';
  progress?: number;
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
// Executive & Staff Types
// ============================================================

export interface StaffMember {
  id: number;
  role: 'CEO' | 'CTO' | 'CFO' | 'COO' | 'CMO' | 'ENGINEER' | 'DESIGNER';
  name: string;
  portrait_icon: string;
  loyalty: number;
  skill_engineering?: number;
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
  relation_score: number;
  status: 'hostile' | 'rival' | 'neutral' | 'friendly' | 'allied';
  last_interaction_turn: number;
  alliance_level?: number;
}

