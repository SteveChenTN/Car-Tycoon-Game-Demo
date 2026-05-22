/**
 * 前端轻量级工程计算
 * 用于实时预览，不包含完整的后端物理模拟
 */

export interface PowerCurvePoint {
  rpm: number;
  torque: number;
  power: number;
}

/**
 * 根据年份获取最大允许的技术等级
 */
export function getMaxTechLevelForYear(currentYear: number): number {
  if (currentYear < 1950) {
    return 2;  // 1940s
  } else if (currentYear < 1960) {
    return 4;  // 1950s
  } else if (currentYear < 1970) {
    return 6;  // 1960s
  } else if (currentYear < 1980) {
    return 8;  // 1970s
  } else {
    return 10;  // 1980s及以后
  }
}

/**
 * 验证组件是否可用（基于年份和技术等级）
 */
export function validateComponentAvailability(
  componentType: 'material' | 'valvetrain' | 'induction' | 'fuel',
  componentId: string,
  currentYear: number,
  effectiveTechLevel: number
): { isValid: boolean; errorMessage?: string } {
  // 组件所需的技术等级（从component_stats.json映射）
  const componentRequirements: Record<string, Record<string, number>> = {
    material: {
      'CAST_IRON': 1,
      'ALUMINUM': 3,
      'MAGNESIUM': 7,
    },
    valvetrain: {
      'OHV': 1,
      'SOHC': 2,
      'DOHC': 4,
      'VARIABLE': 6,
    },
    induction: {
      'NA': 1,
      'TURBO': 5,
      'TWINTURBO': 7,
      'SUPERCHARGED': 4,
    },
    fuel: {
      'GASOLINE': 1,
      'DIESEL': 3,
      'E85': 8,
      'LPG': 6,
    },
  };

  // 基础组件总是可用
  if (componentType === 'induction' && componentId === 'NA') {
    return { isValid: true };
  }
  if (componentType === 'fuel' && componentId === 'GASOLINE') {
    return { isValid: true };
  }

  const requirements = componentRequirements[componentType];
  if (!requirements) {
    return { isValid: true };  // 未知类型默认允许
  }

  const requiredTechLevel = requirements[componentId];
  if (requiredTechLevel === undefined) {
    return { isValid: true };  // 未知组件默认允许
  }

  if (effectiveTechLevel < requiredTechLevel) {
    const maxTechForYear = getMaxTechLevelForYear(currentYear);
    const componentNameMap: Record<string, string> = {
      material: '材料',
      valvetrain: '配气机构',
      induction: '进气方式',
      fuel: '燃料',
    };
    const componentName = componentNameMap[componentType] || componentType;
    return {
      isValid: false,
      errorMessage: `${componentName} '${componentId}' 需要技术等级 ${requiredTechLevel}，但当前年份(${currentYear})最大允许 ${maxTechForYear}，有效技术等级为 ${effectiveTechLevel}`,
    };
  }

  return { isValid: true };
}

/**
 * 计算排量
 */
export function calculateDisplacement(bore: number, stroke: number, cylinders: number): number {
  const radius = bore / 2;
  const singleCylinderVolume = Math.PI * (radius ** 2) * stroke;
  const totalVolume = singleCylinderVolume * cylinders;
  return Math.round(totalVolume / 1000); // 转换为cc
}

/**
 * 估算红线转速
 */
export function estimateRedline(stroke: number, material: string, techLevel: number): number {
  // 基于活塞平均速度限制
  const maxPistonSpeed: Record<string, number> = {
    CAST_IRON: 20,
    ALUMINUM: 25,
    MAGNESIUM: 28,
  };
  
  const baseMPS = maxPistonSpeed[material] || 22;
  const adjustedMPS = baseMPS + techLevel * 0.5;
  
  // RPM = (MPS * 60000) / (2 * Stroke)
  const redline = (adjustedMPS * 60000) / (2 * stroke);
  
  return Math.round(redline / 100) * 100; // 四舍五入到百位
}

/**
 * 估算最大马力
 */
export function estimateHorsepower(
  displacementCC: number,
  compressionRatio: number,
  inductionType: string,
  boostBar: number,
  valvetrain: string,
  techLevel: number,
  redlineRPM: number
): number {
  const displacementL = displacementCC / 1000;
  
  // 容积效率
  const veBase: Record<string, number> = {
    OHV: 0.75,
    SOHC: 0.85,
    DOHC: 0.92,
    VARIABLE: 0.98,
  };
  
  let ve = veBase[valvetrain] || 0.85;
  
  // 增压修正
  if (inductionType === 'TURBO') {
    ve *= 1.0 + boostBar * 0.5;
  } else if (inductionType === 'TWINTURBO') {
    ve *= 1.0 + boostBar * 0.55;
  } else if (inductionType === 'SUPERCHARGED') {
    ve *= 1.0 + boostBar * 0.45;
  }
  
  // BMEP（调整以匹配后端）
  const bmepBase = 10.0 + (compressionRatio - 8.0) * 0.6;
  const techEfficiency = 1.0 + (techLevel - 1) * 0.02;
  
  // 使用VE曲线在峰值功率RPM
  const peakPowerRPM = inductionType.includes('TURBO') 
    ? Math.round(redlineRPM * 0.90)
    : Math.round(redlineRPM * 0.95);
  const veAtPeak = calculateVolumetricEfficiency(
    peakPowerRPM, redlineRPM, valvetrain, inductionType, boostBar
  );
  
  // 从扭矩计算马力：HP = (Torque * RPM) / 7121
  const bmep = bmepBase;
  const torqueNm = (bmep * displacementL * 100 * veAtPeak * techEfficiency) / Math.PI;
  const power = (torqueNm * peakPowerRPM) / 7121;
  
  return Math.round(power);
}

/**
 * 计算容积效率（VE曲线）
 */
export function calculateVolumetricEfficiency(
  rpm: number,
  redlineRPM: number,
  valvetrain: string,
  inductionType: string,
  boostBar: number = 0
): number {
  const rpmRatio = rpm / redlineRPM;
  
  // 基础VE曲线形状（驼峰）
  let veCurve: number;
  if (rpmRatio < 0.3) {
    // 低转：从低值线性上升
    veCurve = 0.3 + (rpmRatio / 0.3) * 0.2; // 0.3到0.5
  } else if (rpmRatio < 0.55) {
    // 中低转：快速上升
    veCurve = 0.5 + ((rpmRatio - 0.3) / 0.25) * 0.35; // 0.5到0.85
  } else if (rpmRatio < 0.65) {
    // 中高转：达到峰值
    veCurve = 0.85 + ((rpmRatio - 0.55) / 0.1) * 0.15; // 0.85到1.0
  } else if (rpmRatio < 0.85) {
    // 高转：缓慢下降
    veCurve = 1.0 - ((rpmRatio - 0.65) / 0.2) * 0.15; // 1.0到0.85
  } else {
    // 极高转：快速下降
    veCurve = 0.85 - ((rpmRatio - 0.85) / 0.15) * 0.15; // 0.85到0.7
  }
  
  // 配气机构修正
  let valvetrainMultiplier: number;
  switch (valvetrain) {
    case 'OHV':
      valvetrainMultiplier = 0.4 < rpmRatio && rpmRatio < 0.7 ? 0.95 : 0.85;
      break;
    case 'SOHC':
      valvetrainMultiplier = 0.92;
      break;
    case 'DOHC':
      valvetrainMultiplier = rpmRatio > 0.6 ? 1.05 : 1.0;
      break;
    case 'VARIABLE':
      valvetrainMultiplier = rpmRatio > 0.6 ? 1.05 : 1.05;
      break;
    default:
      valvetrainMultiplier = 0.92;
  }
  
  let ve = veCurve * valvetrainMultiplier;
  
  // 增压提升容积效率
  if (inductionType === 'NA') {
    // 无变化
  } else if (inductionType === 'TURBO') {
    let boostFactor = 1.0;
    if (rpm < 2000) boostFactor = 0.7;
    else if (rpm < 3000) boostFactor = 0.85;
    ve = ve * (1.0 + boostBar * 0.5 * boostFactor);
  } else if (inductionType === 'TWINTURBO') {
    let boostFactor = 1.0;
    if (rpm < 2000) boostFactor = 0.75;
    else if (rpm < 3000) boostFactor = 0.90;
    ve = ve * (1.0 + boostBar * 0.55 * boostFactor);
  } else if (inductionType === 'SUPERCHARGED') {
    ve = ve * (1.0 + boostBar * 0.45);
  }
  
  return Math.max(0.2, Math.min(ve, 1.5));
}

/**
 * 获取燃料辛烷值限制的最大压缩比
 */
export function getFuelOctaneLimit(currentYear: number, fuelType: string): number {
  // 历史燃料质量
  let historicalOctane: number;
  if (currentYear < 1950) {
    historicalOctane = 75; // 1940s
  } else if (currentYear < 1960) {
    historicalOctane = 80; // 1950s
  } else if (currentYear < 1970) {
    historicalOctane = 90; // 1960s
  } else {
    historicalOctane = 91; // 1970s+
  }
  
  // 燃料类型辛烷值（简化，实际应从数据加载）
  const fuelOctane: Record<string, number> = {
    GASOLINE: 91,
    DIESEL: 50, // 柴油使用十六烷值
    E85: 105,
    LPG: 110,
  };
  
  const octaneRating = fuelOctane[fuelType] || 91;
  const effectiveOctane = Math.min(octaneRating, historicalOctane);
  
  // 辛烷值到压缩比的转换
  const maxCR = 6.0 + (effectiveOctane - 60) * 0.1;
  
  return Math.max(6.0, Math.min(maxCR, 12.0));
}

/**
 * 估算最大扭矩
 */
export function estimateTorque(
  displacementCC: number,
  compressionRatio: number,
  inductionType: string,
  boostBar: number,
  techLevel: number,
  valvetrain?: string,
  redlineRPM?: number
): number {
  const displacementL = displacementCC / 1000;
  
  // 调整BMEP基础值以匹配后端
  let bmepBase = 10.0 + (compressionRatio - 8.0) * 0.6;
  
  // 增压倍增器
  let bmepMultiplier = 1.0;
  if (inductionType === 'TURBO') {
    bmepMultiplier = 1.0 + boostBar * 0.8;
  } else if (inductionType === 'TWINTURBO') {
    bmepMultiplier = 1.0 + boostBar * 0.85;
  } else if (inductionType === 'SUPERCHARGED') {
    bmepMultiplier = 1.0 + boostBar * 0.75;
  }
  
  const bmep = bmepBase * bmepMultiplier;
  const techFactor = 1.0 + (techLevel - 1) * 0.02;
  
  // 计算峰值扭矩RPM的VE（如果提供了参数）
  let veAtPeak = 1.0;
  if (valvetrain && redlineRPM) {
    const peakTorqueRPM = inductionType.includes('TURBO')
      ? Math.round(redlineRPM * 0.40)
      : Math.round(redlineRPM * 0.55);
    veAtPeak = calculateVolumetricEfficiency(
      peakTorqueRPM, redlineRPM, valvetrain, inductionType, boostBar
    );
  }
  
  const torque = (bmep * displacementL * 100 * veAtPeak * techFactor) / Math.PI;
  
  return Math.round(torque);
}

/**
 * 生成动力曲线（使用VE曲线）
 * 
 * 重要：VE曲线基于maxSafeRPM（MPS上限）计算，然后根据redlineRPM截断
 * 这样降低redline时曲线会被直接截断，而不是压缩
 */
export function generatePowerCurve(
  maxTorqueNm: number,
  maxPowerHP: number,
  redlineRPM: number,
  inductionType: string,
  displacementCC?: number,
  compressionRatio?: number,
  valvetrain?: string,
  boostBar?: number,
  techLevel?: number,
  maxSafeRPM?: number  // MPS上限，用于VE曲线计算
): PowerCurvePoint[] {
  const points: PowerCurvePoint[] = [];
  const step = 500;
  const minRPM = 1000;
  
  // 如果提供了完整参数，使用VE曲线计算
  const useVECurve = displacementCC !== undefined && 
                     compressionRatio !== undefined && 
                     valvetrain !== undefined &&
                     boostBar !== undefined &&
                     techLevel !== undefined;
  
  if (useVECurve) {
    const displacementL = displacementCC! / 1000;
    const bmepBase = 10.0 + (compressionRatio! - 8.0) * 0.6;
    const techFactor = 1.0 + (techLevel! - 1) * 0.02;
    
    // 使用MPS上限作为VE曲线的参考（如果提供了）
    // 如果没有提供，使用redlineRPM（向后兼容）
    const veReferenceRedline = maxSafeRPM || redlineRPM;
    
    for (let rpm = minRPM; rpm <= redlineRPM; rpm += step) {
      // 计算该RPM下的VE
      // 重要：VE曲线基于MPS上限计算，而不是用户设定的redline
      const veAtRPM = calculateVolumetricEfficiency(
        rpm, veReferenceRedline, valvetrain!, inductionType, boostBar!
      );
      
      // 计算BMEP
      let bmepMultiplier = 1.0;
      let boostFactor = 1.0;
      
      if (inductionType === 'TURBO' || inductionType === 'TWINTURBO') {
        if (rpm < 2000) boostFactor = 0.7;
        else if (rpm < 3000) boostFactor = 0.85;
        else boostFactor = 1.0;
      }
      
      if (inductionType === 'TURBO') {
        bmepMultiplier = 1.0 + boostBar! * 0.8 * boostFactor;
      } else if (inductionType === 'TWINTURBO') {
        bmepMultiplier = 1.0 + boostBar! * 0.85 * boostFactor;
      } else if (inductionType === 'SUPERCHARGED') {
        bmepMultiplier = 1.0 + boostBar! * 0.75;
      }
      
      const bmep = bmepBase * bmepMultiplier;
      
      // 计算扭矩
      const torque = (bmep * displacementL * 100 * veAtRPM * techFactor) / Math.PI;
      
      // 计算功率：使用正确的单位转换常数 7121
      const powerHP = (torque * rpm) / 7121;
      
      points.push({
        rpm,
        torque: Math.round(torque),
        power: Math.round(powerHP),
      });
    }
  } else {
    // 回退到简化模型
    const peakTorqueRPM = inductionType.includes('TURBO') 
      ? redlineRPM * 0.4 
      : redlineRPM * 0.6;
    
    const peakPowerRPM = redlineRPM * 0.85;
    
    for (let rpm = minRPM; rpm <= redlineRPM; rpm += step) {
      let torque = 0;
      
      if (rpm < peakTorqueRPM) {
        const ratio = rpm / peakTorqueRPM;
        torque = maxTorqueNm * (0.6 + 0.4 * ratio);
      } else if (rpm <= peakPowerRPM) {
        const falloff = (rpm - peakTorqueRPM) / (peakPowerRPM - peakTorqueRPM);
        torque = maxTorqueNm * (1.0 - 0.15 * falloff);
      } else {
        const falloff = (rpm - peakPowerRPM) / (redlineRPM - peakPowerRPM);
        torque = maxTorqueNm * (0.85 - 0.3 * falloff);
      }
      
      // 使用正确的单位转换常数 7121
      const powerHP = (torque * rpm) / 7121;
      
      points.push({
        rpm,
        torque: Math.round(torque),
        power: Math.round(powerHP),
      });
    }
  }
  
  return points;
}

/**
 * 估算引擎重量
 */
export function estimateEngineWeight(
  displacementCC: number,
  configuration: string,
  material: string,
  inductionType: string,
  techLevel: number
): number {
  const displacementL = displacementCC / 1000;
  
  const baseWeightPerLiter = 65;
  let baseWeight = displacementL * baseWeightPerLiter;
  
  // 材料系数
  const materialFactor: Record<string, number> = {
    CAST_IRON: 1.2,
    ALUMINUM: 1.0,
    MAGNESIUM: 0.85,
  };
  
  // 配置系数
  const configFactor: Record<string, number> = {
    INLINE: 1.0,
    V: 1.15,
    BOXER: 1.20,
    VR: 1.12,
    W: 1.25,
  };
  
  // 增压系统重量
  const inductionWeight: Record<string, number> = {
    NA: 0,
    TURBO: 15 + displacementL * 5,
    TWINTURBO: 25 + displacementL * 8,
    SUPERCHARGED: 20 + displacementL * 6,
  };
  
  const techFactor = 1.0 - (techLevel - 1) * 0.03;
  
  const totalWeight = 
    (baseWeight * (materialFactor[material] || 1.0) * (configFactor[configuration] || 1.0) + 
    (inductionWeight[inductionType] || 0)) * techFactor;
  
  return Math.round(totalWeight * 10) / 10;
}

/**
 * 估算引擎尺寸
 */
export function estimateEngineDimensions(
  bore: number,
  stroke: number,
  cylinders: number,
  configuration: string,
  inductionType: string
): { length: number; width: number; height: number } {
  const baseCylinderLength = stroke * 1.5;
  const baseWidth = bore * 1.3;
  const baseHeight = stroke * 2.0 + bore;
  
  let length = 0;
  let width = 0;
  let height = 0;
  
  switch (configuration) {
    case 'INLINE':
      length = baseCylinderLength * cylinders;
      width = baseWidth;
      height = baseHeight;
      break;
    case 'V':
      length = baseCylinderLength * (cylinders / 2);
      width = baseWidth * 2.2;
      height = baseHeight * 1.1;
      break;
    case 'BOXER':
      length = baseCylinderLength * (cylinders / 2);
      width = baseWidth * 3.0;
      height = baseHeight * 0.6;
      break;
    case 'VR':
      length = baseCylinderLength * (cylinders * 0.7);
      width = baseWidth * 1.5;
      height = baseHeight * 1.05;
      break;
    case 'W':
      length = baseCylinderLength * (cylinders / 3);
      width = baseWidth * 2.5;
      height = baseHeight * 1.2;
      break;
    default:
      length = baseCylinderLength * cylinders;
      width = baseWidth;
      height = baseHeight;
  }
  
  // 增压修正
  if (inductionType === 'TURBO' || inductionType === 'TWINTURBO') {
    length *= 1.15;
    height *= 1.25;
  } else if (inductionType === 'SUPERCHARGED') {
    length *= 1.10;
    height *= 1.20;
  }
  
  return {
    length: Math.round(length * 10) / 10,
    width: Math.round(width * 10) / 10,
    height: Math.round(height * 10) / 10,
  };
}

/**
 * 估算可靠性评分
 */
export function estimateReliability(
  compressionRatio: number,
  boostBar: number,
  techLevel: number,
  material: string
): number {
  let baseReliability = 80;
  
  // 压缩比影响
  if (compressionRatio > 11) {
    baseReliability -= (compressionRatio - 11) * 3;
  }
  
  // 增压影响
  baseReliability -= boostBar * 8;
  
  // 技术等级提升
  baseReliability += techLevel * 2;
  
  // 材料影响
  const materialBonus: Record<string, number> = {
    CAST_IRON: 5,
    ALUMINUM: 0,
    MAGNESIUM: -5,
  };
  
  baseReliability += materialBonus[material] || 0;
  
  return Math.max(10, Math.min(100, Math.round(baseReliability)));
}

/**
 * 估算制造成本
 */
export function estimateManufacturingCost(
  displacementCC: number,
  material: string,
  configuration: string,
  inductionType: string,
  valvetrain: string,
  techLevel: number
): number {
  const displacementL = displacementCC / 1000;
  
  // 基础成本 ($/L)
  const baseCostPerLiter = 800;
  let cost = displacementL * baseCostPerLiter;
  
  // 材料倍数
  const materialMult: Record<string, number> = {
    CAST_IRON: 0.8,
    ALUMINUM: 1.0,
    MAGNESIUM: 1.5,
  };
  
  // 配置倍数
  const configMult: Record<string, number> = {
    INLINE: 1.0,
    V: 1.3,
    BOXER: 1.4,
    VR: 1.35,
    W: 1.6,
  };
  
  // 进气倍数
  const inductionMult: Record<string, number> = {
    NA: 1.0,
    TURBO: 1.4,
    TWINTURBO: 1.8,
    SUPERCHARGED: 1.5,
  };
  
  // 配气倍数
  const valvetrainMult: Record<string, number> = {
    OHV: 0.9,
    SOHC: 1.0,
    DOHC: 1.2,
    VARIABLE: 1.5,
  };
  
  cost *= (materialMult[material] || 1.0);
  cost *= (configMult[configuration] || 1.0);
  cost *= (inductionMult[inductionType] || 1.0);
  cost *= (valvetrainMult[valvetrain] || 1.0);
  cost *= (0.9 + techLevel * 0.02); // 技术等级影响
  
  return Math.round(cost);
}

/**
 * 检查引擎与底盘的装配适配性
 */
export function checkEngineFitment(
  engineLength: number,
  engineWidth: number,
  engineHeight: number,
  bayLength: number,
  bayWidth: number,
  bayHeight: number
): {
  fits: boolean;
  message: string;
  engineVolume: number;
  engineBayVolume: number;
} {
  const engineVolume = (engineLength * engineWidth * engineHeight) / 1_000_000_000; // 转为立方米
  const bayVolume = (bayLength * bayWidth * bayHeight) / 1_000_000_000;
  
  // 检查每个维度
  const lengthFits = engineLength <= bayLength;
  const widthFits = engineWidth <= bayWidth;
  const heightFits = engineHeight <= bayHeight;
  
  const fits = lengthFits && widthFits && heightFits;
  
  let message = '';
  if (!fits) {
    const issues: string[] = [];
    if (!lengthFits) issues.push(`长度超出 ${Math.round(engineLength - bayLength)}mm`);
    if (!widthFits) issues.push(`宽度超出 ${Math.round(engineWidth - bayWidth)}mm`);
    if (!heightFits) issues.push(`高度超出 ${Math.round(engineHeight - bayHeight)}mm`);
    message = `引擎不适配: ${issues.join(', ')}`;
  } else {
    message = '引擎完美适配！';
  }
  
  return {
    fits,
    message,
    engineVolume: Math.round(engineVolume * 1000) / 1000,
    engineBayVolume: Math.round(bayVolume * 1000) / 1000,
  };
}

