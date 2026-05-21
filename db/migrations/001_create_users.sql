-- 001: create users table
-- Initial user accounts for authentication.
CREATE TABLE
    users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
        username VARCHAR(32) UNIQUE NOT NULL CHECK (CHAR_LENGTH(username) >= 3),
        password_hash TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW (),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW ()
    );