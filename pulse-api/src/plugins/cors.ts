/**
 * CORS plugin: 允许 API_CORS_ORIGINS 列出的来源跨域访问。
 *
 * 个人项目场景下默认放行 http://localhost:5173（pulse-web vite dev），
 * 部署到内网时通过 API_CORS_ORIGINS 显式声明域名（逗号分隔）。
 */
import fastifyCors from "@fastify/cors";
import type { FastifyPluginAsync } from "fastify";
import fp from "fastify-plugin";
import { env } from "../config/env.js";

const corsPlugin: FastifyPluginAsync = async (app) => {
  await app.register(fastifyCors, {
    origin: env.API_CORS_ORIGINS,
    methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allowedHeaders: ["content-type", "authorization"],
  });
};

export default fp(corsPlugin, { name: "cors" });
