/**
 * JWT plugin: 注册 @fastify/jwt + 暴露 `app.authenticate` preHandler。
 *
 * Token 载荷只放 `userId`（PublicUser 的不可变主键），不含 username 等可变字段，
 * 避免用户改名后 token 失效或显示陈旧信息。`/auth/me` 在每次请求时回查最新用户。
 *
 * 路由用法：
 *   app.get("/me", { onRequest: [app.authenticate] }, ...)
 */
import fastifyJwt from "@fastify/jwt";
import type { FastifyPluginAsync, FastifyReply, FastifyRequest } from "fastify";
import fp from "fastify-plugin";
import { env } from "../config/env.js";

declare module "fastify" {
  interface FastifyInstance {
    authenticate: (request: FastifyRequest, reply: FastifyReply) => Promise<void>;
  }
  interface FastifyRequest {
    user: { userId: string };
  }
}

declare module "@fastify/jwt" {
  interface FastifyJWT {
    payload: { userId: string };
    user: { userId: string };
  }
}

const jwtPlugin: FastifyPluginAsync = async (app) => {
  await app.register(fastifyJwt, {
    secret: env.JWT_SECRET,
    sign: { expiresIn: "7d" },
  });

  app.decorate("authenticate", async (request: FastifyRequest, reply: FastifyReply) => {
    try {
      await request.jwtVerify();
    } catch {
      return reply.status(401).send({
        error: "Unauthorized",
        message: "Invalid or missing token",
      });
    }
  });
};

export default fp(jwtPlugin, { name: "jwt" });
