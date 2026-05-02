# Frontend — TransAPI Station 前端

API 中转站前端应用，提供用户界面和管理后台界面。使用字节跳动 Arco Design 组件库。

## 技术栈

- React 18 + TypeScript
- Arco Design (@arco-design/web-react)
- Vite 5
- React Router v6
- Axios
- Recharts（图表）
- Day.js

## 快速开始

```bash
npm install
npm run dev   # 开发模式，端口 3000
npm run build # 生产构建，输出到 dist/
```

## 页面概览

### 用户界面
- **仪表盘**：余额、调用次数、Token 消耗、费用趋势
- **API Key 管理**：创建/吊销 Key
- **账单明细**：请求日志、费用汇总
- **充值**：兑换码充值
- **接入文档**：快速开始指南

### 管理后台
- **管理仪表盘**：总览统计、趋势图
- **用户管理**：搜索/编辑/禁用用户
- **流控配置**：RPM/TPM 限额
- **代理池管理**：直连 Token / 账号池双模式
- **充值码管理**：批量生成、查看状态
- **系统统计**：收入趋势、模型分布

## UI 风格

- 主色：#165DFF（Arco Blue）
- 字节风格：简约、专业
- 侧边栏导航 + 内容区布局
- 支持亮色/暗色主题切换

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_API_BASE_URL` | 后端 API 地址 | `http://localhost:8080` |
