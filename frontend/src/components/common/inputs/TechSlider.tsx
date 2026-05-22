import React from 'react';
import { Lock } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface TechSliderProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  unit?: string;
  locked?: boolean;
  unlockHint?: string;
  costImpact?: number; // 正数=成本增加，负数=成本减少
  step?: number;
  className?: string;
}

/**
 * TechSlider - 智能技术滑块组件
 * 支持锁定状态、成本反馈、工业风格设计
 */
export const TechSlider: React.FC<TechSliderProps> = ({
  label,
  value,
  onChange,
  min,
  max,
  unit = '',
  locked = false,
  unlockHint,
  costImpact,
  step = 1,
  className,
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!locked) {
      onChange(parseFloat(e.target.value));
    }
  };

  const formatValue = (val: number): string => {
    if (step < 1) {
      return val.toFixed(1);
    }
    return val.toFixed(0);
  };

  const costImpactColor = costImpact
    ? costImpact > 0
      ? 'text-accent-danger'
      : 'text-accent-success'
    : '';

  const costImpactText = costImpact
    ? costImpact > 0
      ? `+$${Math.abs(costImpact).toFixed(0)}`
      : `-$${Math.abs(costImpact).toFixed(0)}`
    : '';

  return (
    <div className={cn('relative', className)}>
      {/* Label and Value Row */}
      <div className="flex justify-between items-center text-xs font-mono mb-1">
        <span className="text-secondary">{label}</span>
        <div className="flex items-center gap-2">
          <span className="text-accent-primary font-bold">
            {formatValue(value)}
            {unit}
          </span>
          {costImpact && (
            <span className={cn('text-xs font-bold', costImpactColor)}>
              {costImpactText}
            </span>
          )}
        </div>
      </div>

      {/* Slider Container with Lock Overlay */}
      <div className="relative">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={handleChange}
          disabled={locked}
          className={cn(
            'w-full h-1 bg-surface-hover rounded-sm appearance-none cursor-pointer',
            'accent-accent-primary',
            locked && 'grayscale cursor-not-allowed opacity-50',
            !locked && 'hover:accent-accent-glow'
          )}
        />

        {/* Lock Overlay */}
        {locked && (
          <div
            className="absolute inset-0 flex items-center justify-center bg-deep/50 rounded-sm cursor-not-allowed group"
            title={unlockHint || '此选项已锁定'}
          >
            <Lock className="w-4 h-4 text-muted group-hover:text-secondary transition-colors" />
            {/* Tooltip on hover */}
            {unlockHint && (
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-surface border border-surface-hover rounded-sm text-xs text-secondary opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                {unlockHint}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

