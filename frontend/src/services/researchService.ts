/**
 * 研发服务API
 * 处理三种R&D路径：模块化平台、定制底盘、逆向工程
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

export interface ResearchProjectRequest {
  company_id: number;
  project_type: 'MODULAR_PLATFORM' | 'BESPOKE_CHASSIS' | 'REVERSE_ENGINEER';
  // 模块化平台参数
  platform_name?: string;
  platform_code?: string;
  supported_body_styles?: string[];
  min_wheelbase_mm?: number;
  max_wheelbase_mm?: number;
  // 定制底盘参数
  chassis_name?: string;
  chassis_code?: string;
  wheelbase_mm?: number;
  layout?: string;
  // 逆向工程参数
  target_car_id?: number;
  investment_multiplier?: number;
  // 通用参数
  material?: string;
  tech_level?: number;
}

export interface ReverseEngineeringRequest {
  company_id: number;
  target_car_id: number;
  investment_multiplier?: number;
}

export interface CompetitorCar {
  id: number;
  name: string;
  model_name: string;
  company_name: string;
  segment: string;
  horsepower: number;
  reliability: number;
  msrp: number;
}

/**
 * 启动研发项目
 */
export async function startResearchProject(
  request: ResearchProjectRequest
): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/engineering/research/start-project`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return await response.json();
}

/**
 * 逆向工程竞争对手车辆
 */
export async function reverseEngineerCar(
  request: ReverseEngineeringRequest
): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/engineering/reverse-engineer`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return await response.json();
}

/**
 * 获取可逆向工程的竞争对手车辆列表
 */
export async function getCompetitorCars(
  companyId: number
): Promise<CompetitorCar[]> {
  const response = await fetch(`${API_BASE_URL}/engineering/cars?exclude_company_id=${companyId}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return await response.json();
}

/**
 * 获取底盘列表（按source_type过滤）
 */
export async function getChassisList(
  companyId?: number,
  sourceType?: 'MODULAR_PLATFORM' | 'BESPOKE' | 'CLONED'
): Promise<any[]> {
  const params = new URLSearchParams();
  if (companyId) params.append('company_id', companyId.toString());
  if (sourceType) params.append('source_type', sourceType);
  
  const response = await fetch(`${API_BASE_URL}/engineering/chassis?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return await response.json();
}

