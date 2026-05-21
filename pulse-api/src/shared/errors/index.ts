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
