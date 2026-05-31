/**
 * pulse-api HTTP server entry point.
 *
 * 启动顺序（register 顺序决定中间件链）：
 *   cors -> jwt -> error-handler -> /auth -> 各业务 domain -> /health
 *
 * 优雅停机（SIGINT/SIGTERM/uncaughtException/unhandledRejection）：
 *   1. app.close() 关闭 HTTP server，拒绝新连接、等已有请求结束
 *   2. closePool() 关闭 pg 连接池
 *   3. 10s 超时后强制退出（兜底，避免悬挂）
 *
 * 8 个业务 domain 目前多为占位（routes 内 export 空函数），随业务推进逐步填充；
 * 边界规则见 AGENTS.md §2：pulse-api 写圈 4 用户数据 + 转发计算结果，不做重计算。
 */
import Fastify from "fastify";
import { randomUUID } from "node:crypto";
import { env } from "./config/env.js";
import { closePool } from "./adapters/db/pool.js";
import corsPlugin from "./plugins/cors.js";
import jwtPlugin from "./plugins/jwt.js";
import errorHandlerPlugin from "./plugins/error-handler.js";
import { authRoutes } from "./domains/auth/routes.js";
import { picksRoutes } from "./domains/picks/routes.js";
import { analysisRoutes } from "./domains/analysis/routes.js";
import { portfolioRoutes } from "./domains/portfolio/routes.js";
import { virtualPortfolioRoutes } from "./domains/virtual-portfolio/routes.js";
import { riskSignalsRoutes } from "./domains/risk-signals/routes.js";
import { strategiesRoutes } from "./domains/strategies/routes.js";
import { evaluationsRoutes } from "./domains/evaluations/routes.js";
import { outboxRoutes } from "./domains/outbox/routes.js";

const app = Fastify({
  genReqId: () => randomUUID(),
  logger: {
    transport: {
      target: "pino-pretty",
      options: {
        translateTime: "HH:MM:ss",
        ignore: "pid,hostname",
      },
    },
  },
});

async function main(): Promise<void> {
  try {
    await app.register(corsPlugin);
    await app.register(jwtPlugin);
    await app.register(errorHandlerPlugin);
    await app.register(authRoutes, { prefix: "/auth" });
    await app.register(picksRoutes, { prefix: "/picks" });
    await app.register(analysisRoutes, { prefix: "/analysis" });
    await app.register(portfolioRoutes, { prefix: "/portfolio" });
    await app.register(virtualPortfolioRoutes, { prefix: "/virtual-portfolio" });
    await app.register(riskSignalsRoutes, { prefix: "/risk-signals" });
    await app.register(strategiesRoutes, { prefix: "/strategies" });
    await app.register(evaluationsRoutes, { prefix: "/evaluations" });
    await app.register(outboxRoutes, { prefix: "/outbox" });
    app.get("/health", async () => ({ status: "ok" }));
    await app.listen({ port: env.API_PORT, host: "0.0.0.0" });
  } catch (error) {
    app.log.error(error);
    process.exit(1);
  }
}

const SHUTDOWN_TIMEOUT_MS = 10_000;
let shuttingDown = false;

async function shutdown(reason: string): Promise<void> {
  if (shuttingDown) {
    app.log.warn(`Shutdown already in progress, ignoring: ${reason}`);
    return;
  }
  shuttingDown = true;

  app.log.info({ reason }, "Shutting down...");

  const forceExitTimer = setTimeout(() => {
    app.log.error(`Shutdown timeout after ${SHUTDOWN_TIMEOUT_MS}ms, forcing exit`);
    process.exit(1);
  }, SHUTDOWN_TIMEOUT_MS);
  forceExitTimer.unref();

  try {
    await app.close();
    app.log.info("HTTP server closed");

    await closePool();
    app.log.info("Database pool closed");

    clearTimeout(forceExitTimer);
    process.exit(0);
  } catch (err) {
    app.log.error({ err }, "Error during shutdown");
    clearTimeout(forceExitTimer);
    process.exit(1);
  }
}

const signals = ["SIGINT", "SIGTERM"] as const;
for (const signal of signals) {
  process.on(signal, () => {
    void shutdown(`signal: ${signal}`);
  });
}

process.on("uncaughtException", (err) => {
  app.log.fatal({ err }, "Uncaught exception");
  void shutdown("uncaughtException");
});

process.on("unhandledRejection", (reason) => {
  app.log.fatal({ reason }, "Unhandled rejection");
  void shutdown("unhandledRejection");
});

void main();
