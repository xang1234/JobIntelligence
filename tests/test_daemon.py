"""Tests for daemon process discovery and shutdown."""

import signal
import subprocess
from pathlib import Path

from src.mcf.daemon import ScraperDaemon


class FakeDB:
    """Minimal DB stub for daemon tests."""

    @staticmethod
    def can_acquire_write_lock(db_path: str, timeout_ms: int = 1000) -> bool:
        return True

    def get_daemon_state(self) -> dict:
        return {}

    def update_daemon_state(self, pid: int, status: str) -> None:
        return None

    def update_daemon_heartbeat(self) -> None:
        return None


def _worker_listing(pid: int, pidfile: Path, logfile: Path) -> str:
    return (
        f"{pid} /usr/local/bin/python -m src.cli _daemon-worker --db data/mcf_jobs.db "
        f"--pidfile {pidfile} --logfile {logfile} --all\n"
    )


def test_is_running_detects_orphaned_worker(monkeypatch, temp_dir: Path):
    """Daemon should detect a worker even when the pidfile is missing."""
    daemon = ScraperDaemon(
        FakeDB(),
        pidfile=temp_dir / ".scraper.pid",
        logfile=temp_dir / "scraper_daemon.log",
    )

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0],
            0,
            stdout=_worker_listing(497, daemon.pidfile, daemon.logfile),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert daemon.is_running() is True
    assert daemon.get_pid() == 497


def test_stop_kills_orphaned_worker(monkeypatch, temp_dir: Path):
    """Stop should terminate orphaned workers discovered via process scan."""
    daemon = ScraperDaemon(
        FakeDB(),
        pidfile=temp_dir / ".scraper.pid",
        logfile=temp_dir / "scraper_daemon.log",
    )
    signals: list[tuple[int, int]] = []

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0],
            0,
            stdout=_worker_listing(497, daemon.pidfile, daemon.logfile),
            stderr="",
        )

    def fake_kill(pid: int, sig: int):
        signals.append((pid, sig))
        if sig == 0:
            raise ProcessLookupError

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(signal, "SIGTERM", signal.SIGTERM)
    monkeypatch.setattr(signal, "SIGKILL", signal.SIGKILL)
    monkeypatch.setattr("src.mcf.daemon.os.kill", fake_kill)
    monkeypatch.setattr("src.mcf.daemon.time.sleep", lambda _: None)

    assert daemon.stop() is True
    assert signals == [
        (497, signal.SIGTERM),
        (497, 0),
    ]
