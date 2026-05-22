import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Lock } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface TechSelectOption {
  value: string | number;
  label: string;
  locked?: boolean;
  unlockHint?: string;
}

export interface TechSelectProps {
  label: string;
  value: string | number;
  options: TechSelectOption[];
  onChange: (value: string | number) => void;
  disabled?: boolean;
  className?: string;
}

/**
 * TechSelect - 智能技术选择组件
 * 支持选项级锁定、自定义下拉菜单
 */
export const TechSelect: React.FC<TechSelectProps> = ({
  label,
  value,
  options,
  onChange,
  disabled = false,
  className,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 关闭下拉菜单当点击外部时
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const selectedOption = options.find((opt) => opt.value === value);

  const handleSelect = (option: TechSelectOption) => {
    if (!option.locked && !disabled) {
      onChange(option.value);
      setIsOpen(false);
    }
  };

  return (
    <div className={cn('relative', className)}>
      {/* Label */}
      <label className="block text-xs font-mono text-secondary mb-1">
        {label}
      </label>

      {/* Dropdown Trigger */}
      <div
        ref={dropdownRef}
        className="relative"
      >
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          className={cn(
            'w-full bg-surface border border-surface-hover rounded-sm px-3 py-2',
            'text-sm font-mono text-primary',
            'flex items-center justify-between',
            'focus:border-accent-primary focus:outline-none',
            'transition-colors',
            disabled && 'opacity-50 cursor-not-allowed',
            !disabled && 'hover:border-accent-glow cursor-pointer'
          )}
        >
          <span className={selectedOption?.locked ? 'opacity-50' : ''}>
            {selectedOption?.label || '请选择...'}
          </span>
          <ChevronDown
            className={cn(
              'w-4 h-4 text-secondary transition-transform',
              isOpen && 'transform rotate-180'
            )}
          />
        </button>

        {/* Dropdown Menu */}
        {isOpen && (
          <div className="absolute z-50 w-full mt-1 bg-deep border border-surface-hover rounded-sm shadow-lg max-h-60 overflow-auto">
            {options.map((option) => {
              const isSelected = option.value === value;
              const isLocked = option.locked || false;

              return (
                <div
                  key={String(option.value)}
                  onClick={() => handleSelect(option)}
                  className={cn(
                    'px-3 py-2 text-sm font-mono',
                    'flex items-center justify-between gap-2',
                    'transition-colors',
                    isSelected && !isLocked && 'bg-accent-primary text-primary',
                    !isSelected && !isLocked && 'text-primary hover:bg-surface cursor-pointer',
                    isLocked && 'opacity-50 cursor-not-allowed text-secondary',
                    !isLocked && 'cursor-pointer'
                  )}
                  title={isLocked ? option.unlockHint || '此选项已锁定' : undefined}
                >
                  <span className="flex items-center gap-2">
                    {isLocked && <Lock className="w-3 h-3" />}
                    {option.label}
                  </span>
                  {isSelected && !isLocked && (
                    <span className="text-xs">✓</span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

