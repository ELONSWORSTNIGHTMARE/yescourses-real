"""
Shared DB access: SQLite locally, PostgreSQL when DATABASE_URL is set (required for Vercel
so all users see the same data). Each Vercel instance has its own /tmp — SQLite there is NOT shared.

Supabase: set DATABASE_URL in Vercel to your Postgres URI (Settings → Database).
Do NOT use NEXT_PUBLIC_* for database passwords — that exposes them in the browser.
"""
from __future__ import annotations

import os
import sqlite3


def _resolve_database_url() -> str:
    """Prefer DATABASE_URL; allow common Supabase/Vercel aliases (server-side only)."""
    for key in (
        "DATABASE_URL",
        "SUPABASE_DATABASE_URL",
        "POSTGRES_URL",
        "POSTGRES_URL_NON_POOLING",
    ):
        v = os.environ.get(key, "").strip()
        if v:
            return v
    return ""


DATABASE_URL = _resolve_database_url()
USE_POSTGRES = bool(DATABASE_URL)


def _adapt_sql(q: str) -> str:
    if not USE_POSTGRES:
        return q
    return q.replace("?", "%s")


def ex(cur, query: str, params=()):
    cur.execute(_adapt_sql(query), params)


def _pg_connect_kwargs():
    """Supabase pooler (PgBouncer) needs prepared statements disabled."""
    url = DATABASE_URL.lower()
    if "pooler" in url or ":6543" in url or "pgbouncer" in url:
        return {"prepare_threshold": None}
    return {}


def get_db():
    if USE_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row,
            **_pg_connect_kwargs(),
        )
    conn = sqlite3.connect(os.environ.get("SQLITE_PATH") or _sqlite_default_path())
    conn.row_factory = sqlite3.Row
    return conn


def _sqlite_default_path():
    base = os.path.dirname(os.path.abspath(__file__))
    if os.environ.get("VERCEL") == "1":
        return "/tmp/yescourses_data.db"
    return os.path.join(base, "data.db")


def init_db_sqlite(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pack_id TEXT NOT NULL,
            purchased_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pack_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            filename TEXT NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 1,
            uploaded_at TEXT NOT NULL,
            remote_src TEXT
        )
        """
    )
    try:
        cur.execute("ALTER TABLE videos ADD COLUMN remote_src TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()


def init_db_postgres(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS purchases (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            pack_id TEXT NOT NULL,
            purchased_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS videos (
            id SERIAL PRIMARY KEY,
            pack_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            filename TEXT NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 1,
            uploaded_at TEXT NOT NULL,
            remote_src TEXT
        )
        """
    )
    conn.commit()


def init_db():
    conn = get_db()
    try:
        if USE_POSTGRES:
            init_db_postgres(conn)
        else:
            init_db_sqlite(conn)
    finally:
        conn.close()


def row_to_dict(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)


def is_unique_violation(exc) -> bool:
    if isinstance(exc, sqlite3.IntegrityError):
        return "UNIQUE" in str(exc).upper()
    try:
        import psycopg.errors as pe

        return isinstance(exc, pe.UniqueViolation)
    except ImportError:
        return False
