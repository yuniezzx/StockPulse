import type { FastifyInstance } from "fastify";
import { ZodError } from "zod";
import { loginBodySchema, registerBodySchema } from "./schemas.js";
import {
  ConflictError,
  NotFoundError,
  UnauthorizedError,
  getMe,
  login,
  register,
  type SignToken,
} from "./service.js";

export default async function authRoutes(app: FastifyInstance): Promise<void> {
  const signToken: SignToken = (payload) => app.jwt.sign(payload);

  app.setErrorHandler((error, _request, reply) => {
    if (error instanceof ZodError) {
      return reply.status(400).send({
        error: "ValidationError",
        message: "Invalid request body",
        issues: error.issues,
      });
    }
    if (error instanceof ConflictError) {
      return reply.status(409).send({ error: "ConflictError", message: error.message });
    }
    if (error instanceof UnauthorizedError) {
      return reply.status(401).send({ error: "Unauthorized", message: error.message });
    }
    if (error instanceof NotFoundError) {
      return reply.status(404).send({ error: "NotFound", message: error.message });
    }

    app.log.error({ error }, "Unhandled error in auth routes");
    return reply
      .status(500)
      .send({ error: "InternalServerError", message: "An unexpected error occurred" });
  });

  app.post("/auth/register", async (request) => {
    const body = registerBodySchema.parse(request.body);
    return register(body, signToken);
  });

  app.post("/auth/login", async (request) => {
    const body = loginBodySchema.parse(request.body);
    return login(body, signToken);
  });

  app.get("/auth/me", { onRequest: [app.authenticate] }, async (request) => {
    const { userId } = request.user;
    return getMe(userId);
  });
}
