import { readdir, readFile } from "fs/promises";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import { pool, closePool } from "../src/adapters/db/pool.js";

const MIGRATIONS_DIR = join(
  dirname(fileURLToPath(import.meta.url)),
  "..",        // api/scripts → api/
  "..",        // api/ → repo root
  "db",
  "migrations",
);

async function ensureMigrationsTable(): Promise<void> {
  await pool.query(`
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        `);
}

async function getAppliedVersions(): Promise<Set<string>> {
  const result = await pool.query<{ version: string }>(`
        SELECT version FROM schema_migrations
    `);
  return new Set(result.rows.map((row) => row.version));
}

async function getPendingFiles(applied: Set<string>): Promise<string[]> {
  const files = await readdir(MIGRATIONS_DIR);
  return files
    .filter((f) => f.endsWith(".sql"))
    .sort()
    .filter((f) => !applied.has(f.replace(".sql", "")));
}

async function applyMigration(file: string): Promise<void> {
  const sql = await readFile(join(MIGRATIONS_DIR, file), "utf-8");
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    await client.query(sql);
    await client.query("INSERT INTO schema_migrations (version) VALUES ($1)", [
      file.replace(".sql", ""),
    ]);
    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

async function main(): Promise<void> {
  try {
    await ensureMigrationsTable();
    const appliedVersions = await getAppliedVersions();
    const pendingFiles = await getPendingFiles(appliedVersions);
    if (pendingFiles.length === 0) {
      console.log("No pending migrations.");
      return;
    }
    console.log(`Applying ${pendingFiles.length} migration(s)...`);
    for (const file of pendingFiles) {
      console.log(`  ▶ ${file}`);
      await applyMigration(file);
      console.log(`  ✓ ${file}`);
    }
    console.log("Done.");
  } catch (error) {
    console.error("Migration failed:", error);
    await closePool();
    process.exit(1);
  }
}

void main();
