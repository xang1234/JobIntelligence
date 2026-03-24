from datetime import date

from src.mcf.db_target import resolve_database_target
from src.mcf.hosted_slice import HostedSlicePolicy


def test_resolve_database_target_detects_sqlite_path():
    target = resolve_database_target("data/mcf_jobs.db")
    assert target.is_sqlite is True
    assert target.is_postgres is False


def test_resolve_database_target_detects_postgres_dsn():
    target = resolve_database_target("postgresql://user:pass@localhost:5432/mcf")
    assert target.is_postgres is True
    assert target.is_sqlite is False


def test_hosted_slice_policy_uses_max_of_year_floor_and_rolling_cutoff():
    policy = HostedSlicePolicy(min_posted_date=date(2026, 1, 1), max_age_days=90)
    assert policy.cutoff_date(date(2026, 3, 24)) == date(2026, 1, 1)
    assert policy.cutoff_date(date(2026, 7, 1)) == date(2026, 4, 2)
