"""
Migration and hosted-slice tooling for PostgreSQL deployments.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .hosted_slice import HostedSlicePolicy
from .pg_database import PostgresDatabase


TABLE_COPY_ORDER = [
    "jobs",
    "job_history",
    "scrape_sessions",
    "historical_scrape_progress",
    "fetch_attempts",
    "daemon_state",
    "search_analytics",
]

SEQUENCE_RESET_TABLES = (
    "scrape_sessions",
    "historical_scrape_progress",
    "fetch_attempts",
    "search_analytics",
)


@dataclass
class MigrationAnomaly:
    table: str
    row_id: str
    column: str
    raw_value: str
    issue: str


@dataclass
class MigrationReport:
    source: str
    target: str
    started_at: str
    finished_at: str | None = None
    copied_rows: dict[str, int] = field(default_factory=dict)
    anomalies: list[MigrationAnomaly] = field(default_factory=list)


def _open_sqlite_source(path: str | Path) -> sqlite3.Connection:
    source = Path(path)
    conn = sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.text_factory = lambda raw: raw.decode("utf-8", "replace")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _is_iso_date(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, date):
        return True
    raw = str(value)
    try:
        date.fromisoformat(raw)
    except ValueError:
        return False
    return len(raw) == 10


def audit_sqlite_source(sqlite_path: str | Path) -> list[MigrationAnomaly]:
    """Find malformed date values before load."""
    conn = _open_sqlite_source(sqlite_path)
    anomalies: list[MigrationAnomaly] = []
    try:
        for batch in _stream_sqlite_rows(
            conn,
            """
            SELECT uuid, posted_date, expiry_date
            FROM jobs
            """,
        ):
            for row in batch:
                for column in ("posted_date", "expiry_date"):
                    raw_value = row[column]
                    if not _is_iso_date(raw_value):
                        anomalies.append(
                            MigrationAnomaly(
                                table="jobs",
                                row_id=row["uuid"],
                                column=column,
                                raw_value=str(raw_value),
                                issue="invalid_iso_date",
                            )
                        )
    finally:
        conn.close()
    return anomalies


def _truncate_postgres_target(db: PostgresDatabase) -> None:
    with db._connection() as conn:
        conn.execute(
            """
            TRUNCATE TABLE
                search_analytics,
                embeddings,
                fetch_attempts,
                historical_scrape_progress,
                scrape_sessions,
                job_history,
                jobs,
                daemon_state
            RESTART IDENTITY CASCADE
            """
        )
        conn.execute("INSERT INTO daemon_state (id, status) VALUES (1, 'stopped') ON CONFLICT (id) DO NOTHING")


def _coerce_job_row(row: sqlite3.Row, report: MigrationReport) -> dict[str, Any]:
    coerced = dict(row)
    for column in ("posted_date", "expiry_date"):
        raw = coerced.get(column)
        if not _is_iso_date(raw):
            report.anomalies.append(
                MigrationAnomaly(
                    table="jobs",
                    row_id=str(coerced["uuid"]),
                    column=column,
                    raw_value=str(raw),
                    issue="coerced_to_null",
                )
            )
            coerced[column] = None
    return coerced


def _chunked(iterable: Iterable[Any], size: int) -> Iterable[list[Any]]:
    chunk: list[Any] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _stream_sqlite_rows(
    conn: sqlite3.Connection,
    query: str,
    params: tuple[Any, ...] = (),
    *,
    fetch_size: int = 5000,
) -> Iterable[list[sqlite3.Row]]:
    cursor = conn.execute(query, params)
    while True:
        rows = cursor.fetchmany(fetch_size)
        if not rows:
            break
        yield rows


def _reset_postgres_sequences(conn: Any, tables: Iterable[str] = SEQUENCE_RESET_TABLES) -> None:
    for table in tables:
        seq_row = conn.execute(
            "SELECT pg_get_serial_sequence(%s, 'id') AS sequence_name",
            (table,),
        ).fetchone()
        sequence_name = seq_row["sequence_name"] if seq_row else None
        if not sequence_name:
            continue

        max_id = conn.execute(f"SELECT MAX(id) AS max_id FROM {table}").fetchone()["max_id"]
        if max_id is None:
            conn.execute("SELECT setval(CAST(%s AS regclass), %s, false)", (sequence_name, 1))
        else:
            conn.execute("SELECT setval(CAST(%s AS regclass), %s, true)", (sequence_name, max_id))


def migrate_sqlite_backup_to_postgres(
    *,
    sqlite_path: str | Path,
    postgres_dsn: str,
    batch_size: int = 5000,
    truncate_first: bool = True,
) -> MigrationReport:
    """Copy a full SQLite backup into PostgreSQL."""
    report = MigrationReport(
        source=str(sqlite_path),
        target=postgres_dsn,
        started_at=datetime.now().isoformat(),
    )
    source = _open_sqlite_source(sqlite_path)
    target = PostgresDatabase(postgres_dsn, read_only=False, ensure_schema=True)

    try:
        if truncate_first:
            _truncate_postgres_target(target)

        with target._connection() as conn:
            copied = 0
            for chunk in _stream_sqlite_rows(source, "SELECT * FROM jobs ORDER BY id", fetch_size=batch_size):
                for row in chunk:
                    payload = _coerce_job_row(row, report)
                    target._insert_job(conn, payload, payload.get("last_updated_at") or datetime.now().isoformat())
                    copied += 1
            report.copied_rows["jobs"] = copied

        with target._connection() as conn:
            copied = 0
            for chunk in _stream_sqlite_rows(
                source,
                """
                SELECT job_uuid, title, company_name, salary_min, salary_max,
                       applications_count, description, recorded_at
                FROM job_history ORDER BY id
                """,
                fetch_size=batch_size,
            ):
                conn.executemany(
                    """
                    INSERT INTO job_history (
                        job_uuid, title, company_name, salary_min, salary_max,
                        applications_count, description, recorded_at
                    ) VALUES (
                        %(job_uuid)s, %(title)s, %(company_name)s, %(salary_min)s, %(salary_max)s,
                        %(applications_count)s, %(description)s, %(recorded_at)s
                    )
                    """,
                    [dict(row) for row in chunk],
                )
                copied += len(chunk)
            report.copied_rows["job_history"] = copied

            for table in ("scrape_sessions", "historical_scrape_progress", "fetch_attempts", "search_analytics"):
                copied = 0
                column_list: str | None = None
                value_list: str | None = None
                for chunk in _stream_sqlite_rows(source, f"SELECT * FROM {table} ORDER BY id", fetch_size=batch_size):
                    if column_list is None or value_list is None:
                        columns = chunk[0].keys()
                        column_list = ", ".join(columns)
                        value_list = ", ".join(f"%({column})s" for column in columns)
                    conn.executemany(
                        f"INSERT INTO {table} ({column_list}) VALUES ({value_list})",
                        [dict(row) for row in chunk],
                    )
                    copied += len(chunk)
                report.copied_rows[table] = copied

            daemon_rows: list[dict[str, Any]] = []
            for chunk in _stream_sqlite_rows(source, "SELECT * FROM daemon_state", fetch_size=batch_size):
                daemon_rows.extend(dict(row) for row in chunk)
            if daemon_rows:
                conn.execute("DELETE FROM daemon_state")
                conn.executemany(
                    """
                    INSERT INTO daemon_state (id, pid, status, last_heartbeat, started_at, current_year, current_seq)
                    VALUES (%(id)s, %(pid)s, %(status)s, %(last_heartbeat)s, %(started_at)s, %(current_year)s, %(current_seq)s)
                    """,
                    daemon_rows,
                )
            report.copied_rows["daemon_state"] = len(daemon_rows)
            _reset_postgres_sequences(conn)

        with target._connection() as conn:
            copied = 0
            for chunk in _stream_sqlite_rows(
                source,
                "SELECT entity_id, entity_type, embedding_blob, model_version FROM embeddings ORDER BY id",
                fetch_size=batch_size,
            ):
                payloads = [
                    (
                        row["entity_id"],
                        row["entity_type"],
                        PostgresDatabase._vector_literal(np.frombuffer(row["embedding_blob"], dtype=np.float32)),
                        row["model_version"],
                    )
                    for row in chunk
                ]
                conn.executemany(
                    """
                    INSERT INTO embeddings (entity_id, entity_type, embedding, model_version, updated_at)
                    VALUES (%s, %s, %s::vector, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (entity_id, entity_type) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        model_version = EXCLUDED.model_version,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    payloads,
                )
                copied += len(payloads)
            report.copied_rows["embeddings"] = copied

        report.finished_at = datetime.now().isoformat()
        return report
    finally:
        source.close()


def write_migration_report(report: MigrationReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    payload["anomalies"] = [asdict(anomaly) for anomaly in report.anomalies]
    path.write_text(json.dumps(payload, indent=2))
    return path


def seed_hosted_slice_from_postgres(
    *,
    source_dsn: str,
    target_dsn: str,
    policy: HostedSlicePolicy,
) -> dict[str, int]:
    """
    Seed a lean hosted slice from a full local Postgres dataset.

    Only job rows and job embeddings are copied.
    """
    source = PostgresDatabase(source_dsn, read_only=True, ensure_schema=False)
    target = PostgresDatabase(target_dsn, read_only=False, ensure_schema=True)
    cutoff = policy.cutoff_date()
    _truncate_postgres_target(target)

    with source._connection() as source_conn, target._connection() as target_conn:
        jobs = source_conn.execute(
            """
            SELECT * FROM jobs
            WHERE posted_date IS NOT NULL
              AND posted_date >= %s
            ORDER BY posted_date DESC, id DESC
            """,
            (cutoff,),
        ).fetchall()
        for row in jobs:
            target._insert_job(target_conn, dict(row), row.get("last_updated_at") or datetime.now().isoformat())

    job_ids = []
    with target._connection() as conn:
        rows = conn.execute("SELECT uuid FROM jobs").fetchall()
        job_ids = [row["uuid"] for row in rows]

    with source._connection() as source_conn:
        embeddings = source_conn.execute(
            """
            SELECT entity_id, embedding::text AS embedding, model_version
            FROM embeddings
            WHERE entity_type = 'job' AND entity_id = ANY(%s)
            """,
            (job_ids,),
        ).fetchall()
    with target._connection() as conn:
        conn.executemany(
            """
            INSERT INTO embeddings (entity_id, entity_type, embedding, model_version, updated_at)
            VALUES (%s, 'job', %s::vector, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (entity_id, entity_type) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                model_version = EXCLUDED.model_version,
                updated_at = CURRENT_TIMESTAMP
            """,
            [
                (
                    row["entity_id"],
                    PostgresDatabase._vector_literal(PostgresDatabase._vector_from_value(row["embedding"])),
                    row["model_version"],
                )
                for row in embeddings
            ],
        )

    purge_counts = purge_hosted_slice(target_dsn=target_dsn, policy=policy)
    purge_counts["seeded_jobs"] = len(job_ids)
    purge_counts["seeded_job_embeddings"] = len(embeddings)
    return purge_counts


def purge_hosted_slice(*, target_dsn: str, policy: HostedSlicePolicy) -> dict[str, int]:
    """
    Enforce the lean hosted slice rules inside a Postgres deployment.
    """
    target = PostgresDatabase(target_dsn, read_only=False, ensure_schema=True)
    cutoff = policy.cutoff_date()
    with target._connection() as conn:
        company_deleted = conn.execute(
            "DELETE FROM embeddings WHERE entity_type IN ('skill', 'company') RETURNING 1"
        ).fetchall()
        orphan_job_embeddings = conn.execute(
            """
            DELETE FROM embeddings
            WHERE entity_type = 'job'
              AND entity_id NOT IN (
                  SELECT uuid FROM jobs WHERE posted_date IS NOT NULL AND posted_date >= %s
              )
            RETURNING 1
            """,
            (cutoff,),
        ).fetchall()
        deleted_jobs = conn.execute(
            """
            DELETE FROM jobs
            WHERE posted_date IS NULL OR posted_date < %s
            RETURNING 1
            """,
            (cutoff,),
        ).fetchall()
    return {
        "deleted_non_job_embeddings": len(company_deleted),
        "deleted_orphan_job_embeddings": len(orphan_job_embeddings),
        "deleted_jobs": len(deleted_jobs),
    }
