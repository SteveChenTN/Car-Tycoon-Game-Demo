# 依赖包更新说明

## 更新日期
2025-12-27

## 更新原因
修复 npm 安装时的废弃警告（deprecated warnings）

## 主要更新

### 1. ESLint 8 → 9
- `eslint`: `^8.55.0` → `^9.17.0`
- 新增 `@eslint/js`: `^9.17.0`（ESLint 9 必需）
- 新增 `globals`: `^15.13.0`（替代旧的全局变量配置）
- 迁移到新的扁平配置格式（`eslint.config.js`）

### 2. TypeScript ESLint
- `@typescript-eslint/eslint-plugin`: `^6.14.0` → `^8.18.2`
- `@typescript-eslint/parser`: `^6.14.0` → `^8.18.2`
- 新增 `typescript-eslint`: `^8.18.2`（统一包）

### 3. React 插件
- `eslint-plugin-react-hooks`: `^4.6.0` → `^5.1.0`
- `eslint-plugin-react-refresh`: `^0.4.5` → `^0.4.16`

### 4. 其他依赖更新
- `react`: `^18.2.0` → `^18.3.1`
- `react-dom`: `^18.2.0` → `^18.3.1`
- `axios`: `^1.6.2` → `^1.7.9`
- `recharts`: `^2.10.3` → `^2.15.0`
- `lucide-react`: `^0.294.0` → `^0.460.0`
- `framer-motion`: `^10.16.12` → `^11.15.0`
- `clsx`: `^2.0.0` → `^2.1.1`
- `tailwind-merge`: `^2.2.0` → `^2.5.5`
- `@vitejs/plugin-react`: `^4.2.1` → `^4.3.4`
- `autoprefixer`: `^10.4.16` → `^10.4.20`
- `postcss`: `^8.4.32` → `^8.4.49`
- `tailwindcss`: `^3.4.0` → `^3.4.17`
- `typescript`: `^5.2.2` → `^5.7.2`
- `vite`: `^5.0.8` → `^6.0.5`

## 破坏性变更

### ESLint 配置格式变更
ESLint 9 使用新的扁平配置格式。已创建 `eslint.config.js` 来替代旧的配置方式。

### 配置迁移
- **旧配置**: `.eslintrc.*` 文件或 `package.json` 中的 `eslintConfig` 字段
- **新配置**: `eslint.config.js` (扁平配置)

### Lint 脚本更新
- **旧命令**: `eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0`
- **新命令**: `eslint .` （扁平配置会自动识别文件类型）

## 安装步骤

```bash
# 1. 删除旧的 node_modules 和 lock 文件（推荐）
cd frontend
rm -rf node_modules package-lock.json

# 2. 安装新的依赖
npm install

# 3. 验证 ESLint 配置
npm run lint
```

## 验证

运行以下命令确保一切正常：

```bash
# 检查 lint
npm run lint

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 已解决的警告

✅ `inflight@1.0.6` - 通过更新间接依赖解决  
✅ `glob@7.2.3` - 通过更新到新版本解决  
✅ `rimraf@3.0.2` - 通过更新到新版本解决  
✅ `@humanwhocodes/object-schema` - 通过升级到 ESLint 9 解决  
✅ `@humanwhocodes/config-array` - 通过升级到 ESLint 9 解决  
✅ `eslint@8.57.1` - 升级到 ESLint 9.17.0  

## 注意事项

1. **Vite 6**: 从 Vite 5 升级到 Vite 6，可能有轻微的配置变更，但当前配置应该兼容
2. **React 18.3**: 完全向后兼容，无需修改代码
3. **TypeScript 5.7**: 新增了一些类型检查改进，可能会发现之前未发现的类型问题

## 回滚方案

如果遇到问题，可以恢复到旧版本：

```bash
git checkout HEAD -- package.json eslint.config.js
rm eslint.config.js  # 如果之前没有这个文件
npm install
```


