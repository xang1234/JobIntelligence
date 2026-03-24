"""
Database factory functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .db_target import DatabaseTarget, resolve_database_target, resolve_dual_write_target
from .dual_write import DualWriteDatabase

if TYPE_CHECKING:
    from .db_protocols import DatabaseProtocol


def open_database(
    db_value: str | DatabaseTarget | None = None,
    *,
    read_only: bool = False,
    ensure_schema: bool = True,
    journal_mode: str | None = None,
) -> "DatabaseProtocol":
    """Open the requested database backend with compatibility fallbacks."""
    target = db_value if isinstance(db_value, DatabaseTarget) else resolve_database_target(db_value)

    if target.is_postgres:
        from .pg_database import PostgresDatabase

        primary = PostgresDatabase(
            target.dsn,
            read_only=read_only,
            ensure_schema=ensure_schema,
        )
    else:
        from .database import MCFDatabase

        primary = MCFDatabase(
            target.sqlite_path.as_posix(),
            read_only=read_only,
            ensure_schema=ensure_schema,
            journal_mode=journal_mode,
        )

    secondary_target = None if read_only else resolve_dual_write_target()
    if secondary_target and secondary_target.value != target.value:
        secondary = open_database(
            secondary_target,
            read_only=False,
            ensure_schema=ensure_schema,
            journal_mode=journal_mode,
        )
        return DualWriteDatabase(primary, secondary)

    return primary
