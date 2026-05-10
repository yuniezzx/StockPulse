import bcrypt from "bcrypt";
import * as repository from "./repository.js";
import type { UserRow } from "./repository.js";
import type { AuthSuccess, LoginBody, MeResponse, PublicUser, RegisterBody } from "./schemas.js";

export class ConflictError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ConflictError";
  }
}

export class UnauthorizedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "UnauthorizedError";
  }
}

export class NotFoundError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NotFoundError";
  }
}

export type SignToken = (payload: { userId: string }) => string;

const SALT_ROUNDS = 10;
const PG_UNIQUE_VIOLATION = "23505";

function toPublicUser(row: UserRow): PublicUser {
  return {
    id: row.id,
    username: row.username,
    createdAt: row.created_at.toISOString(),
  };
}

function isPgUniqueViolation(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "code" in err &&
    (err as { code: unknown }).code === PG_UNIQUE_VIOLATION
  );
}

// ========================== 业务函数 ==========================

export async function register(input: RegisterBody, signToken: SignToken): Promise<AuthSuccess> {
  const passwordHash = await bcrypt.hash(input.password, SALT_ROUNDS);

  let row: UserRow;
  try {
    row = await repository.create(input.username, passwordHash);
  } catch (err) {
    if (isPgUniqueViolation(err)) {
      throw new ConflictError(`Username "${input.username}" is already taken.`);
    }
    throw err;
  }

  const user = toPublicUser(row);
  const token = signToken({ userId: user.id });
  return { user, token };
}

export async function login(input: LoginBody, signToken: SignToken): Promise<AuthSuccess> {
  const row = await repository.findByUsername(input.username);
  if (row === null) {
    throw new UnauthorizedError("Invalid credentials");
  }

  const passwordMatch = await bcrypt.compare(input.password, row.password_hash);
  if (!passwordMatch) {
    throw new UnauthorizedError("Invalid credentials");
  }

  const user = toPublicUser(row);
  const token = signToken({ userId: user.id });
  return { user, token };
}

export async function getMe(userId: string): Promise<MeResponse> {
  const row = await repository.findById(userId);
  if (row === null) {
    throw new NotFoundError("User not found.");
  }
  return { user: toPublicUser(row) };
}
