/**
 * ChassisBlueprint - 底盘蓝图可视化器
 * 真实汽车比例，厚重工业风格
 */
import React from 'react';

export interface ChassisBlueprintProps {
  /** 轴距 (mm) */
  wheelbase_mm: number;
  /** 前轮距 (mm) */
  track_front_mm: number;
  /** 后轮距 (mm) */
  track_rear_mm: number;
  /** 引擎舱容积 (升) */
  engine_bay_volume?: number;
  /** 引擎舱长度 (mm) */
  engine_bay_length_mm?: number;
  /** 引擎舱宽度 (mm) */
  engine_bay_width_mm?: number;
  /** 引擎舱高度 (mm) */
  engine_bay_height_mm?: number;
  /** 溃缩区长度 (m) */
  crumple_zone_length?: number;
  /** 油箱位置 */
  fuel_tank_location?: 'REAR_AXLE_BEHIND' | 'UNDER_SEAT' | 'MID_CENTRAL';
  /** 驱动布局 */
  layout?: 'FF' | 'FR' | 'MR' | 'RR' | 'AWD';
  /** 结构类型 */
  structure_type?: 'LADDER' | 'MONOCOQUE';
  /** 是否显示侧视图 */
  showSideView?: boolean;
}

export const ChassisBlueprint: React.FC<ChassisBlueprintProps> = ({
  wheelbase_mm,
  track_front_mm,
  track_rear_mm,
  engine_bay_volume,
  engine_bay_length_mm = 800,
  engine_bay_width_mm = 700,
  engine_bay_height_mm = 600,
  crumple_zone_length = 0,
  fuel_tank_location = 'REAR_AXLE_BEHIND',
  layout = 'FF',
  structure_type = 'LADDER',
  showSideView = false,
}) => {
  // ========== 物理常数（真实汽车比例）==========
  // viewBox="0 0 1000 700"
  // 1单位 ≈ 4mm
  // 车指向右侧
  
  const scale = 0.25; // 1mm = 0.25单位，所以1单位 ≈ 4mm
  const viewBoxScale = 1; // viewBox缩放因子（1/0.6 = 1.66667）
  
  // 关键坐标（硬编码，需要按viewBox缩放）
  const frontAxleX = 1250 * viewBoxScale; // 前轴X（固定锚点）
  const rearAxleX = 1250 - (wheelbase_mm * scale); // 后轴X（计算）
  const groundLineY = 900; // 地面线Y（向下移动100+50+50+50）
  const wheelRadius = 70; // 车轮半径（增大，真实比例）
  const wheelCenterY = 830; // 车轮中心Y（900 - 70，精确接触地面）
  
  // 顶视图参数（向上移动）
  const topViewCenterY = 270; // 顶视图中心Y（向上移动+50+50+50）
  const topViewZone = { min: 150, max: 450 }; // 顶视图区域（缩小+50+50+50）
  
  // 侧视图参数（继续向下移动100）
  const sideViewZone = { min: 650, max: 950 }; // 侧视图区域（向下移动100+50+50+50）
  const frameRailY = 790; // 车架轨道Y（830 - 40，位于轮中心线上方）
  
  // 车轮参数（顶视图 - 厚重矩形，需要按viewBox缩放）
  const wheelWidth = 130 * viewBoxScale; // 车轮长度（水平方向，厚重）
  const wheelThickness = 50 * viewBoxScale; // 车轮厚度（垂直方向）
  
  // 车架轨道参数（厚重，需要按viewBox缩放）
  const railThickness = 15 * viewBoxScale; // 轨道厚度（填充矩形）
  const railSpacing = Math.max(track_front_mm, track_rear_mm) * scale * 0.5 * viewBoxScale; // 轨道间距
  
  // 车架轨道位置（顶视图，需要按viewBox缩放）
  const leftRailY = topViewCenterY - railSpacing / 2;
  const rightRailY = topViewCenterY + railSpacing / 2;
  const railStartX = rearAxleX - 150 * viewBoxScale; // 轨道起始（后保险杠）
  const railEndX = frontAxleX + 150 * viewBoxScale; // 轨道结束（前保险杠）
  const railLength = railEndX - railStartX;
  
  // 横梁位置（3个）
  const crossmemberCount = 3;
  const crossmemberPositions = Array.from({ length: crossmemberCount }, (_, i) => {
    const t = (i + 1) / (crossmemberCount + 1);
    return railStartX + railLength * t;
  });
  
  // 发动机位置计算（根据布局动态调整）
  const engineLength = engine_bay_length_mm * scale * viewBoxScale; // 发动机长度（动态）
  const engineWidth = engineLength; // 发动机宽度（使用动态长度）
  const engineTopY = topViewCenterY - (engine_bay_width_mm * scale * viewBoxScale) / 2; // 顶视图Y
  const engineTopHeight = engine_bay_width_mm * scale * viewBoxScale; // 顶视图高度（动态）
  const engineSideHeight = engine_bay_height_mm * scale * viewBoxScale; // 发动机高度（动态）
  
  // 根据布局计算引擎位置
  const enginePosition = React.useMemo(() => {
    const midPointX = (frontAxleX + rearAxleX) / 2;
    const frontOverhang = 150 * viewBoxScale; // 前悬长度
    const rearOverhang = 150 * viewBoxScale; // 后悬长度
    
    switch (layout) {
      case 'FF':
      case 'FR':
        // 前置引擎：位于前轴前方（Nose区域）
        return {
          topX: frontAxleX - engineLength - 20 * viewBoxScale,
          topY: engineTopY,
          topWidth: engineLength,
          topHeight: engineTopHeight,
          sideX: frontAxleX - engineLength - 20 * viewBoxScale,
          sideY: frameRailY - engineSideHeight,
          sideWidth: engineLength,
          sideHeight: engineSideHeight,
        };
      case 'MR':
        // 中置引擎：位于两轴之间（驾驶员后方，后轴前方）
        const mrStartX = midPointX - engineLength / 2;
        return {
          topX: mrStartX,
          topY: engineTopY,
          topWidth: engineLength,
          topHeight: engineTopHeight,
          sideX: mrStartX,
          sideY: frameRailY - engineSideHeight,
          sideWidth: engineLength,
          sideHeight: engineSideHeight,
        };
      case 'RR':
        // 后置引擎：位于后轴后方（Rear Overhang区域）
        return {
          topX: rearAxleX + 20 * viewBoxScale,
          topY: engineTopY,
          topWidth: engineLength,
          topHeight: engineTopHeight,
          sideX: rearAxleX + 20 * viewBoxScale,
          sideY: frameRailY - engineSideHeight,
          sideWidth: engineLength,
          sideHeight: engineSideHeight,
        };
      case 'AWD':
        // AWD通常前置，但可能有中置变体，这里默认前置
        return {
          topX: frontAxleX - engineLength - 20 * viewBoxScale,
          topY: engineTopY,
          topWidth: engineLength,
          topHeight: engineTopHeight,
          sideX: frontAxleX - engineLength - 20 * viewBoxScale,
          sideY: frameRailY - engineSideHeight,
          sideWidth: engineLength,
          sideHeight: engineSideHeight,
        };
      default:
        return {
          topX: frontAxleX - engineLength - 20 * viewBoxScale,
          topY: engineTopY,
          topWidth: engineLength,
          topHeight: engineTopHeight,
          sideX: frontAxleX - engineLength - 20 * viewBoxScale,
          sideY: frameRailY - engineSideHeight,
          sideWidth: engineLength,
          sideHeight: engineSideHeight,
        };
    }
  }, [layout, frontAxleX, rearAxleX, engineLength, engineTopY, engineTopHeight, engineSideHeight, frameRailY, viewBoxScale]);
  
  return (
    <div className="bg-slate-900 border border-cyan-500/30 rounded p-4">
      <h3 className="font-mono text-cyan-400 text-sm font-bold mb-3 uppercase">
        底盘蓝图
      </h3>
      
      <div className="flex justify-center">
        <svg
          width="100%"
          height="400"
          viewBox="0 0 1666.67 966.67"
          className="border border-slate-700 rounded bg-slate-950"
          preserveAspectRatio="xMidYMid meet"
        >
        <defs>
          {/* 网格图案 */}
          <pattern id="gridPattern" width="50" height="50" patternUnits="userSpaceOnUse">
            <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#1e293b" strokeWidth="0.5" />
          </pattern>
        </defs>
        
        {/* 网格背景 - 覆盖整个viewBox */}
        <rect
          x="-1666.67"
          y="-816.67"
          width="5000"
          height="3000"
          fill="url(#gridPattern)"
        />
        
        {/* ========== 顶视图（Y = 0-350）========== */}
        
        {/* 车架结构渲染（根据结构类型） */}
        {structure_type === 'LADDER' ? (
          <>
            {/* 非承载式：两条平行轨道 + 横梁 */}
            <rect
              x={railStartX}
              y={leftRailY - railThickness / 2}
              width={railLength}
              height={railThickness}
              fill="#06b6d4"
              fillOpacity="0.6"
              stroke="#06b6d4"
              strokeWidth={2 * viewBoxScale}
            />
            <rect
              x={railStartX}
              y={rightRailY - railThickness / 2}
              width={railLength}
              height={railThickness}
              fill="#06b6d4"
              fillOpacity="0.6"
              stroke="#06b6d4"
              strokeWidth={2 * viewBoxScale}
            />
            {crossmemberPositions.map((x, idx) => (
              <line
                key={`crossmember-${idx}`}
                x1={x}
                y1={leftRailY - railThickness / 2}
                x2={x}
                y2={rightRailY + railThickness / 2}
                stroke="#06b6d4"
                strokeWidth={4 * viewBoxScale}
              />
            ))}
          </>
        ) : (
          <>
            {/* 承载式：Perimeter Frame（周边框架）或Floor Pan样式 */}
            <rect
              x={railStartX}
              y={leftRailY - railSpacing / 2 - 30 * viewBoxScale}
              width={railLength}
              height={railSpacing + 60 * viewBoxScale}
              fill="#06b6d4"
              fillOpacity="0.4"
              stroke="#06b6d4"
              strokeWidth={3 * viewBoxScale}
              rx={5 * viewBoxScale}
            />
            {/* 内部加强筋（承载式特征） */}
            {crossmemberPositions.map((x, idx) => (
              <line
                key={`monocoque-stiffener-${idx}`}
                x1={x}
                y1={leftRailY - railSpacing / 2 - 30 * viewBoxScale}
                x2={x}
                y2={rightRailY + railSpacing / 2 + 30 * viewBoxScale}
                stroke="#06b6d4"
                strokeWidth={2 * viewBoxScale}
                strokeDasharray={`${8 * viewBoxScale} ${4 * viewBoxScale}`}
                opacity="0.6"
              />
            ))}
          </>
        )}
        
        {/* 后轴（垂直线） */}
        <line
          x1={rearAxleX}
          y1={topViewCenterY - track_rear_mm * scale * viewBoxScale / 2 - wheelThickness / 2}
          x2={rearAxleX}
          y2={topViewCenterY + track_rear_mm * scale * viewBoxScale / 2 + wheelThickness / 2}
          stroke="#60a5fa"
          strokeWidth={4 * viewBoxScale}
        />
        
        {/* 后左轮（厚重填充矩形） */}
        <rect
          x={rearAxleX - wheelWidth / 2}
          y={topViewCenterY - track_rear_mm * scale * viewBoxScale / 2 - wheelThickness / 2}
          width={wheelWidth}
          height={wheelThickness}
          fill="#334155"
          stroke="#06b6d4"
          strokeWidth={3 * viewBoxScale}
          rx={5 * viewBoxScale}
        />
        
        {/* 后右轮（厚重填充矩形） */}
        <rect
          x={rearAxleX - wheelWidth / 2}
          y={topViewCenterY + track_rear_mm * scale * viewBoxScale / 2 - wheelThickness / 2}
          width={wheelWidth}
          height={wheelThickness}
          fill="#334155"
          stroke="#06b6d4"
          strokeWidth={3 * viewBoxScale}
          rx={5 * viewBoxScale}
        />
        
        {/* 前轴（垂直线） */}
        <line
          x1={frontAxleX}
          y1={topViewCenterY - track_front_mm * scale * viewBoxScale / 2 - wheelThickness / 2}
          x2={frontAxleX}
          y2={topViewCenterY + track_front_mm * scale * viewBoxScale / 2 + wheelThickness / 2}
          stroke="#60a5fa"
          strokeWidth={4 * viewBoxScale}
        />
        
        {/* 前左轮（厚重填充矩形） */}
        <rect
          x={frontAxleX - wheelWidth / 2}
          y={topViewCenterY - track_front_mm * scale * viewBoxScale / 2 - wheelThickness / 2}
          width={wheelWidth}
          height={wheelThickness}
          fill="#334155"
          stroke="#06b6d4"
          strokeWidth={3 * viewBoxScale}
          rx={5 * viewBoxScale}
        />
        
        {/* 前右轮（厚重填充矩形） */}
        <rect
          x={frontAxleX - wheelWidth / 2}
          y={topViewCenterY + track_front_mm * scale * viewBoxScale / 2 - wheelThickness / 2}
          width={wheelWidth}
          height={wheelThickness}
          fill="#334155"
          stroke="#06b6d4"
          strokeWidth={3 * viewBoxScale}
          rx={5 * viewBoxScale}
        />
        
        {/* 发动机舱（顶视图，根据布局动态位置） */}
        {enginePosition && (
          <rect
            x={enginePosition.topX}
            y={enginePosition.topY}
            width={enginePosition.topWidth}
            height={enginePosition.topHeight}
            fill="#ef4444"
            fillOpacity="0.4"
            stroke="#ef4444"
            strokeWidth={3 * viewBoxScale}
            rx={3 * viewBoxScale}
          />
        )}
        
        {/* 传动系统可视化（顶视图） */}
        {layout === 'FR' && enginePosition && (
          <>
            {/* 传动轴（从引擎到后轴） */}
            <line
              x1={enginePosition.topX + enginePosition.topWidth}
              y1={topViewCenterY}
              x2={rearAxleX}
              y2={topViewCenterY}
              stroke="#fbbf24"
              strokeWidth={4 * viewBoxScale}
              strokeDasharray={`${10 * viewBoxScale} ${5 * viewBoxScale}`}
              opacity="0.7"
            />
            {/* 后差速器（Pumpkin） */}
            <circle
              cx={rearAxleX}
              cy={topViewCenterY}
              r={15 * viewBoxScale}
              fill="#fbbf24"
              fillOpacity="0.6"
              stroke="#fbbf24"
              strokeWidth={2 * viewBoxScale}
            />
          </>
        )}
        {layout === 'FF' && enginePosition && (
          <>
            {/* 前差速器（Pumpkin） */}
            <circle
              cx={frontAxleX}
              cy={topViewCenterY}
              r={15 * viewBoxScale}
              fill="#fbbf24"
              fillOpacity="0.6"
              stroke="#fbbf24"
              strokeWidth={2 * viewBoxScale}
            />
          </>
        )}
        {(layout === 'MR' || layout === 'RR') && enginePosition && (
          <>
            {/* 后差速器（Pumpkin） */}
            <circle
              cx={rearAxleX}
              cy={topViewCenterY}
              r={15 * viewBoxScale}
              fill="#fbbf24"
              fillOpacity="0.6"
              stroke="#fbbf24"
              strokeWidth={2 * viewBoxScale}
            />
          </>
        )}
        
        {/* ========== 侧视图（Y = 350-700）========== */}
        {showSideView && (
          <>
            {/* 地面线（白色） */}
            <line
              x1={0}
              y1={groundLineY}
              x2={1666.67 * viewBoxScale}
              y2={groundLineY}
              stroke="#ffffff"
              strokeWidth={3 * viewBoxScale}
            />
            
            {/* 后轮（厚重圆形，必须接触地面） */}
            <circle
              cx={rearAxleX}
              cy={wheelCenterY}
              r={wheelRadius}
              fill="#334155"
              stroke="#06b6d4"
              strokeWidth={4 * viewBoxScale}
            />
            {/* 轮毂（厚重） */}
            <circle
              cx={rearAxleX}
              cy={wheelCenterY}
              r={wheelRadius * 0.4}
              fill="#1e293b"
              stroke="#06b6d4"
              strokeWidth={3 * viewBoxScale}
            />
            
            {/* 前轮（厚重圆形，必须接触地面） */}
            <circle
              cx={frontAxleX}
              cy={wheelCenterY}
              r={wheelRadius}
              fill="#334155"
              stroke="#06b6d4"
              strokeWidth={4 * viewBoxScale}
            />
            <circle
              cx={frontAxleX}
              cy={wheelCenterY}
              r={wheelRadius * 0.4}
              fill="#1e293b"
              stroke="#06b6d4"
              strokeWidth={3 * viewBoxScale}
            />
            
            {/* 车架结构（侧视图，根据结构类型） */}
            {structure_type === 'LADDER' ? (
              <>
                {/* 非承载式：轨道 + 横梁标记 */}
                <rect
                  x={railStartX}
                  y={frameRailY - 20 * viewBoxScale}
                  width={railLength}
                  height={40 * viewBoxScale}
                  fill="#06b6d4"
                  fillOpacity="0.6"
                  stroke="#06b6d4"
                  strokeWidth={2 * viewBoxScale}
                />
                {crossmemberPositions.map((x, idx) => (
                  <line
                    key={`side-crossmember-${idx}`}
                    x1={x}
                    y1={frameRailY - 20 * viewBoxScale - 5 * viewBoxScale}
                    x2={x}
                    y2={frameRailY + 20 * viewBoxScale + 5 * viewBoxScale}
                    stroke="#06b6d4"
                    strokeWidth={3 * viewBoxScale}
                  />
                ))}
              </>
            ) : (
              <>
                {/* 承载式：Floor Pan（地板盘）样式 */}
                <rect
                  x={railStartX}
                  y={frameRailY - 30 * viewBoxScale}
                  width={railLength}
                  height={60 * viewBoxScale}
                  fill="#06b6d4"
                  fillOpacity="0.4"
                  stroke="#06b6d4"
                  strokeWidth={3 * viewBoxScale}
                  rx={3 * viewBoxScale}
                />
                {/* 承载式加强筋（侧视图） */}
                {crossmemberPositions.map((x, idx) => (
                  <line
                    key={`monocoque-side-stiffener-${idx}`}
                    x1={x}
                    y1={frameRailY - 30 * viewBoxScale}
                    x2={x}
                    y2={frameRailY + 30 * viewBoxScale}
                    stroke="#06b6d4"
                    strokeWidth={2 * viewBoxScale}
                    strokeDasharray={`${8 * viewBoxScale} ${4 * viewBoxScale}`}
                    opacity="0.6"
                  />
                ))}
              </>
            )}
            
            {/* 前悬挂（厚重垂直线） */}
            <line
              x1={frontAxleX}
              y1={wheelCenterY}
              x2={frontAxleX}
              y2={frameRailY}
              stroke="#06b6d4"
              strokeWidth={4 * viewBoxScale}
            />
            
            {/* 后悬挂（厚重垂直线） */}
            <line
              x1={rearAxleX}
              y1={wheelCenterY}
              x2={rearAxleX}
              y2={frameRailY}
              stroke="#06b6d4"
              strokeWidth={4 * viewBoxScale}
            />
            
            {/* 发动机舱（侧视图，根据布局动态位置） */}
            {enginePosition && (
              <rect
                x={enginePosition.sideX}
                y={enginePosition.sideY}
                width={enginePosition.sideWidth}
                height={enginePosition.sideHeight}
                fill="#ef4444"
                fillOpacity="0.4"
                stroke="#ef4444"
                strokeWidth={3 * viewBoxScale}
                rx={3 * viewBoxScale}
              />
            )}
            
            {/* 传动系统可视化（侧视图） */}
            {layout === 'FR' && enginePosition && (
              <>
                {/* 传动轴（从引擎到后轴） */}
                <line
                  x1={enginePosition.sideX + enginePosition.sideWidth}
                  y1={frameRailY - 10 * viewBoxScale}
                  x2={rearAxleX}
                  y2={frameRailY - 10 * viewBoxScale}
                  stroke="#fbbf24"
                  strokeWidth={4 * viewBoxScale}
                  strokeDasharray={`${10 * viewBoxScale} ${5 * viewBoxScale}`}
                  opacity="0.7"
                />
              </>
            )}
            
            {/* 对齐线（虚线，连接顶视图和侧视图的前轴） */}
            <line
              x1={frontAxleX}
              y1={topViewZone.max}
              x2={frontAxleX}
              y2={sideViewZone.min}
              stroke="#06b6d4"
              strokeWidth={1 * viewBoxScale}
              strokeDasharray={`${5 * viewBoxScale} ${5 * viewBoxScale}`}
              opacity="0.2"
            />
            
            {/* 尺寸线：轴距（侧视图下方） */}
            <g>
              {/* 尺寸线 */}
              <line
                x1={rearAxleX}
                y1={930 * viewBoxScale}
                x2={frontAxleX}
                y2={930 * viewBoxScale}
                stroke="#22d3ee"
                strokeWidth={2 * viewBoxScale}
                markerEnd="url(#arrowhead)"
                markerStart="url(#arrowhead-reverse)"
              />
              {/* 延长线 */}
              <line
                x1={rearAxleX}
                y1={wheelCenterY}
                x2={rearAxleX}
                y2={930 * viewBoxScale}
                stroke="#22d3ee"
                strokeWidth={1 * viewBoxScale}
                strokeDasharray={`${3 * viewBoxScale} ${3 * viewBoxScale}`}
              />
              <line
                x1={frontAxleX}
                y1={wheelCenterY}
                x2={frontAxleX}
                y2={930 * viewBoxScale}
                stroke="#22d3ee"
                strokeWidth={1 * viewBoxScale}
                strokeDasharray={`${3 * viewBoxScale} ${3 * viewBoxScale}`}
              />
              {/* 标签 - 放在横线下面 */}
              <text
                x={(rearAxleX + frontAxleX) / 2}
                y={980 * viewBoxScale}
                textAnchor="middle"
                className="text-[42px] fill-cyan-400 font-mono font-bold"
              >
                轴距: {wheelbase_mm}mm
              </text>
            </g>
          </>
        )}
        
        <defs>
          {/* 箭头标记 */}
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 10 3, 0 6" fill="#22d3ee" />
          </marker>
          <marker
            id="arrowhead-reverse"
            markerWidth="10"
            markerHeight="10"
            refX="1"
            refY="3"
            orient="auto"
          >
            <polygon points="10 0, 0 3, 10 6" fill="#22d3ee" />
          </marker>
        </defs>
      </svg>
      </div>
      
      {/* 图例 */}
      <div className="mt-4 grid grid-cols-3 gap-2 text-xs font-mono">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-cyan-400 bg-cyan-400/60"></div>
          <span className="text-slate-400">车架轨道</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-deep border-2 border-accent-primary rounded"></div>
          <span className="text-slate-400">车轮</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-red-500 bg-red-500/40"></div>
          <span className="text-slate-400">引擎舱</span>
        </div>
      </div>
    </div>
  );
};
