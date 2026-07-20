"""Repository layer over the persistence backend.

Two interchangeable backends behind one interface:
  - SQLiteStore   : local dev, zero setup (default until Catalyst is provisioned)
  - CatalystStore : Zoho Catalyst Data Store via zcatalyst-sdk + ZCQL

Service code only ever calls get_datastore() and the query/insert methods —
it never knows which backend is live. Switch with DATASTORE_BACKEND=catalyst.
"""

import os
import sqlite3
from contextvars import ContextVar
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = Path(__file__).resolve().parents[2] / "data" / "ksp_local.db"

# Populated per-request by middleware in app.main; carries the x-zc-* headers
# AppSail injects, which the Catalyst SDK needs to authenticate.
request_headers_var: ContextVar[dict] = ContextVar("request_headers", default={})


class SQLiteStore:
    def __init__(self, db_path=SQLITE_PATH):
        self.db_path = str(db_path)

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute_query(self, sql: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(sql).fetchall()
            return [dict(r) for r in rows]

    def create_table(self, table: str, columns: dict):
        cols = ", ".join(f'"{name}" {sqltype}' for name, sqltype in columns.items())
        with self._conn() as conn:
            conn.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({cols})')

    def bulk_insert(self, table: str, rows: list[dict]):
        if not rows:
            return
        cols = list(rows[0].keys())
        placeholders = ", ".join("?" for _ in cols)
        col_list = ", ".join(f'"{c}"' for c in cols)
        with self._conn() as conn:
            conn.executemany(
                f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})',
                [tuple(r[c] for c in cols) for r in rows],
            )

    def query(self, table: str, filters: dict | None = None, limit: int = 200) -> list[dict]:
        sql = f'SELECT * FROM "{table}"'
        params: list = []
        if filters:
            clauses = []
            for col, val in filters.items():
                clauses.append(f'"{col}" = ?')
                params.append(val)
            sql += " WHERE " + " AND ".join(clauses)
        sql += f" LIMIT {int(limit)}"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]


class CatalystStore:
    """Zoho Catalyst Data Store backend. Requires the app to run inside a
    Catalyst context (AppSail) or with admin-scope credentials configured."""

    def _app(self):
        """Initialize the SDK inside the calling thread using this request's
        Catalyst headers (the SDK stores credentials thread-locally)."""
        import zcatalyst_sdk

        headers = request_headers_var.get()
        if headers:
            return zcatalyst_sdk.initialize(req=SimpleNamespace(headers=headers))
        return zcatalyst_sdk.initialize()

    def execute_query(self, zcql: str) -> list[dict]:
        result = self._app().zcql().execute_query(zcql)
        # ZCQL rows come back nested as {table_name: {col: val}}; flatten them
        flat = []
        for row in result:
            merged = {}
            for value in row.values():
                if isinstance(value, dict):
                    merged.update(value)
                else:
                    merged.update(row)
                    break
            flat.append(merged)
        return flat

    def create_table(self, table: str, columns: dict):
        raise NotImplementedError(
            "Catalyst Data Store tables must be created in the Catalyst console "
            "or via catalyst CLI — create them there, then re-run seeding."
        )

    def bulk_insert(self, table: str, rows: list[dict]):
        table_ref = self._app().datastore().table(table)
        # Catalyst caps batch insert size; chunk conservatively
        for i in range(0, len(rows), 100):
            table_ref.insert_rows(rows[i : i + 100])

    def query(self, table: str, filters: dict | None = None, limit: int = 200) -> list[dict]:
        base = f"SELECT * FROM {table}"
        if filters:
            clauses = []
            for col, val in filters.items():
                if isinstance(val, str):
                    val = "'" + val.replace("'", "''") + "'"
                clauses.append(f"{col} = {val}")
            base += " WHERE " + " AND ".join(clauses)

        # ZCQL caps SELECT at 300 rows; page with LIMIT <start>,<count> where
        # <start> is a 1-based row number (LIMIT 4,3 returns rows 4-6).
        rows: list[dict] = []
        start = 1
        while len(rows) < limit:
            page_size = min(300, limit - len(rows))
            batch = self.execute_query(f"{base} LIMIT {start},{page_size}")
            rows.extend(batch)
            if len(batch) < page_size:
                break
            start += page_size
        return rows


_store = None


def get_datastore():
    global _store
    if _store is None:
        backend = os.getenv("DATASTORE_BACKEND", "sqlite").lower()
        _store = CatalystStore() if backend == "catalyst" else SQLiteStore()
    return _store
