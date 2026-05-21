import type { FastifyPluginAsync } from "fastify";
import fp from "fastify-plugin";
import { ZodError } from "zod";
import { DomainError } from "../shared/errors/index.js";

const errorHandlerPlugin: FastifyPluginAsync = async (app) => {
  app.setErrorHandler((error, _request, reply) => {
    if (error instanceof ZodError) {
      return reply.status(400).send({
        error: "ValidationError",
        message: "Invalid request body",
        issues: error.issues,
      });
    }

    if (error instanceof DomainError) {
      return reply.status(error.statusCode).send({
        error: error.name,
        message: error.message,
      });
    }

    app.log.error({ error }, "Unhandled error");
    return reply.status(500).send({
      error: "InternalServerError",
      message: "An unexpected error occurred",
    });
  });
};

export default fp(errorHandlerPlugin, { name: "error-handler" });
