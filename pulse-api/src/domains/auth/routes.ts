/**
 * Auth routes: POST /register · POST /login · GET /me
 *
 * route 层只做三件事：解析 Zod schema、把 JWT sign 注入 service、转发返回值。
 * 业务逻辑 / 错误抛出全部在 service.ts；错误响应由 plugins/error-handler.ts 兜底。
 */
import type { FastifyInstance } from "fastify";
import { loginBodySchema, registerBodySchema } from "./schemas.js";
import { getMe, login, register, type SignToken } from "./service.js";

export async function authRoutes(app: FastifyInstance): Promise<void> {
  const signToken: SignToken = (payload) => app.jwt.sign(payload);

  app.post("/register", async (request) => {
    const body = registerBodySchema.parse(request.body);
    return register(body, signToken);
  });

  app.post("/login", async (request) => {
    const body = loginBodySchema.parse(request.body);
    return login(body, signToken);
  });

  app.get("/me", { onRequest: [app.authenticate] }, async (request) => {
    const { userId } = request.user;
    return getMe(userId);
  });
}
