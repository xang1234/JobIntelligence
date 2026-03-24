#!/usr/bin/env python3
"""
Purge a hosted Postgres slice down to the lean policy.
"""

from __future__ import annotations

import argparse
import json
from datetime import date

from src.mcf.hosted_slice import HostedSlicePolicy
from src.mcf.postgres_migration import purge_hosted_slice


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge a hosted slice to the lean policy")
    parser.add_argument("--target", required=True, help="Target PostgreSQL DSN")
    parser.add_argument("--min-posted-date", default="2026-01-01", help="Minimum posted date for hosted rows")
    parser.add_argument("--max-age-days", type=int, default=90, help="Maximum row age in days")
    args = parser.parse_args()

    policy = HostedSlicePolicy(
        min_posted_date=date.fromisoformat(args.min_posted_date),
        max_age_days=args.max_age_days,
    )
    result = purge_hosted_slice(target_dsn=args.target, policy=policy)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
