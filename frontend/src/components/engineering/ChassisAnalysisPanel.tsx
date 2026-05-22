/**
 * ChassisAnalysisPanel - 底盘分析反馈面板
 * 包含雷达图和测试车手反馈
 */
import React from 'react';
import { TrendingUp, MessageSquare, DollarSign, Weight, Clock, Loader2, AlertCircle } from 'lucide-react';

export interface ChassisFeedback {
  scores: {
    rigidity: number;
    nvh: number;
    safety: number;
    manufacturing_ease: number;
    character: number;
  };
  feedback_text: string;
}

export interface ChassisAnalysisPanelProps {
  /** 测试车手反馈 */
  feedback?: ChassisFeedback;
  /** 单位成本估算 */
  estimatedCost?: number;
  /** R&D时间估算（周） */
  estimatedRndWeeks?: number;
  /** 重量估算（kg） */
  estimatedWeight?: number;
  /** 是否正在加载 */
  isLoading?: boolean;
  /** 错误信息 */
  error?: string | null;
  /** 可靠性评分 (0-100) */
  reliabilityScore?: number;
  /** 最大载荷 (N) */
  maxLoad?: number;
}

// 简单的雷达图组件（使用SVG）
const RadarChart: React.FC<{ scores: ChassisFeedback['scores'] }> = ({ scores }) => {
  const size = 200;
  const center = size / 2;
  const radius = 80;
  const axes = [
    { name: '刚性', key: 'rigidity', angle: -Math.PI / 2 },
    { name: 'NVH', key: 'nvh', angle: -Math.PI / 2 + (2 * Math.PI / 5) },
    { name: '安全', key: 'safety', angle: -Math.PI / 2 + (4 * Math.PI / 5) },
    { name: '制造便利', key: 'manufacturing_ease', angle: -Math.PI / 2 + (6 * Math.PI / 5) },
    { name: '特色', key: 'character', angle: -Math.PI / 2 + (8 * Math.PI / 5) },
  ];
  
  const getPoint = (angle: number, value: number) => {
    const r = radius * value;
    const x = center + r * Math.cos(angle);
    const y = center + r * Math.sin(angle);
    return { x, y };
  };
  
  const points = axes.map((axis) => getPoint(axis.angle, scores[axis.key as keyof typeof scores]));
  const pathData = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z';
  
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="mx-auto">
      {/* 背景网格 */}
      {[0.2, 0.4, 0.6, 0.8, 1.0].map((scale) => (
        <circle
          key={scale}
          cx={center}
          cy={center}
          r={radius * scale}
          fill="none"
          stroke="#334155"
          strokeWidth="1"
          opacity={0.3}
        />
      ))}
      
      {/* 轴线 */}
      {axes.map((axis, i) => {
        const point = getPoint(axis.angle, 1.0);
        return (
          <line
            key={i}
            x1={center}
            y1={center}
            x2={point.x}
            y2={point.y}
            stroke="#475569"
            strokeWidth="1"
            opacity={0.5}
          />
        );
      })}
      
      {/* 数据区域 */}
      <path
        d={pathData}
        fill="rgba(139, 92, 246, 0.3)"
        stroke="#8b5cf6"
        strokeWidth="2"
      />
      
      {/* 数据点 */}
      {points.map((point, i) => (
        <circle
          key={i}
          cx={point.x}
          cy={point.y}
          r="4"
          fill="#8b5cf6"
          stroke="#fff"
          strokeWidth="1"
        />
      ))}
      
      {/* 标签 */}
      {axes.map((axis, i) => {
        const labelPoint = getPoint(axis.angle, 1.15);
        return (
          <text
            key={i}
            x={labelPoint.x}
            y={labelPoint.y}
            textAnchor="middle"
            className="text-[10px] fill-slate-400 font-mono"
          >
            {axis.name}
          </text>
        );
      })}
    </svg>
  );
};

export const ChassisAnalysisPanel: React.FC<ChassisAnalysisPanelProps> = ({
  feedback,
  estimatedCost,
  estimatedRndWeeks,
  estimatedWeight,
  isLoading = false,
  error = null,
  reliabilityScore,
  maxLoad,
}) => {
  const defaultScores = {
    rigidity: 0.5,
    nvh: 0.5,
    safety: 0.5,
    manufacturing_ease: 0.5,
    character: 0.5,
  };
  
  const scores = feedback?.scores || defaultScores;
  const feedbackText = feedback?.feedback_text || "测试车手：'等待参数输入...'";
  
  return (
    <div className="bg-slate-900 border border-purple-500/30 rounded p-4 space-y-4">
      <h3 className="font-mono text-purple-400 text-sm font-bold mb-3 uppercase flex items-center gap-2">
        <TrendingUp className="w-4 h-4" />
        分析反馈
      </h3>
      
      {/* 雷达图 */}
      <div className="bg-slate-800/50 rounded p-4 border border-slate-700">
        <h4 className="text-xs font-mono text-slate-400 mb-3 text-center">性能雷达图</h4>
        <RadarChart scores={scores} />
      </div>
      
      {/* 测试车手反馈 */}
      <div className="bg-slate-800/50 rounded p-4 border border-slate-700">
        <h4 className="text-xs font-mono text-slate-400 mb-2 flex items-center gap-2">
          <MessageSquare className="w-3 h-3" />
          测试车手反馈
        </h4>
        <div className="text-xs text-slate-300 font-mono leading-relaxed italic">
          {feedbackText}
        </div>
      </div>
      
      {/* 加载状态 */}
      {isLoading && (
        <div className="bg-slate-800/50 rounded p-3 border border-cyan-500/30 flex items-center gap-2 text-cyan-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-xs font-mono">计算中...</span>
        </div>
      )}

      {/* 错误信息 */}
      {error && !isLoading && (
        <div className="bg-red-900/20 rounded p-3 border border-red-500/30 flex items-center gap-2 text-red-400">
          <AlertCircle className="w-4 h-4" />
          <span className="text-xs font-mono">{error}</span>
        </div>
      )}

      {/* 成本/重量/时间估算 */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        {estimatedCost !== undefined && (
          <div className="bg-slate-800/50 rounded p-2 border border-slate-700">
            <div className="flex items-center gap-1 text-slate-400 mb-1">
              <DollarSign className="w-3 h-3" />
              <span className="font-mono">单位成本</span>
            </div>
            <div className="text-cyan-400 font-mono font-bold">
              ${(estimatedCost / 1000).toFixed(1)}k
            </div>
          </div>
        )}
        
        {estimatedWeight !== undefined && (
          <div className="bg-slate-800/50 rounded p-2 border border-slate-700">
            <div className="flex items-center gap-1 text-slate-400 mb-1">
              <Weight className="w-3 h-3" />
              <span className="font-mono">重量</span>
            </div>
            <div className="text-cyan-400 font-mono font-bold">
              {estimatedWeight.toFixed(0)}kg
            </div>
          </div>
        )}
        
        {estimatedRndWeeks !== undefined && (
          <div className="bg-slate-800/50 rounded p-2 border border-slate-700">
            <div className="flex items-center gap-1 text-slate-400 mb-1">
              <Clock className="w-3 h-3" />
              <span className="font-mono">R&D时间</span>
            </div>
            <div className="text-cyan-400 font-mono font-bold">
              {estimatedRndWeeks}周
            </div>
          </div>
        )}
      </div>

      {/* 物理引擎返回的额外数据 */}
      {(reliabilityScore !== undefined || maxLoad !== undefined) && (
        <div className="grid grid-cols-2 gap-2 text-xs mt-2">
          {reliabilityScore !== undefined && (
            <div className="bg-slate-800/50 rounded p-2 border border-slate-700">
              <div className="flex items-center gap-1 text-slate-400 mb-1">
                <span className="font-mono">可靠性</span>
              </div>
              <div className="text-green-400 font-mono font-bold">
                {reliabilityScore.toFixed(1)}%
              </div>
            </div>
          )}
          
          {maxLoad !== undefined && (
            <div className="bg-slate-800/50 rounded p-2 border border-slate-700">
              <div className="flex items-center gap-1 text-slate-400 mb-1">
                <span className="font-mono">最大载荷</span>
              </div>
              <div className="text-purple-400 font-mono font-bold">
                {(maxLoad / 1000).toFixed(0)}kN
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

