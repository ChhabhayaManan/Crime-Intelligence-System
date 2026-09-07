from __future__ import annotations

import os
from pathlib import Path

from psycopg2 import connect

from .session import SCHEMA

SENTINEL_TABLE = "address"
ADVISORY_LOCK_KEY = 8_531_207

# project root directory, two levels up from this file
def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]

# read the .sql files 
def _read_sql(name: str) -> str:
    return (_project_root() / "Database" / name).read_text(encoding="utf-8")

# check if the schema is already populated by looking for the sentinel table
def _schema_is_populated(cur) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = %s AND table_name = %s",
        (SCHEMA, SENTINEL_TABLE),
    )
    return cur.fetchone() is not None

# columns added to schema.sql after the first release, applied to already-migrated schemas
_COLUMN_ADDITIONS = (
    ("testifies_in", "testimony", "VARCHAR(255)"),
)


# add any post-release columns that an already-populated schema is missing
def _apply_column_additions(cur) -> None:
    for table, column, column_type in _COLUMN_ADDITIONS:
        cur.execute(
            f"ALTER TABLE {SCHEMA}.{table} "
            f"ADD COLUMN IF NOT EXISTS {column} {column_type}"
        )


# run the migration by executing the SQL files if the schema is not already populated
def run_migration(database_url: str) -> bool:
    conn = connect(database_url)
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (ADVISORY_LOCK_KEY,))

            if _schema_is_populated(cur):
                _apply_column_additions(cur)
                conn.commit()
                return False

            cur.execute(_read_sql("schema.sql"))
            cur.execute(_read_sql("seed_data.sql"))

            if not _schema_is_populated(cur):
                raise RuntimeError(
                    f"schema.sql did not create {SENTINEL_TABLE!r} in schema {SCHEMA!r}."
                )
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

    if run_migration(database_url):
        print(f"Migration applied to schema '{SCHEMA}'.")
    else:
        print(f"Schema '{SCHEMA}' already migrated — no-op.")


if __name__ == "__main__":
    main()


