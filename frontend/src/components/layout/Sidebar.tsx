import { 
  LayoutDashboard, 
  Wrench, 
  Factory, 
  TrendingUp, 
  Users, 
  FlaskConical,
  FileText,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useLanguage } from '@/contexts/LanguageContext';
import type { NavigationModule } from '@/types';

// ============================================================
// Navigation Items (Based on design_doc.md)
// ============================================================

interface NavItem {
  id: NavigationModule;
  labelKey: string;
  icon: React.ComponentType<{ className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: 'dashboard',
    labelKey: 'nav.dashboard',
    icon: LayoutDashboard,
  },
  {
    id: 'design',
    labelKey: 'nav.design',
    icon: Wrench,
  },
  {
    id: 'factory',
    labelKey: 'nav.factory',
    icon: Factory,
  },
  {
    id: 'market',
    labelKey: 'nav.market',
    icon: TrendingUp,
  },
  {
    id: 'executive',
    labelKey: 'nav.executive',
    icon: Users,
  },
  {
    id: 'research',
    labelKey: 'nav.research',
    icon: FlaskConical,
  },
  {
    id: 'reports',
    labelKey: 'nav.reports',
    icon: FileText,
  },
];

// ============================================================
// Sidebar Component
// ============================================================

interface SidebarProps {
  activeModule: NavigationModule;
  onNavigate: (module: NavigationModule) => void;
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ activeModule, onNavigate, isOpen = false, onClose }: SidebarProps) {
  const { t } = useLanguage();

  // Handle navigation and close sidebar on mobile
  const handleNavigate = (module: NavigationModule) => {
    onNavigate(module);
    // Close sidebar on mobile after navigation
    if (onClose) {
      onClose();
    }
  };

  return (
    <>
      {/* Mobile: Background Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar - Fixed 260px on desktop, drawer on mobile */}
      <aside
        className={cn(
          // Base styles
          'w-[260px] h-full flex flex-col bg-surface border-r border-surface-hover flex-shrink-0',
          // Desktop: always visible
          'hidden md:flex',
          // Mobile: drawer behavior
          'md:relative fixed top-0 left-0 z-50 md:z-auto',
          'transition-transform duration-300 ease-in-out',
          // Mobile: slide in/out
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        )}
      >
        {/* Logo Area */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-surface-hover">
          <div className="text-accent-primary font-bold text-xl">AM</div>
          {/* Mobile: Close Button */}
          {onClose && (
            <button
              onClick={onClose}
              className="md:hidden p-2 text-secondary hover:text-accent-primary transition-colors"
              aria-label="Close sidebar"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 py-4 overflow-y-auto">
          <ul className="space-y-2">
            {NAV_ITEMS.map((item) => {
              const isActive = item.id === activeModule;
              const Icon = item.icon;
              const label = t(item.labelKey);

              return (
                <li key={item.id}>
                  <button
                    onClick={() => handleNavigate(item.id)}
                    className={cn(
                      'w-full flex items-center gap-3 py-3 px-4 transition-colors group',
                      'hover:bg-surface-hover/50',
                      isActive && 'bg-surface-hover border-r-2 border-accent-primary'
                    )}
                    title={label}
                  >
                    <Icon
                      className={cn(
                        'w-5 h-5 transition-colors flex-shrink-0',
                        isActive ? 'text-accent-primary' : 'text-secondary group-hover:text-accent-primary'
                      )}
                    />
                    <span
                      className={cn(
                        'text-sm font-medium transition-colors',
                        isActive ? 'text-accent-primary' : 'text-primary group-hover:text-accent-primary'
                      )}
                    >
                      {label}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Bottom Status Indicator */}
        <div className="h-12 flex items-center justify-center border-t border-surface-hover">
          <div className="w-2 h-2 rounded-full bg-accent-success animate-pulse" title={t('status.connected')} />
        </div>
      </aside>
    </>
  );
}

