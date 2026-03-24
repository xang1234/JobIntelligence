#!/usr/bin/env python3
"""
Migrate a SQLite backup into PostgreSQL.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.mcf.postgres_migration import (
    audit_sqlite_source,
    migrate_sqlite_backup_to_postgres,
    write_migration_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate a SQLite backup into PostgreSQL")
    parser.add_argument("--source", required=True, help="SQLite backup path")
    parser.add_argument("--target", required=True, help="PostgreSQL DSN")
    parser.add_argument("--report", default="data/backups/postgres_migration_report.json", help="Report output path")
    parser.add_argument("--batch-size", type=int, default=5000, help="Rows per batch")
    parser.add_argument("--no-truncate-first", action="store_true", help="Do not truncate target tables before load")
    parser.add_argument("--audit-only", action="store_true", help="Only run the preflight audit")
    args = parser.parse_args()

    anomalies = audit_sqlite_source(args.source)
    if args.audit_only:
        print(json.dumps({"source": args.source, "anomalies": [a.__dict__ for a in anomalies]}, indent=2))
        return

    report = migrate_sqlite_backup_to_postgres(
        sqlite_path=args.source,
        postgres_dsn=args.target,
        batch_size=args.batch_size,
        truncate_first=not args.no_truncate_first,
    )
    report_path = write_migration_report(report, args.report)
    print(json.dumps({"report_path": str(report_path), "copied_rows": report.copied_rows, "anomalies": len(report.anomalies)}, indent=2))


if __name__ == "__main__":
    main()
