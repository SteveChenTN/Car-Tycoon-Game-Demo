import { createContext, useContext, useState, ReactNode } from 'react';

// ============================================================
// 翻译字典
// ============================================================

type Language = 'en' | 'zh';

interface Translations {
  [key: string]: {
    en: string;
    zh: string;
  };
}

const translations: Translations = {
  // === Navigation ===
  'nav.dashboard': { en: 'Dashboard', zh: '仪表盘' },
  'nav.design': { en: 'Design Studio', zh: '设计工作室' },
  'nav.factory': { en: 'Factory', zh: '工厂' },
  'nav.market': { en: 'Market', zh: '市场' },
  'nav.executive': { en: 'Executive', zh: '执行层' },
  'nav.research': { en: 'Research', zh: '研发' },
  'nav.reports': { en: 'Reports', zh: '报表' },

  // === Status Bar Labels ===
  'status.date': { en: 'Date', zh: '日期' },
  'status.turn': { en: 'Turn', zh: '回合' },
  'status.cash': { en: 'Cash', zh: '现金' },
  'status.worldGDP': { en: 'World GDP', zh: '全球GDP' },
  'status.pause': { en: 'Pause', zh: '暂停' },
  'status.resume': { en: 'Resume', zh: '继续' },
  'status.connected': { en: 'Connected', zh: '已连接' },
  'status.disconnected': { en: 'Disconnected', zh: '未连接' },
  'status.nextTurn': { en: 'Next Turn', zh: '下一回合' },
  'status.nextWeek': { en: 'NEXT WEEK', zh: '下一周' },
  'status.simulating': { en: 'Simulating...', zh: '模拟中...' },
  'status.holdToAdvance': { en: 'Hold to advance', zh: '按住推进' },

  // === Main Menu ===
  'menu.title': { en: 'AUTOMOGUL', zh: '汽车大亨' },
  'menu.subtitle': { en: 'Build Your Automotive Empire', zh: '打造您的汽车帝国' },
  'menu.newGame': { en: 'New Game', zh: '新游戏' },
  'menu.loadGame': { en: 'Load Game', zh: '加载游戏' },
  'menu.settings': { en: 'Settings', zh: '设置' },
  'menu.quit': { en: 'Quit', zh: '退出' },
  'menu.back': { en: 'Back', zh: '返回' },

  // === Pause Menu ===
  'pause.title': { en: 'Game Paused', zh: '游戏已暂停' },
  'pause.resume': { en: 'Resume Game', zh: '继续游戏' },
  'pause.save': { en: 'Save Game', zh: '保存游戏' },
  'pause.load': { en: 'Load Game', zh: '加载游戏' },
  'pause.settings': { en: 'Settings', zh: '设置' },
  'pause.mainMenu': { en: 'Main Menu', zh: '主菜单' },

  // === Settings ===
  'settings.title': { en: 'Settings', zh: '设置' },
  'settings.language': { en: 'Language', zh: '语言' },
  'settings.audio': { en: 'Audio', zh: '音频' },
  'settings.graphics': { en: 'Graphics', zh: '图形' },
  'settings.gameplay': { en: 'Gameplay', zh: '游戏' },

  // === Save/Load ===
  'save.title': { en: 'Save Game', zh: '保存游戏' },
  'save.name': { en: 'Save Name', zh: '存档名称' },
  'save.success': { en: 'Game Saved Successfully', zh: '游戏保存成功' },
  'save.error': { en: 'Save Failed', zh: '保存失败' },
  'load.title': { en: 'Load Game', zh: '加载游戏' },
  'load.empty': { en: 'No Saves Found', zh: '未找到存档' },
  'load.confirm': { en: 'Load this save?', zh: '加载此存档？' },
  'load.success': { en: 'Game Loaded Successfully', zh: '游戏加载成功' },
  'load.error': { en: 'Load Failed', zh: '加载失败' },

  // === Financial Terms ===
  'finance.revenue': { en: 'Revenue', zh: '营收' },
  'finance.profit': { en: 'Profit', zh: '利润' },
  'finance.expenses': { en: 'Expenses', zh: '支出' },
  'finance.assets': { en: 'Assets', zh: '资产' },
  'finance.liabilities': { en: 'Liabilities', zh: '负债' },
  'finance.equity': { en: 'Equity', zh: '权益' },
  'finance.cashFlow': { en: 'Cash Flow', zh: '现金流' },

  // === Engineering Terms ===
  'eng.displacement': { en: 'Displacement', zh: '排量' },
  'eng.horsepower': { en: 'Horsepower', zh: '马力' },
  'eng.torque': { en: 'Torque', zh: '扭矩' },
  'eng.efficiency': { en: 'Efficiency', zh: '效率' },
  'eng.reliability': { en: 'Reliability', zh: '可靠性' },
  'eng.emissions': { en: 'Emissions', zh: '排放' },
  'eng.fuelEconomy': { en: 'Fuel Economy', zh: '燃油经济性' },

  // === Production Terms ===
  'prod.capacity': { en: 'Capacity', zh: '产能' },
  'prod.utilization': { en: 'Utilization', zh: '利用率' },
  'prod.retooling': { en: 'Retooling', zh: '产线改造' },
  'prod.automation': { en: 'Automation', zh: '自动化' },
  'prod.quality': { en: 'Quality', zh: '质量' },
  'prod.efficiency': { en: 'Efficiency', zh: '效率' },
  'prod.output': { en: 'Output', zh: '产出' },

  // === Market Terms ===
  'market.demand': { en: 'Demand', zh: '需求' },
  'market.supply': { en: 'Supply', zh: '供给' },
  'market.price': { en: 'Price', zh: '价格' },
  'market.marketShare': { en: 'Market Share', zh: '市场份额' },
  'market.competition': { en: 'Competition', zh: '竞争' },
  'market.segment': { en: 'Segment', zh: '细分市场' },
  'market.trend': { en: 'Trend', zh: '趋势' },

  // === Common Buttons ===
  'btn.confirm': { en: 'Confirm', zh: '确认' },
  'btn.cancel': { en: 'Cancel', zh: '取消' },
  'btn.save': { en: 'Save', zh: '保存' },
  'btn.load': { en: 'Load', zh: '加载' },
  'btn.delete': { en: 'Delete', zh: '删除' },
  'btn.edit': { en: 'Edit', zh: '编辑' },
  'btn.close': { en: 'Close', zh: '关闭' },
  'btn.back': { en: 'Back', zh: '返回' },
  'btn.next': { en: 'Next', zh: '下一步' },
  'btn.submit': { en: 'Submit', zh: '提交' },
  'btn.reset': { en: 'Reset', zh: '重置' },

  // === Common Labels ===
  'common.name': { en: 'Name', zh: '名称' },
  'common.description': { en: 'Description', zh: '描述' },
  'common.date': { en: 'Date', zh: '日期' },
  'common.status': { en: 'Status', zh: '状态' },
  'common.type': { en: 'Type', zh: '类型' },
  'common.category': { en: 'Category', zh: '类别' },
  'common.total': { en: 'Total', zh: '总计' },
  'common.loading': { en: 'Loading...', zh: '加载中...' },
  'common.error': { en: 'Error', zh: '错误' },
  'common.success': { en: 'Success', zh: '成功' },
};

// ============================================================
// Context Types
// ============================================================

interface LanguageContextValue {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextValue | undefined>(undefined);

// ============================================================
// Provider Component
// ============================================================

interface LanguageProviderProps {
  children: ReactNode;
  defaultLanguage?: Language;
}

export function LanguageProvider({ children, defaultLanguage = 'en' }: LanguageProviderProps) {
  const [language, setLanguage] = useState<Language>(() => {
    // Try to load from localStorage
    const stored = localStorage.getItem('automogul_language');
    if (stored === 'en' || stored === 'zh') {
      return stored;
    }
    return defaultLanguage;
  });

  const handleSetLanguage = (lang: Language) => {
    setLanguage(lang);
    localStorage.setItem('automogul_language', lang);
  };

  const t = (key: string): string => {
    const translation = translations[key];
    if (!translation) {
      console.warn(`Translation missing for key: ${key}`);
      return key;
    }
    return translation[language];
  };

  return (
    <LanguageContext.Provider
      value={{
        language,
        setLanguage: handleSetLanguage,
        t,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

// ============================================================
// Hook
// ============================================================

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within LanguageProvider');
  }
  return context;
}

