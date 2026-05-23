/**
 * PLACEHOLDER: outbox domain routes not yet implemented.
 * 通知出箱状态查询/重发入口（pulse-core 写表，pulse-api 07:00 聚合发送）。
 * 详见 docs/architecture.md §4.4 outbox 模式。
 */
import type { FastifyInstance } from "fastify";

export async function outboxRoutes(_app: FastifyInstance): Promise<void> {}
