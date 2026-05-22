import React from 'react';
import { ArrowLeft, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface RDBaseLayoutStep {
  id: number;
  name: string;
  icon?: React.ComponentType<{ className?: string }>;
}

export interface RDBaseLayoutProps {
  title: string;
  subtitle?: string;
  programCost?: number; // 百万游戏币单位
  steps?: RDBaseLayoutStep[];
  currentStepIndex?: number;
  onBackToHQ?: () => void;
  children: React.ReactNode;
}

/**
 * RDBaseLayout - R&D页面统一布局包装器
 * 提供统一的Header和灵活的主内容区
 */
export const RDBaseLayout: React.FC<RDBaseLayoutProps> = ({
  title,
  subtitle,
  programCost,
  steps,
  currentStepIndex,
  onBackToHQ,
  children,
}) => {
  const handleBack = () => {
    if (onBackToHQ) {
      onBackToHQ();
    }
  };

  return (
    <div className="h-full flex flex-col bg-deep text-primary">
      {/* Header - Fixed Top Bar */}
      <div className="bg-gradient-to-r from-accent-primary/20 to-surface border-b border-accent-glow/50 px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between gap-4">
          {/* Left: Back Button */}
          <button
            onClick={handleBack}
            className="flex items-center gap-2 px-4 py-2 rounded-sm font-mono text-sm font-bold transition-colors bg-surface hover:bg-surface-hover text-primary border border-surface-hover"
          >
            <ArrowLeft className="w-4 h-4" />
            返回总部
          </button>

          {/* Center: Title */}
          <div className="flex-1 text-center">
            <h1 className="text-2xl font-bold font-mono text-accent-primary">
              {title}
            </h1>
            {subtitle && (
              <p className="text-secondary text-sm font-mono mt-1">
                {subtitle}
              </p>
            )}
          </div>

          {/* Right: Budget Widget and Step Indicator */}
          <div className="flex items-center gap-4">
            {/* Budget Widget */}
            {programCost !== undefined && (
              <div className="bg-deep/80 border-2 border-accent-success/50 rounded-sm px-6 py-3 shadow-lg">
                <div className="text-xs font-mono text-secondary uppercase mb-1">
                  预算成本
                </div>
                <div className="text-2xl font-mono font-bold text-accent-success tracking-wider">
                  ${programCost.toFixed(1)}M
                </div>
              </div>
            )}

            {/* Step Indicator */}
            {steps && currentStepIndex !== undefined && (
              <div className="flex items-center gap-2">
                {steps.map((step, idx) => {
                  const Icon = step.icon;
                  const isActive = currentStepIndex === idx;
                  const isCompleted = currentStepIndex > idx;

                  return (
                    <React.Fragment key={step.id}>
                      <div
                        className={cn(
                          'flex items-center gap-2',
                          isActive && 'cursor-default',
                          !isActive && !isCompleted && 'cursor-pointer'
                        )}
                        onClick={() => {
                          // 可以添加点击跳转逻辑，但需要父组件提供goToStep函数
                          // 这里暂时不实现，因为需要额外的props
                        }}
                      >
                        <div
                          className={cn(
                            'w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all',
                            isActive
                              ? 'bg-accent-primary border-accent-glow text-primary'
                              : isCompleted
                              ? 'bg-accent-success border-accent-success text-primary'
                              : 'bg-surface border-surface-hover text-secondary'
                          )}
                        >
                          {isCompleted ? (
                            <CheckCircle2 className="w-5 h-5" />
                          ) : Icon ? (
                            <Icon className="w-5 h-5" />
                          ) : (
                            <span className="text-xs font-bold">{idx + 1}</span>
                          )}
                        </div>
                        <span
                          className={cn(
                            'font-mono text-sm hidden md:block',
                            isActive ? 'text-accent-primary font-bold' : 'text-secondary'
                          )}
                        >
                          {step.name}
                        </span>
                      </div>
                      {idx < steps.length - 1 && (
                        <div className="w-8 h-0.5 bg-surface-hover" />
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content - Flexible Container */}
      <div className="flex-1 relative overflow-auto">
        {children}
      </div>
    </div>
  );
};

