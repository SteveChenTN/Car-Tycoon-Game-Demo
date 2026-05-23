import React, { useState, useRef, useEffect } from 'react';
import { ComponentInfo } from '../../services/engineeringService';

interface ComponentRichSelectProps {
  label: string;
  value: string;
  options: ComponentInfo[];
  isLoading?: boolean;
  onChange: (value: string) => void;
}

/**
 * ComponentRichSelect - 带熟悉度信息的组件选择器
 * 显示悬停Tooltip，包含成本修正、可靠性修正和熟悉度等级
 */
export const ComponentRichSelect: React.FC<ComponentRichSelectProps> = ({
  label,
  value,
  options,
  isLoading,
  onChange,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [hoveredOption, setHoveredOption] = useState<ComponentInfo | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  // 查找当前选中的选项
  const selectedOption = options.find((opt) => opt.value === value);

  // 处理选项悬停
  const handleOptionHover = (option: ComponentInfo, event: React.MouseEvent) => {
    setHoveredOption(option);
    const rect = event.currentTarget.getBoundingClientRect();
    setTooltipPosition({
      x: rect.right + 10,
      y: rect.top,
    });
  };

  // 处理选项离开
  const handleOptionLeave = () => {
    setHoveredOption(null);
  };

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isOpen]);

  // 调整Tooltip位置（避免超出屏幕）
  useEffect(() => {
    if (hoveredOption && tooltipRef.current) {
      const tooltip = tooltipRef.current;
      const rect = tooltip.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      let x = tooltipPosition.x;
      let y = tooltipPosition.y;

      // 如果超出右边界，显示在左侧
      if (rect.right > viewportWidth) {
        x = tooltipPosition.x - rect.width - 20;
      }

      // 如果超出下边界，向上调整
      if (rect.bottom > viewportHeight) {
        y = viewportHeight - rect.height - 10;
      }

      tooltip.style.left = `${x}px`;
      tooltip.style.top = `${y}px`;
    }
  }, [hoveredOption, tooltipPosition]);

  if (isLoading) {
    return (
      <div className="mb-3">
        <label className="block text-xs font-mono text-secondary mb-1">{label}</label>
        <div className="w-full bg-surface border border-surface-hover rounded px-2 py-1 text-xs font-mono text-muted">
          加载中...
        </div>
      </div>
    );
  }

  return (
    <div className="mb-3 relative" ref={containerRef}>
      <label className="block text-xs font-mono text-secondary mb-1">{label}</label>
      
      {/* 选择按钮 */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full bg-surface border border-surface-hover rounded px-2 py-1 text-xs md:text-sm font-mono text-primary focus:border-accent-primary focus:outline-none flex items-center justify-between hover:border-accent-glow transition-colors"
      >
        <span>{selectedOption?.value || value}</span>
        {selectedOption && (selectedOption.familiarity_level || selectedOption.familiarity_level === 0) && (
          <span className="text-accent-primary text-xs ml-2">
            Lv.{selectedOption.familiarity_level}
          </span>
        )}
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* 下拉菜单 */}
      {isOpen && (
        <div 
          className="absolute z-50 w-full mt-1 bg-deep border border-accent-primary/30 rounded shadow-lg max-h-60 overflow-auto"
          onMouseLeave={() => setHoveredOption(null)} // 当鼠标离开下拉菜单时清除tooltip
        >
          {options.length === 0 ? (
            <div className="px-3 py-2 text-xs font-mono text-muted text-center">
              无可用选项
            </div>
          ) : (
            options.map((option) => (
            <div
              key={option.value}
              onClick={() => {
                onChange(option.value);
                setIsOpen(false);
                setHoveredOption(null); // 清除tooltip
              }}
              onMouseEnter={(e) => handleOptionHover(option, e)}
              onMouseLeave={handleOptionLeave}
              className={`px-3 py-2 text-xs font-mono cursor-pointer transition-colors flex items-center justify-between ${
                option.value === value
                  ? 'bg-accent-primary/20 text-accent-primary'
                  : 'text-primary hover:bg-surface-hover'
              }`}
            >
              <span>{option.value}</span>
              {option.familiarity_level !== undefined && (
                <span className="text-accent-primary text-xs ml-2">
                  Lv.{option.familiarity_level}
                </span>
              )}
            </div>
            ))
          )}
        </div>
      )}

      {/* Tooltip */}
      {hoveredOption && (
        <div
          ref={tooltipRef}
          className="fixed z-50 bg-deep border border-accent-primary/50 rounded p-3 shadow-xl min-w-[200px] pointer-events-none"
          style={{
            left: `${tooltipPosition.x}px`,
            top: `${tooltipPosition.y}px`,
          }}
        >
          <div className="font-mono text-xs space-y-1">
            <div className="text-accent-primary font-bold mb-2">{hoveredOption.value}</div>
            
            {hoveredOption.familiarity_level !== undefined && (
              <div className="flex justify-between">
                <span className="text-secondary">熟悉度等级:</span>
                <span className="text-accent-primary font-bold">Lv.{hoveredOption.familiarity_level}</span>
              </div>
            )}
            
            {hoveredOption.cost_modifier !== undefined && hoveredOption.cost_modifier !== 0 && (
              <div className="flex justify-between">
                <span className="text-secondary">成本修正:</span>
                <span className={hoveredOption.cost_modifier < 0 ? 'text-accent-success' : 'text-accent-danger'}>
                  {hoveredOption.cost_modifier > 0 ? '+' : ''}
                  {(hoveredOption.cost_modifier * 100).toFixed(1)}%
                </span>
              </div>
            )}
            
            {hoveredOption.reliability_modifier !== undefined && hoveredOption.reliability_modifier !== 0 && (
              <div className="flex justify-between">
                <span className="text-secondary">可靠性修正:</span>
                <span className={hoveredOption.reliability_modifier > 0 ? 'text-accent-success' : 'text-accent-danger'}>
                  {hoveredOption.reliability_modifier > 0 ? '+' : ''}
                  {(hoveredOption.reliability_modifier * 100).toFixed(1)}%
                </span>
              </div>
            )}
            
            {(!hoveredOption.familiarity_level || hoveredOption.familiarity_level === 1) && 
             (!hoveredOption.cost_modifier || hoveredOption.cost_modifier === 0) &&
             (!hoveredOption.reliability_modifier || hoveredOption.reliability_modifier === 0) && (
              <div className="text-muted text-xs">无熟悉度加成</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
