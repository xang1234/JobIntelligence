#!/usr/bin/env python3
"""
Create and verify a hot SQLite backup.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.mcf.db_backup import create_sqlite_hot_backup, verify_sqlite_backup


def main() -> None:
    parser = argparse.ArgumentParser(description="Create and verify a hot SQLite backup")
    parser.add_argument("--source", default="data/mcf_jobs.db", help="Path to the live SQLite database")
    parser.add_argument("--backup-dir", default="data/backups", help="Directory to write backups into")
    parser.add_argument("--prefix", default="mcf_pre_postgres", help="Backup filename prefix")
    args = parser.parse_args()

    backup_path = create_sqlite_hot_backup(args.source, args.backup_dir, prefix=args.prefix)
    metadata = verify_sqlite_backup(backup_path)

    metadata_path = Path(args.backup_dir) / f"{backup_path.stem}.json"
    metadata_path.write_text(json.dumps(metadata.__dict__ | {"path": str(metadata.path)}, indent=2, default=str))

    print(json.dumps({"backup_path": str(backup_path), "metadata_path": str(metadata_path), **metadata.__dict__}, default=str))


if __name__ == "__main__":
    main()
