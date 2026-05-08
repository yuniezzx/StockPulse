必读（已用到的核心 4 个）
1. PostgreSQL — 你天天接触的数据库
- 官方教程（最系统）：https://www.postgresql.org/docs/17/tutorial.html
- 重点章节（30 分钟可读完）：
  - 2.3-2.10：CREATE TABLE / INSERT / SELECT / 约束基础
  - 5.4：CHECK 约束（你 users 表用了）
  - 13：事务和并发控制（你 migrate.ts 用了）
- 你的盲点：TIMESTAMPTZ vs TIMESTAMP、UUID 类型、索引（下一阶段加 username 唯一索引时会用到）
2. node-postgres (pg) — 你的 DB 驱动
- 官方文档：https://node-postgres.com/
- 重点：
  - Pool (https://node-postgres.com/apis/pool) ← 你用的这个
  - Pool 的 client (https://node-postgres.com/apis/pool#poolconnect) ← 事务用的
  - Parameterized Queries (https://node-postgres.com/features/queries#parameterized-query) ← $1 占位符
  - Transactions (https://node-postgres.com/features/transactions) ← BEGIN/COMMIT/ROLLBACK 套路
- 你的盲点：连接池行为、pool.query vs client.query 的区别、错误事件
3. TypeScript — 你的语言
- 官方手册：https://www.typescriptlang.org/docs/handbook/intro.html
- 重点（按你的薄弱点排序）：
  - Generics (https://www.typescriptlang.org/docs/handbook/2/generics.html) ← pool.query<T> 那个
  - Modules (https://www.typescriptlang.org/docs/handbook/2/modules.html) ← nodenext + .js 后缀的诡异约定
  - Narrowing (https://www.typescriptlang.org/docs/handbook/2/narrowing.html) ← process.exit 是 never 的原因
  - Utility Types (https://www.typescriptlang.org/docs/handbook/utility-types.html) ← Promise<T>、Pick、Omit
- 盲点诊断：你之前不太确定返回类型该写什么 → narrowing + utility types 补强
4. Node.js (核心 API) — 你的运行时
- 官方文档：https://nodejs.org/api/
- 重点（你用过的）：
  - fs/promises (https://nodejs.org/api/fs.html#promises-api) ← readFile、readdir
  - path (https://nodejs.org/api/path.html) ← join、dirname
  - url (https://nodejs.org/api/url.html#urlfileurltopathurl) ← fileURLToPath
  - Process (https://nodejs.org/api/process.html) ← process.exit、process.on(signal)、process.env
  - --env-file (https://nodejs.org/api/cli.html#--env-fileconfig) ← 你 scripts 用的
- 盲点诊断：信号处理、graceful shutdown 的 timer + unref()
---
建议看（即将用到，看了能让 E 阶段更顺）
5. Fastify — 你的 web 框架
- 官方文档：https://fastify.dev/docs/latest/
- 必看（按顺序）：
  - Getting Started (https://fastify.dev/docs/latest/Guides/Getting-Started/) — 30 分钟
  - Routes (https://fastify.dev/docs/latest/Reference/Routes/) — app.get/post、handler 签名、reply 对象
  - Validation (https://fastify.dev/docs/latest/Reference/Validation-and-Serialization/) — Fastify 自带的 schema 校验（用 JSON Schema 的，跟 Zod 不一样）
  - Plugins (https://fastify.dev/docs/latest/Reference/Plugins/) — fastify-plugin 的封装套路（E 阶段写 jwt/cors plugin 时关键）
  - Hooks (https://fastify.dev/docs/latest/Reference/Hooks/) — onRequest / preHandler（鉴权用）
- 跳过：性能调优、HTTP/2、自定义 logger transport（暂时不用）
6. Zod — 你的校验库
- 官方文档：https://zod.dev/
- 必看：
  - Basic Usage (https://zod.dev/?id=basic-usage)
  - Object schemas (https://zod.dev/?id=objects)
  - String validators (https://zod.dev/?id=strings)
  - z.infer (https://zod.dev/?id=type-inference)
  - Error handling (https://zod.dev/?id=error-handling)（prettifyError 你已经用过）
- 跳过：transform、refine 的高级用法（用到再看）
7. JWT 概念（不是某个库的文档，是协议）
- 入门可视化（必看，10 分钟）：https://jwt.io/introduction
- 重点理解：
  - JWT 三段结构（header.payload.signature）
  - 签名 ≠ 加密（payload 是 base64，谁都能解码看内容）
  - 服务端怎么验证签名
- 跳过：JWE（加密 JWT，你用不上）、各种算法细节（HS256 够用）
8. bcrypt
- bcrypt (npm) 官方 README：https://github.com/kelektiv/node.bcrypt.js#readme
- 够用，10 分钟看完。重点：hash / compare 两个函数、salt rounds 的含义。
---
选读（深度补强，有时间再看）
9. ESLint Flat Config
- 你已经在用，但配置写得有点 magic。如果想理解：https://eslint.org/docs/latest/use/configure/configuration-files
10. pnpm 工作区
- 你现在没用 monorepo，但以后 web/ + api/ 共享类型时会用：https://pnpm.io/workspaces
11. @fastify/jwt / @fastify/cors 插件文档
- 用之前直接看 README 就够：
  - https://github.com/fastify/fastify-jwt
  - https://github.com/fastify/fastify-cors
---
复习建议（按"投入产出比"排序）
如果只有 2 小时：
1. 30 分钟 — JWT 入门（jwt.io/introduction）+ bcrypt README
2. 30 分钟 — Fastify Getting Started + Routes
3. 30 分钟 — Zod Basic Usage + Object schemas + z.infer
4. 30 分钟 — node-postgres 的 Pool + Transactions 章节
如果有 4 小时，再加：
5. 1 小时 — TypeScript Generics + Narrowing 两章
6. 1 小时 — PostgreSQL 教程 5.4 (约束) + 第 13 章 (事务)
如果有一整天，再加：
7. Node.js process / fs/promises 文档通读
8. Fastify 完整文档（Plugins + Hooks + Validation）
---
一个反向技巧：带问题去读文档
不要从头读到尾。每读一节问自己：
> "我之前写的代码里，哪个地方用到了这个？我当时是不是似懂非懂？"
比如读 pool.connect() 文档时，回想你的 applyMigration 里 const client = await pool.connect() —— 现在能不能解释为什么不能用 pool.query 跑事务？能 → 跳过。卡壳 → 这一节认真读。
已经写过的代码就是你最好的索引。
---