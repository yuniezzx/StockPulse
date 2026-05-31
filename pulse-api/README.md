# pulse-api

StockPulse API 网关（TypeScript + Fastify）：薄路由 + 用户数据写入 + 通知发送。

> 详细架构 → [`../docs/architecture.md`](../docs/architecture.md) §3
> 命名规则 → [`../docs/naming-conventions.md`](../docs/naming-conventions.md) §3
> AI 守则 → [`../AGENTS.md`](../AGENTS.md)

## 技术栈

- Node.js 22+ · pnpm 10+ · TypeScript 6
- Fastify 5 + `@fastify/cors` + `@fastify/jwt`
- Zod 4（请求/响应 schema 校验）
- pg（PostgreSQL 驱动；用 pool）
- bcrypt（密码哈希）
- pino-pretty（开发期日志格式）

## 命令

> 推荐从**仓库根目录**用 pnpm 别名调用：

```bash
pnpm api:dev                 # tsx watch + 自动加载 .env
pnpm api:build               # tsc 编译到 dist/
pnpm api:start               # node 跑 dist/server.js
pnpm api:typecheck           # tsc --noEmit
pnpm api:lint                # eslint --max-warnings=0
```

## 环境变量

环境变量集中在**仓库根** `.env`（不是子项目级）。pulse-api 关心的前缀：

- `DB_*` —— 数据库连接（与 pulse-core 共用同一个 PG 实例）
- `API_*` —— Fastify 自有配置（监听端口、host、log level）
- `JWT_*` —— JWT 签名密钥、过期时间
- `WEWORK_*` / `EMAIL_*` / `TELEGRAM_*` —— 通知通道凭据（按通道选用）

完整环境变量清单 → [`../docs/naming-conventions.md`](../docs/naming-conventions.md) §五。

## 目录约定

```
src/
├── server.ts                     Fastify 启动入口
├── config/                       env 校验（zod）
├── adapters/db/                  pg pool 适配
├── plugins/                      Fastify 插件
│   ├── cors.ts
│   ├── jwt.ts
│   └── error-handler.ts
├── shared/                       跨 domain 共享
│   ├── errors/                   领域无关错误类型
│   └── types/                    跨 domain 共享类型（barrel）
└── domains/{feature}/            一个业务域一目录（domain-driven）
    ├── routes.ts                 HTTP 路由（薄，只做参数校验 + 调 service）
    ├── service.ts                业务编排（不做重计算）
    ├── repository.ts             数据访问（snake_case row → camelCase entity 在此层转换）
    └── schemas.ts                Zod schema + 推导类型
```

**当前 domain 状态**：

- ✅ `auth/` —— 登录注册（已落地）
- 🚧 `picks/` `analysis/` `portfolio/` `virtual-portfolio/` `risk-signals/` `strategies/` `evaluations/` `outbox/` —— PLACEHOLDER，待实现

## 命名红线

- 文件名一律 `kebab-case.ts`
- 标识符 `camelCase`，组件 `PascalCase`
- 类型/接口**不加** `I` / `T` 前缀
- API 输出字段一律 `camelCase`，**禁止 snake_case 泄漏**（repository 层做转换）
- 股票代码统一叫 `tsCode`，禁止 `code` / `symbol` / `stockCode`
- 策略 key 与 DB / pulse-core 完全一致（snake_case，如 `"breakout"` / `"macd_cross"`）

## 边界铁律

- **不做重业务计算**（薄路由 + 编排；重计算属于 pulse-core）
- **只写圈 4 用户数据**（users / real_positions / strategy_weights / weight_decisions / preferences）
- **唯一写权限例外**：可向 `job_runs` INSERT `status='pending'` 行（用户手动触发入口），后续 UPDATE 由 pulse-core worker 接管（详见 architecture §3.2 ⑨）
- 通知用 outbox 模式：pulse-core 写表，pulse-api 在 07:00 cron 聚合后发送（架构 §5.4 / §5.5）

## 新增 API 端点流程

详见 [`../AGENTS.md`](../AGENTS.md) §4「新 API 端点」checklist。要点：

1. 在 `src/domains/{feature}/` 下补齐 4 件套（routes / service / repository / schemas）
2. Zod schema 字段一律 camelCase；repository 做 snake → camel 转换
3. 同步在 `pulse-web/src/lib/api/{feature}.ts` 补客户端函数（`getXxx` / `postXxx`）
4. 同步在 `pulse-web/src/hooks/use-{feature}.ts` 补 hook
