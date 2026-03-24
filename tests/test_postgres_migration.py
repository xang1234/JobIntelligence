from __future__ import annotations

import sqlite3

from src.mcf.postgres_migration import _reset_postgres_sequences, _stream_sqlite_rows


def test_stream_sqlite_rows_batches_without_fetchall():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE jobs (id INTEGER PRIMARY KEY, title TEXT)")
    conn.executemany("INSERT INTO jobs (title) VALUES (?)", [(f"job-{i}",) for i in range(5)])

    batches = list(_stream_sqlite_rows(conn, "SELECT * FROM jobs ORDER BY id", fetch_size=2))

    assert [len(batch) for batch in batches] == [2, 2, 1]
    assert [row["title"] for batch in batches for row in batch] == [f"job-{i}" for i in range(5)]


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeSequenceConn:
    def __init__(self):
        self.calls = []

    def execute(self, query, params=None):
        self.calls.append((query, params))
        if "pg_get_serial_sequence" in query:
            table = params[0]
            return _FakeResult({"sequence_name": f"public.{table}_id_seq"})
        if "SELECT MAX(id)" in query:
            if "scrape_sessions" in query:
                return _FakeResult({"max_id": 12})
            return _FakeResult({"max_id": None})
        return _FakeResult(None)


def test_reset_postgres_sequences_uses_max_id_and_empty_table_defaults():
    conn = _FakeSequenceConn()

    _reset_postgres_sequences(conn, tables=("scrape_sessions", "search_analytics"))

    setval_calls = [(query, params) for query, params in conn.calls if "SELECT setval" in query]
    assert setval_calls == [
        ("SELECT setval(CAST(%s AS regclass), %s, true)", ("public.scrape_sessions_id_seq", 12)),
        ("SELECT setval(CAST(%s AS regclass), %s, false)", ("public.search_analytics_id_seq", 1)),
    ]
