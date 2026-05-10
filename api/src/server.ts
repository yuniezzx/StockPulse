import Fastify from "fastify";
import { env } from "./config/env.js";
import { closePool } from "./adapters/db/pool.js";
import jwtPlugin from "./plugins/jwt.js";
import authRoutes from "./domains/auth/routes.js";

const app = Fastify({
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

app.get("/health", async () => {
  return { status: "ok" };
});

async function main(): Promise<void> {
  try {
    await app.register(jwtPlugin);
    await app.register(authRoutes);
    await app.listen({ port: env.API_PORT, host: "0.0.0.0" });
  } catch (error) {
    app.log.error(error);
    process.exit(1);
  }
}

// ============ Graceful Shutdown ============

const SHUTDOWN_TIMEOUT_MS = 10_000; // k8s 默认 30s 强杀，这里留足余量
let shuttingDown = false;

async function shutdown(reason: string): Promise<void> {
  if (shuttingDown) {
    app.log.warn(`Shutdown already in progress, ignoring: ${reason}`);
    return;
  }
  shuttingDown = true;

  app.log.info({ reason }, "Shutting down...");

  // 超时兜底:即使关闭流程卡死,也强制退出
  const forceExitTimer = setTimeout(() => {
    app.log.error(`Shutdown timeout after ${SHUTDOWN_TIMEOUT_MS}ms, forcing exit`);
    process.exit(1);
  }, SHUTDOWN_TIMEOUT_MS);
  forceExitTimer.unref();

  try {
    // 1. 停止接收新请求 + 等 in-flight 请求完成
    await app.close();
    app.log.info("HTTP server closed");

    // 2. 关闭数据库连接池
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

// 进程信号:Ctrl+C / kill / Docker stop / k8s 终止
const signals = ["SIGINT", "SIGTERM"] as const;
for (const signal of signals) {
  process.on(signal, () => {
    void shutdown(`signal: ${signal}`);
  });
}

// 未捕获的同步异常
process.on("uncaughtException", (err) => {
  app.log.fatal({ err }, "Uncaught exception");
  void shutdown("uncaughtException");
});

// 未捕获的 Promise rejection
process.on("unhandledRejection", (reason) => {
  app.log.fatal({ reason }, "Unhandled rejection");
  void shutdown("unhandledRejection");
});

void main();
