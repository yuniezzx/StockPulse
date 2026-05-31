/**
 * PostgreSQL connection pool (node-postgres).
 *
 * pulse-api 唯一的 DB 访问出口。所有 SQL 查询通过 `query()` 走这里，
 * 便于统一观察连接池压力 + 集中处理参数化查询。
 *
 * 命名边界（AGENTS.md §1 红线）：
 *   DB 列名 snake_case，由 repository 层负责 snake -> camel 转换；
 *   snake_case 字段禁止泄漏到 service / route / 前端。
 */
import { Pool, type QueryResult, type QueryResultRow } from "pg";
import { env } from "../../config/env.js";

export const pool = new Pool({
  connectionString: env.DATABASE_URL,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

pool.on("error", (err) => {
  console.error("Unexpected pg pool error", err);
});

export async function query<T extends QueryResultRow>(
  text: string,
  params?: unknown[],
): Promise<QueryResult<T>> {
  return pool.query<T>(text, params);
}

export async function closePool(): Promise<void> {
  await pool.end();
}
