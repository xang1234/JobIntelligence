#!/usr/bin/env python3
"""
Seed a lean hosted Postgres slice from a full local Postgres database.
"""

from __future__ import annotations

import argparse
import json
from datetime import date

from src.mcf.hosted_slice import HostedSlicePolicy
from src.mcf.postgres_migration import seed_hosted_slice_from_postgres


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a lean hosted slice from local Postgres")
    parser.add_argument("--source", required=True, help="Source PostgreSQL DSN")
    parser.add_argument("--target", required=True, help="Target PostgreSQL DSN")
    parser.add_argument("--min-posted-date", default="2026-01-01", help="Minimum posted date for hosted rows")
    parser.add_argument("--max-age-days", type=int, default=90, help="Maximum row age in days")
    args = parser.parse_args()

    policy = HostedSlicePolicy(
        min_posted_date=date.fromisoformat(args.min_posted_date),
        max_age_days=args.max_age_days,
    )
    result = seed_hosted_slice_from_postgres(
        source_dsn=args.source,
        target_dsn=args.target,
        policy=policy,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
