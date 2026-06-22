"""
setup_db.py
-----------
Idempotent migration entrypoint for the one-off ECS task.

Reads DATABASE_URL (the writer) from the environment, ensures the named schema
exists, sets the search_path, and — if the schema has not yet been populated —
runs Database/schema.sql followed by Database/seed_data.sql.

This is a *create-or-skip* migration, not a versioned one: schema evolution on an
already-migrated DB is out of scope (Alembic is the documented future path).

Run with:
    python -m App.db.setup_db
"""

from __future__ import annotations

import os
from pathlib import Path

from psycopg2 import connect, sql

# Schema namespace (matches App/db/session.py default).
SCHEMA_NAME = os.getenv("DB_SCHEMA", "crimedb")
# A table from schema.sql whose presence indicates the schema is already populated.
SENTINEL_TABLE = "address"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_sql_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _schema_is_populated(cur, schema_name: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = %s AND table_name = %s",
        (schema_name, SENTINEL_TABLE),
    )
    return cur.fetchone() is not None


def run_migration(database_url: str, schema_name: str = SCHEMA_NAME) -> bool:
    """Ensure the schema exists and is seeded.

    Returns True if migration ran, False if it was a no-op (already migrated).
    """
    root = _project_root()
    schema_sql = _read_sql_file(root / "Database" / "schema.sql")
    seed_sql = _read_sql_file(root / "Database" / "seed_data.sql")

    conn = connect(database_url)
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            # Create-if-missing schema, then scope all work to it.
            cur.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                    sql.Identifier(schema_name)
                )
            )
            cur.execute(
                sql.SQL("SET search_path TO {}").format(sql.Identifier(schema_name))
            )

            if _schema_is_populated(cur, schema_name):
                conn.commit()
                return False

            cur.execute(schema_sql)
            cur.execute(seed_sql)
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required.")

    ran = run_migration(database_url)
    if ran:
        print(f"Migration applied to schema '{SCHEMA_NAME}'.")
    else:
        print(f"Schema '{SCHEMA_NAME}' already migrated — no-op.")


if __name__ == "__main__":
    main()
