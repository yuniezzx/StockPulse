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
