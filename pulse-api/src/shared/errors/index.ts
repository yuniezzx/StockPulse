/**
 * Domain error hierarchy: 每个子类对应一个 HTTP 状态码。
 *
 * service 层抛出 DomainError 子类，由 plugins/error-handler.ts 翻译成 HTTP 响应。
 * 这样 service 不依赖 fastify 类型，单测好写；route 层也几乎不需要 try/catch。
 */
export abstract class DomainError extends Error {
  abstract readonly statusCode: number;

  constructor(message: string) {
    super(message);
    this.name = this.constructor.name;
  }
}

export class ConflictError extends DomainError {
  readonly statusCode = 409;

  constructor(message: string) {
    super(message);
  }
}

export class UnauthorizedError extends DomainError {
  readonly statusCode = 401;

  constructor(message: string) {
    super(message);
  }
}

export class NotFoundError extends DomainError {
  readonly statusCode = 404;

  constructor(message: string) {
    super(message);
  }
}

export class ValidationError extends DomainError {
  readonly statusCode = 400;

  constructor(message: string) {
    super(message);
  }
}
