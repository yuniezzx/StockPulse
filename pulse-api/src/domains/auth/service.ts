/**
 * Auth service: 注册 / 登录 / 获取当前用户。
 *
 * 职责边界：
 *   - 密码哈希（bcrypt，SALT_ROUNDS=10）
 *   - 把 repository 返回的 snake_case UserRow 转成 camelCase PublicUser
 *   - 把 PG unique violation (23505) 翻译成 ConflictError
 *   - 签发 JWT 通过依赖注入的 signToken（解耦于 fastify 实例）
 */
import bcrypt from "bcrypt";
import { ConflictError, UnauthorizedError } from "../../shared/errors/index.js";
import * as repository from "./repository.js";
import type { UserRow } from "./repository.js";
import type { AuthSuccess, LoginBody, MeResponse, PublicUser, RegisterBody } from "./schemas.js";

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
    throw new UnauthorizedError("User no longer exists.");
  }
  return { user: toPublicUser(row) };
}
