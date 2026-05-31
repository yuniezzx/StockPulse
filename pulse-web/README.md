# pulse-web

StockPulse 前端展示层（零业务计算）。

> 详细架构 → [`../docs/architecture.md`](../docs/architecture.md) §3
> 命名规则 → [`../docs/naming-conventions.md`](../docs/naming-conventions.md) §3
> AI 守则 → [`../AGENTS.md`](../AGENTS.md)

## 技术栈

- React 19 + Vite + TypeScript
- Tailwind v4 + shadcn/ui（radix-luma 风格）
- react-router v7
- zustand（auth 状态持久化）
- lightweight-charts（图表，按需）

## 命令

```bash
pnpm dev              # 启动开发服务器
pnpm build            # 类型检查 + 构建
pnpm typecheck        # 仅类型检查
pnpm lint             # ESLint
pnpm lint:fix         # ESLint 自动修复
pnpm format           # Prettier
```

## 环境变量

复制 `.env.example` 为 `.env`：

```
VITE_API_BASE_URL=http://localhost:3000
```

## 目录约定

```
src/
├── main.tsx
├── router/                       路由配置
├── store/                        zustand store（auth / preferences）
├── lib/
│   ├── api/                      一个 feature 一文件（getXxx / postXxx）
│   ├── nav.ts                    侧栏导航配置
│   ├── strategy-meta.ts          策略元数据（key/label/color）
│   ├── track-meta.ts             赛道元数据（scalp/swing/position）
│   ├── exit-reason-meta.ts       风控退出原因元数据
│   └── utils.ts                  cn() 等通用工具
├── hooks/                        use-xxx.ts
├── pages/                        路由页面（kebab-case）
└── components/
    ├── ui/                       shadcn 原子件（禁止业务逻辑）
    ├── layout/                   app-layout / app-sidebar / app-header
    ├── auth/                     protected-route / guest-route
    └── {feature}/                业务组件按 feature 分组
```

## 命名红线

- 文件名一律 `kebab-case`（含组件）
- 类型不加 `I` / `T` 前缀
- 字段名 `camelCase`，**禁止 snake_case 泄漏**（API 边界由 pulse-api 转换）
- 股票代码统一叫 `tsCode`
- 策略 key 与 DB / Python 完全一致（snake_case）
