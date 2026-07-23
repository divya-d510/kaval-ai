"""Dump the seeded SQLite tables to CSV for Catalyst ds:import."""

import csv
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "ksp_local.db"
OUT = Path(__file__).parent / "export"
TABLES = [
    "fir_records", "suspects", "fir_suspect_links", "suspect_associations",
    "victims", "fir_victim_links", "financial_accounts", "financial_transactions",
]


def main():
    OUT.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    for table in TABLES:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        path = OUT / f"{table}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(rows[0].keys())
            writer.writerows([tuple(r) for r in rows])
        print(f"{table}: {len(rows)} rows -> {path.name}")
    conn.close()


if __name__ == "__main__":
    main()
