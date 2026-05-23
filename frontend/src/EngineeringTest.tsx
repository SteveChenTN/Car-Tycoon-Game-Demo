import { EngineeringHub } from './pages/engineering';

/**
 * 工程模块独立测试入口
 * 
 * 使用方法：
 * 1. 在 main.tsx 中导入本文件
 * 2. 替换 <App /> 为 <EngineeringTest />
 * 3. 启动开发服务器: npm run dev
 */
function EngineeringTest() {
  return (
    <div className="w-screen h-screen bg-slate-950">
      <EngineeringHub />
    </div>
  );
}

export default EngineeringTest;


