import { query } from "../../adapters/db/pool.js";

export interface UserRow {
  id: string;
  username: string;
  password_hash: string;
  created_at: Date;
  updated_at: Date;
}

export const findByUsername = async (username: string): Promise<UserRow | null> => {
  const result = await query<UserRow>(
    `SELECT id, username, password_hash, created_at, updated_at
         FROM users
         WHERE username = $1`,
    [username],
  );
  return result.rows[0] ?? null;
};

export const findById = async (id: string): Promise<UserRow | null> => {
  const result = await query<UserRow>(
    `SELECT id, username, password_hash, created_at, updated_at
         FROM users
         WHERE id = $1`,
    [id],
  );
  return result.rows[0] ?? null;
};

export const create = async (username: string, passwordHash: string): Promise<UserRow> => {
  const result = await query<UserRow>(
    `INSERT INTO users (username, password_hash)
         VALUES ($1, $2)
         RETURNING id, username, password_hash, created_at, updated_at`,
    [username, passwordHash],
  );
  return result.rows[0] as UserRow;
};
