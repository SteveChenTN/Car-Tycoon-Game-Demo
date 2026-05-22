/**
 * chassisCalculations - 底盘平台统计计算引擎
 * 纯函数，无副作用，用于实时计算底盘参数
 */

export interface ChassisCalculationParams {
  /** 轴距 (mm) */
  wheelbase_mm: number;
  /** 前轮距 (mm) */
  track_front_mm: number;
  /** 后轮距 (mm) */
  track_rear_mm: number;
  /** 材料类型 */
  material: 'STEEL' | 'ALUMINUM' | 'CARBON';
  /** 结构类型 */
  structure_type: 'LADDER' | 'MONOCOQUE';
  /** 驱动布局 */
  layout: 'FF' | 'FR' | 'MR' | 'RR' | 'AWD';
  /** 扭转刚性目标 (1-100) */
  torsional_rigidity_target: number;
  /** 平台策略 */
  platform_strategy?: 'MODULAR' | 'BESPOKE';
}

export interface ChassisStats {
  /** 重量 (kg) */
  weight: number;
  /** 单位成本 (USD) */
  unitCost: number;
  /** R&D时间 (周) */
  rdTime: number;
  /** R&D项目成本 (USD) */
  programCost: number;
}

/**
 * 计算底盘平台统计数据
 */
export function calculatePlatformStats(params: ChassisCalculationParams): ChassisStats {
  const {
    wheelbase_mm,
    track_front_mm,
    track_rear_mm,
    material,
    structure_type,
    layout,
    torsional_rigidity_target,
    platform_strategy = 'MODULAR', // 默认为模块化
  } = params;

  // ========== 1. 基础重量计算 ==========
  // 基础体积因子：轴距 * 平均轮距 * 结构因子
  const avgTrack = (track_front_mm + track_rear_mm) / 2;
  const baseVolume = (wheelbase_mm / 1000) * (avgTrack / 1000) * 0.5; // m³
  
  // 结构类型乘数
  const structureMultiplier = structure_type === 'LADDER' ? 1.2 : 0.9;
  
  // 材料密度乘数（相对于钢）
  const materialDensityMultiplier = {
    STEEL: 1.0,
    ALUMINUM: 0.65,
    CARBON: 0.5,
  }[material];
  
  // 基础重量 = 体积 * 密度 * 结构因子
  // 假设基础密度为 2000 kg/m³（钢）
  const baseWeight = baseVolume * 2000 * structureMultiplier * materialDensityMultiplier;
  
  // 扭转刚性修正（更高的刚性需要更多材料）
  const rigidityFactor = 1 + (torsional_rigidity_target / 100) * 0.2; // +0-20%
  
  // 布局修正（MR/RR需要额外支撑）
  const layoutWeightFactor = (layout === 'MR' || layout === 'RR') ? 1.1 : 1.0;
  
  const weight = Math.round(baseWeight * rigidityFactor * layoutWeightFactor);

  // ========== 2. 单位成本计算 ==========
  // 基础制造成本
  const baseManufacturingCost = 2000; // USD
  
  // 材料成本乘数（每kg）
  const materialCostPerKg = {
    STEEL: 2.0,      // $2/kg
    ALUMINUM: 4.5,   // $4.5/kg
    CARBON: 25.0,    // $25/kg
  }[material];
  
  // 材料成本 = 重量 * 单位材料成本
  const materialCost = weight * materialCostPerKg;
  
  // 结构复杂度成本
  // Monocoque 比 Ladder Frame 贵 20%
  const structureComplexityMultiplier = structure_type === 'MONOCOQUE' ? 1.2 : 1.0;
  
  // 布局复杂度（MR/RR/AWD 更复杂）
  const layoutComplexityMultiplier = 
    layout === 'MR' || layout === 'RR' ? 1.15 :
    layout === 'AWD' ? 1.25 : 1.0;
  
  // 扭转刚性成本（更高的刚性需要更精密的工艺）
  const rigidityCostFactor = 1 + (torsional_rigidity_target / 100) * 0.15; // +0-15%
  
  // 平台策略对单位成本的影响
  // 模块化平台：单位成本正常（可以分摊到多个车型）
  // 定制平台：单位成本 +20%（无法分摊，效率低）
  const platformCostMultiplier = platform_strategy === 'BESPOKE' ? 1.2 : 1.0;
  
  const unitCost = Math.round(
    (baseManufacturingCost + materialCost) * 
    structureComplexityMultiplier * 
    layoutComplexityMultiplier * 
    rigidityCostFactor *
    platformCostMultiplier
  );

  // ========== 3. R&D时间计算 ==========
  // 平台策略对R&D时间的影响
  // 模块化平台：需要设计可扩展架构，时间长（基础 50周）
  // 定制平台：针对单一车型优化，时间短（基础 12周）
  let rdTime = platform_strategy === 'MODULAR' ? 50 : 12;
  
  // Monocoque 结构复杂，+10周
  if (structure_type === 'MONOCOQUE') {
    rdTime += 10;
  }
  
  // MR/RR 布局非标准，+5周
  if (layout === 'MR' || layout === 'RR') {
    rdTime += 5;
  }
  
  // AWD 复杂度高，+8周
  if (layout === 'AWD') {
    rdTime += 8;
  }
  
  // 扭转刚性目标影响（更高的目标需要更多测试）
  rdTime += Math.round((torsional_rigidity_target / 100) * 5); // +0-5周
  
  // 材料复杂度（碳纤维需要更多研发）
  if (material === 'CARBON') {
    rdTime += 8;
  } else if (material === 'ALUMINUM') {
    rdTime += 3;
  }

  // ========== 4. R&D项目成本计算 ==========
  // 平台策略对R&D成本的影响（这是最大的差异）
  // 模块化平台：需要设计可扩展架构，R&D成本高（基础 $5M）
  // 定制平台：针对单一车型优化，R&D成本低（基础 $500k）
  let baseProgramCost = platform_strategy === 'MODULAR' ? 5_000_000 : 500_000;
  
  // 技术等级乘数（基于材料和技术复杂度）
  let techLevelMultiplier = 1.0;
  
  if (material === 'CARBON') {
    techLevelMultiplier = 1.8; // 碳纤维技术昂贵
  } else if (material === 'ALUMINUM') {
    techLevelMultiplier = 1.3; // 铝合金技术
  }
  
  // 结构复杂度乘数
  if (structure_type === 'MONOCOQUE') {
    techLevelMultiplier *= 1.4; // Monocoque 研发成本高
  }
  
  // 布局复杂度乘数
  if (layout === 'MR' || layout === 'RR') {
    techLevelMultiplier *= 1.2; // 非标准布局
  } else if (layout === 'AWD') {
    techLevelMultiplier *= 1.5; // AWD 最复杂
  }
  
  // 扭转刚性目标影响（更高的目标需要更多测试和迭代）
  const rigidityCostMultiplier = 1 + (torsional_rigidity_target / 100) * 0.3; // +0-30%
  
  const programCost = Math.round(baseProgramCost * techLevelMultiplier * rigidityCostMultiplier);

  return {
    weight: isNaN(weight) ? 0 : weight,
    unitCost: isNaN(unitCost) ? 0 : unitCost,
    rdTime: isNaN(rdTime) ? 0 : rdTime,
    programCost: isNaN(programCost) ? 0 : programCost,
  };
}

