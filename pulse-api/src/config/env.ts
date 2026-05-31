/**
 * Environment variable schema + parse-once singleton.
 *
 * 启动期 fail-fast：env 不合法直接 process.exit(1)，避免后续运行时报错难定位。
 * .env 由 pnpm workspace 在仓库根目录加载（dotenv-cli / docker-compose），
 * 本文件只负责 schema 校验，不负责加载。
 */
import { z } from "zod";

const Schema = z.object({
  DATABASE_URL: z.url(),
  API_PORT: z.coerce.number().int().min(1).max(65535).default(3000),
  JWT_SECRET: z.string().min(16),
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  API_CORS_ORIGINS: z
    .string()
    .default("http://localhost:5173")
    .transform((s) =>
      s
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
    ),
});

const result = Schema.safeParse(process.env);

if (!result.success) {
  console.error("❌ Invalid environment variables:");
  console.error(z.prettifyError(result.error));
  process.exit(1);
}

export const env = result.data;
