/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ============================================================
        // SEMANTIC DESIGN TOKENS - Industrial Sci-Fi / Cyberpunk Theme
        // ============================================================
        
        // Backgrounds (use as: bg-deep, bg-surface, bg-surface-hover)
        'deep': '#0f172a',           // Slate-900 - Main background
        'surface': '#1e293b',        // Slate-800 - Cards/Panels
        'surface-hover': '#334155',  // Slate-700 - Hover states
        
        // Accents (The "Energy" Colors) - use as: bg-accent-primary, text-accent-primary, etc.
        'accent-primary': '#06b6d4',    // Cyan-500 - Active states, Primary buttons
        'accent-glow': '#22d3ee',       // Cyan-400 - Box-shadows/glows
        'accent-danger': '#ef4444',     // Red-500 - Errors, Critical warnings
        'accent-success': '#10b981',    // Emerald-500 - Positive cashflow, Ready state
        'accent-warning': '#f59e0b',    // Amber-500 - Locked tech, Low funds
        
        // Text (use as: text-primary, text-secondary, text-muted)
        'primary': '#f8fafc',      // Slate-50 - Headings
        'secondary': '#94a3b8',    // Slate-400 - Labels, Hints
        'muted': '#475569',        // Slate-600 - Disabled text
        
        // Legacy support (backward compatibility)
        'industrial': {
          bg: '#0f172a',
          panel: '#1e293b',
          accent: '#06b6d4',
        },
        'cyan-tech': {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
          700: '#0e7490',
          800: '#155e75',
          900: '#164e63',
        },
      },
      fontFamily: {
        // UI/Labels: Inter (Clean, readable)
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
        // Data/Numbers/Code: JetBrains Mono (Tabular numbers for engineering)
        mono: ['JetBrains Mono', 'Fira Code', 'Roboto Mono', 'Consolas', 'Monaco', 'Courier New', 'monospace'],
      },
      aspectRatio: {
        '18/9': '18 / 9',
      },
      boxShadow: {
        'glow-primary': '0 0 20px rgba(6, 182, 212, 0.3)',
        'glow-glow': '0 0 20px rgba(34, 211, 238, 0.2)',
        'glow-danger': '0 0 20px rgba(239, 68, 68, 0.3)',
        'glow-success': '0 0 20px rgba(16, 185, 129, 0.3)',
      },
    },
  },
  plugins: [],
}

