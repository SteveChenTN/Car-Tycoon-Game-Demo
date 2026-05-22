# AutoMogul Frontend

基于 React + Vite + TypeScript 的汽车大亨游戏前端界面。

## 技术栈

- **框架**: React 18 + TypeScript
- **构建工具**: Vite 5
- **样式**: TailwindCSS (Cyan-Tech 设计系统)
- **图标**: Lucide React
- **图表**: Recharts
- **动画**: Framer Motion
- **状态管理**: Context API + WebSocket

## 设计理念

### Cyan-Tech 设计系统

- **配色方案**:
  - 背景: 深石板色 (`bg-slate-950`)
  - 主色调: 青色 (`text-cyan-400`, `border-cyan-500/50`)
  - 辅助色: 石板灰 (`text-slate-400`)
  - 边框: 细线边框 (`border-[1px] border-slate-800`)

- **排版**:
  - 数字: **严格使用** 等宽字体 (`font-mono`)
  - 文本: Inter / 系统无衬线字体
  - 密度: 中等密度 (基础文本 `text-sm` 14px，表格行高 `h-10` 40px)

- **布局架构**:
  - 固定左侧导航栏 (图标 + 标签)
  - **18:9 宽高比游戏容器** (模拟专用游戏窗口)
  - 超宽屏上容器居中，外部使用深色背景

## 安装与运行

### 前置要求

- Node.js 18+ 
- npm 或 yarn

### 安装依赖

```bash
cd frontend
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000

### 生产构建

```bash
npm run build
```

构建产物在 `dist/` 目录。

## 项目结构

```
frontend/
├── src/
│   ├── components/
│   │   └── layout/
│   │       ├── AppShell.tsx      # 主布局容器
│   │       ├── Sidebar.tsx       # 左侧导航
│   │       └── StatusBar.tsx     # 顶部状态栏
│   ├── contexts/
│   │   └── GameContext.tsx       # WebSocket 上下文
│   ├── pages/
│   │   └── Dashboard.tsx         # 仪表盘页面
│   ├── types/
│   │   └── index.ts              # TypeScript 类型定义
│   ├── utils/
│   │   └── formatters.ts         # 数字/日期格式化
│   ├── lib/
│   │   └── utils.ts              # 工具函数
│   ├── App.tsx                   # 根组件
│   ├── main.tsx                  # 入口文件
│   └── index.css                 # 全局样式
├── index.html
├── vite.config.ts
├── tailwind.config.js
└── package.json
```

## 功能特性

### 已实现

- ✅ 18:9 宽高比游戏容器
- ✅ 响应式侧边栏导航 (7个核心模块)
- ✅ 实时 WebSocket 连接
- ✅ 游戏状态显示
- ✅ 顶部状态栏 (日期/现金/GDP趋势)
- ✅ Cyan-Tech 设计系统
- ✅ 自定义滚动条
- ✅ 玻璃态面板效果

### 核心模块 (导航)

根据 `design_doc.md` 定义:

1. **Dashboard** - 仪表盘总览
2. **Design Studio** - 车辆设计工作室
3. **Factory** - 工厂管理
4. **Market** - 市场分析
5. **Executive** - 高管管理
6. **Research** - 研发中心
7. **Reports** - 报告中心

## WebSocket 通信

前端通过 WebSocket 连接到后端 `ws://localhost:8000/ws/game`

### 消息类型

- `game_state` - 游戏状态更新
- `event` - 游戏事件
- `notification` - 通知消息

### 自动重连

连接断开后，自动在 3 秒后尝试重连。

## 样式工具类

### 自定义类

- `.glass-panel` - 玻璃态面板
- `.retro-grid` - 复古网格背景
- `.cyan-glow` - 青色发光效果
- `.tech-border` - 技术风格边框
- `.number` - 数字专用等宽字体

### 按钮变体

- `.btn-primary` - 主按钮
- `.btn-secondary` - 次按钮
- `.btn-danger` - 危险按钮

### 表单元素

- `.input-field` - 输入框
- `.select-field` - 下拉框

## 开发注意事项

1. **数字格式化**: 所有数字必须使用 `formatters.ts` 中的函数
2. **类名合并**: 使用 `cn()` 函数合并 Tailwind 类名
3. **WebSocket**: 使用 `useGameContext()` Hook 访问游戏状态
4. **响应式**: 所有组件必须在 18:9 容器内正确显示

## 下一步

- [ ] 实现其他模块页面 (Design Studio, Factory, etc.)
- [ ] 集成 Recharts 图表
- [ ] 实现 Framer Motion 动画
- [ ] 添加键盘快捷键支持
- [ ] 实现主题切换 (可选)


